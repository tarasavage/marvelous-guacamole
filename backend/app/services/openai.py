import base64
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

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
from app.services.llm_observability import (
    log_llm_event,
    sanitize_messages_for_debug,
    utc_now_iso,
    write_debug_artifact,
)

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

_attempt_number: ContextVar[int] = ContextVar("llm_attempt_number", default=1)


@dataclass(frozen=True)
class _LlmContext:
    operation: str
    document_id: str | None
    batch_num: int | None = None
    start_page: int | None = None
    end_page: int | None = None


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


def _record_attempt(retry_state) -> None:
    _attempt_number.set(retry_state.attempt_number)


def check_context_limit(text: str) -> None:
    estimated_tokens = len(text) // CHARS_PER_TOKEN_ESTIMATE
    if estimated_tokens > CONTEXT_TOKEN_LIMIT:
        raise ContextLimitError(
            "Document too dense to summarize within model context limits"
        )


def _usage_fields(response) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _log_success(
    ctx: _LlmContext,
    *,
    latency_ms: int,
    finish_reason: str | None,
    response_text: str,
    response: Any,
) -> None:
    log_llm_event(
        "llm_call_success",
        {
            "document_id": ctx.document_id,
            "operation": ctx.operation,
            "model": MODEL,
            "batch_num": ctx.batch_num,
            "start_page": ctx.start_page,
            "end_page": ctx.end_page,
            "latency_ms": latency_ms,
            "finish_reason": finish_reason,
            "response_chars": len(response_text),
            "attempt": _attempt_number.get(),
            **_usage_fields(response),
        },
    )


def _log_failure(ctx: _LlmContext, *, latency_ms: int, error: Exception) -> None:
    log_llm_event(
        "llm_call_failure",
        {
            "document_id": ctx.document_id,
            "operation": ctx.operation,
            "model": MODEL,
            "batch_num": ctx.batch_num,
            "start_page": ctx.start_page,
            "end_page": ctx.end_page,
            "latency_ms": latency_ms,
            "attempt": _attempt_number.get(),
            "error_type": type(error).__name__,
        },
    )


def _write_debug(
    ctx: _LlmContext,
    *,
    filename: str,
    messages: list[dict[str, Any]],
    response_text: str | None,
    response: Any | None,
    error: Exception | None,
) -> None:
    payload: dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "document_id": ctx.document_id,
        "operation": ctx.operation,
        "model": MODEL,
        "batch_num": ctx.batch_num,
        "start_page": ctx.start_page,
        "end_page": ctx.end_page,
        "attempt": _attempt_number.get(),
        "messages": sanitize_messages_for_debug(messages),
        "response_text": response_text,
        "error": repr(error) if error else None,
    }
    if response is not None:
        payload.update(_usage_fields(response))
    write_debug_artifact(
        settings.data_dir,
        ctx.document_id or "",
        filename,
        payload,
        enabled=settings.debug_llm,
    )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=_wait_chain(EXTRACTION_BACKOFF),
    before=_record_attempt,
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_extraction(
    client: OpenAI,
    content: list[dict],
    ctx: _LlmContext,
) -> str:
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=EXTRACTION_MAX_TOKENS,
            messages=messages,
        )
        choice = response.choices[0]
        text = (choice.message.content or "").strip()
        latency_ms = int((time.perf_counter() - started) * 1000)
        if choice.finish_reason == "length":
            raise OpenAIServiceError("Vision response truncated (max tokens reached)")
        if not text:
            raise OpenAIServiceError("Vision response was empty")
        _log_success(
            ctx,
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason,
            response_text=text,
            response=response,
        )
        _write_debug(
            ctx,
            filename=f"extraction-b{ctx.batch_num or 0}-p{ctx.start_page}-{ctx.end_page}.json",
            messages=messages,
            response_text=text,
            response=response,
            error=None,
        )
        return text
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not _is_retryable(exc):
            _log_failure(ctx, latency_ms=latency_ms, error=exc)
            _write_debug(
                ctx,
                filename=f"extraction-b{ctx.batch_num or 0}-p{ctx.start_page}-{ctx.end_page}-error.json",
                messages=messages,
                response_text=None,
                response=None,
                error=exc,
            )
        raise


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(2),
    wait=_wait_chain(SUMMARY_BACKOFF),
    before=_record_attempt,
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_summary(client: OpenAI, full_text: str, ctx: _LlmContext) -> str:
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": SUMMARY_USER_TEMPLATE.format(content=full_text),
        },
    ]
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=SUMMARY_MAX_TOKENS,
            messages=messages,
        )
        choice = response.choices[0]
        text = (choice.message.content or "").strip()
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not text:
            raise OpenAIServiceError("Summary response was empty")
        _log_success(
            ctx,
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason,
            response_text=text,
            response=response,
        )
        _write_debug(
            ctx,
            filename="summary.json",
            messages=messages,
            response_text=text,
            response=response,
            error=None,
        )
        return text
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not _is_retryable(exc):
            _log_failure(ctx, latency_ms=latency_ms, error=exc)
            _write_debug(
                ctx,
                filename="summary-error.json",
                messages=messages,
                response_text=None,
                response=None,
                error=exc,
            )
        raise


def extract_batch(
    page_images: list[bytes],
    start_page: int,
    end_page: int,
    *,
    document_id: str | None = None,
    batch_num: int | None = None,
) -> str:
    client = _get_client()
    ctx = _LlmContext(
        operation="extraction",
        document_id=document_id,
        batch_num=batch_num,
        start_page=start_page,
        end_page=end_page,
    )

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

    try:
        return _call_extraction(client, content, ctx)
    except Exception as exc:
        if _is_retryable(exc):
            _log_failure(ctx, latency_ms=0, error=exc)
        raise


def summarize(
    full_text: str,
    *,
    document_id: str | None = None,
) -> str:
    check_context_limit(full_text)
    client = _get_client()
    ctx = _LlmContext(operation="summary", document_id=document_id)
    try:
        return _call_summary(client, full_text, ctx)
    except Exception as exc:
        if _is_retryable(exc):
            _log_failure(ctx, latency_ms=0, error=exc)
        raise
