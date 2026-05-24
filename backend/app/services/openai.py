import base64
import logging

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)

from app.config import settings

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
EXTRACTION_MAX_TOKENS = 4096
SUMMARY_MAX_TOKENS = 1024
CONTEXT_TOKEN_LIMIT = 100_000
CHARS_PER_TOKEN_ESTIMATE = 4

EXTRACTION_BACKOFF = (2, 4, 8)
SUMMARY_BACKOFF = (2, 4)

EXTRACTION_SYSTEM_PROMPT = """You extract content from PDF page images.

Output strict Markdown:
- Reproduce plain text faithfully
- Convert tables to Markdown tables
- Describe charts and images with brief captions
- Use the document's primary language
- Separate each page's content with a line containing only ---"""

EXTRACTION_USER_TEMPLATE = """Extract the content from pages {start_page} through {end_page} of this document.
Separate each page with --- on its own line."""

SUMMARY_SYSTEM_PROMPT = """You summarize document content for a busy reader.

Output format:
- Start with "TL;DR:" followed by 1-2 sentences
- Then a blank line
- Then 5-10 bullet points (each starting with •)
- Preserve critical numbers, names, and table data
- Do not invent content not in the source
- Use the document's primary language"""

SUMMARY_USER_TEMPLATE = """Summarize the following document content:

{content}"""


class OpenAIServiceError(Exception):
    pass


class ContextLimitError(OpenAIServiceError):
    pass


def _get_client() -> OpenAI:
    if not settings.openai_api_key:
        raise OpenAIServiceError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.openai_api_key, timeout=120.0)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None) if response else None
    if status in (429, 500, 502, 503, 504):
        return True
    return False


def _wait_chain(backoff_seconds: tuple[int, ...]):
    return wait_chain(*(wait_fixed(seconds) for seconds in backoff_seconds))


def check_context_limit(text: str) -> None:
    estimated_tokens = len(text) // CHARS_PER_TOKEN_ESTIMATE
    if estimated_tokens > CONTEXT_TOKEN_LIMIT:
        raise ContextLimitError(
            "Document too dense to summarize within model context limits"
        )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=_wait_chain(EXTRACTION_BACKOFF),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_extraction(client: OpenAI, content: list[dict]) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=EXTRACTION_MAX_TOKENS,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    if choice.finish_reason == "length":
        raise OpenAIServiceError("Vision response truncated (max tokens reached)")
    if not text:
        raise OpenAIServiceError("Vision response was empty")
    return text


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(2),
    wait=_wait_chain(SUMMARY_BACKOFF),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_summary(client: OpenAI, full_text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=SUMMARY_MAX_TOKENS,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": SUMMARY_USER_TEMPLATE.format(content=full_text),
            },
        ],
    )
    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    if not text:
        raise OpenAIServiceError("Summary response was empty")
    return text


def extract_batch(page_images: list[bytes], start_page: int, end_page: int) -> str:
    client = _get_client()

    content: list[dict] = [
        {"type": "text", "text": EXTRACTION_USER_TEMPLATE.format(start_page=start_page, end_page=end_page)}
    ]
    for image_bytes in page_images:
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            }
        )

    return _call_extraction(client, content)


def summarize(full_text: str) -> str:
    check_context_limit(full_text)
    client = _get_client()
    return _call_summary(client, full_text)
