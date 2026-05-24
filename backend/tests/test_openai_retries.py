from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import RateLimitError

from app.services import openai as openai_service


def _completion(content: str = "extracted markdown", finish_reason: str = "stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150),
    )


def _rate_limit_error() -> RateLimitError:
    return RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    monkeypatch.setattr("tenacity.nap.sleep", lambda _: None)


@pytest.fixture
def mock_openai_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(openai_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(openai_service, "_get_client", lambda: client)
    return client


def test_extract_batch_retries_transient_error_then_succeeds(mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = [
        _rate_limit_error(),
        _completion("page content"),
    ]

    result = openai_service.extract_batch([b"image"], start_page=1, end_page=1)

    assert result == "page content"
    assert mock_openai_client.chat.completions.create.call_count == 2


def test_extract_batch_raises_after_three_attempts(mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = _rate_limit_error()

    with pytest.raises(RateLimitError):
        openai_service.extract_batch([b"image"], start_page=1, end_page=1)

    assert mock_openai_client.chat.completions.create.call_count == 3


def test_extract_batch_does_not_retry_empty_response(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = _completion("")

    with pytest.raises(openai_service.OpenAIServiceError, match="empty"):
        openai_service.extract_batch([b"image"], start_page=1, end_page=1)

    assert mock_openai_client.chat.completions.create.call_count == 1


def test_extract_batch_does_not_retry_truncated_response(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = _completion(
        "partial",
        finish_reason="length",
    )

    with pytest.raises(openai_service.OpenAIServiceError, match="truncated"):
        openai_service.extract_batch([b"image"], start_page=1, end_page=1)

    assert mock_openai_client.chat.completions.create.call_count == 1


def test_summarize_retries_transient_error_then_succeeds(mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = [
        _rate_limit_error(),
        _completion("TL;DR: summary\n\n• point"),
    ]

    result = openai_service.summarize("document text")

    assert result == "TL;DR: summary\n\n• point"
    assert mock_openai_client.chat.completions.create.call_count == 2


def test_summarize_raises_after_two_attempts(mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = _rate_limit_error()

    with pytest.raises(RateLimitError):
        openai_service.summarize("document text")

    assert mock_openai_client.chat.completions.create.call_count == 2


def test_summarize_does_not_retry_empty_response(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = _completion("")

    with pytest.raises(openai_service.OpenAIServiceError, match="empty"):
        openai_service.summarize("document text")

    assert mock_openai_client.chat.completions.create.call_count == 1


def test_summarize_does_not_retry_context_limit(monkeypatch):
    monkeypatch.setattr(openai_service.settings, "openai_api_key", "test-key")
    get_client = MagicMock()
    monkeypatch.setattr(openai_service, "_get_client", get_client)

    oversized = "x" * (openai_service.CONTEXT_TOKEN_LIMIT * openai_service.CHARS_PER_TOKEN_ESTIMATE + 4)

    with pytest.raises(openai_service.ContextLimitError):
        openai_service.summarize(oversized)

    get_client.assert_not_called()
