import base64
import logging
import time
from typing import Callable, TypeVar

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

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

T = TypeVar("T")


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


def _call_with_retries(
    fn: Callable[[], T],
    max_attempts: int,
    backoff_seconds: tuple[int, ...],
) -> T:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt >= max_attempts - 1:
                raise
            delay = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
            logger.warning("OpenAI call failed (attempt %s/%s): %s", attempt + 1, max_attempts, exc)
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def check_context_limit(text: str) -> None:
    estimated_tokens = len(text) // CHARS_PER_TOKEN_ESTIMATE
    if estimated_tokens > CONTEXT_TOKEN_LIMIT:
        raise ContextLimitError(
            "Document too dense to summarize within model context limits"
        )


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

    def _call() -> str:
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

    return _call_with_retries(_call, max_attempts=3, backoff_seconds=EXTRACTION_BACKOFF)


def summarize(full_text: str) -> str:
    check_context_limit(full_text)
    client = _get_client()

    def _call() -> str:
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

    return _call_with_retries(_call, max_attempts=2, backoff_seconds=SUMMARY_BACKOFF)
