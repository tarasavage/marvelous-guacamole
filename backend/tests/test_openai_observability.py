import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import openai as openai_service


def _completion(content: str = "extracted markdown"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
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


def test_extract_batch_logs_document_id_on_success(mock_openai_client, caplog):
    caplog.set_level(logging.INFO)
    mock_openai_client.chat.completions.create.return_value = _completion()

    openai_service.extract_batch(
        [b"image"],
        start_page=1,
        end_page=1,
        document_id="doc-abc",
        batch_num=2,
    )

    messages = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    success = next(event for event in messages if event.get("event") == "llm_call_success")
    assert success["document_id"] == "doc-abc"
    assert success["operation"] == "extraction"
    assert success["batch_num"] == 2
    assert success["prompt_tokens"] == 10


def test_extract_batch_logs_failure_after_retries_exhausted(mock_openai_client, caplog):
    from openai import RateLimitError

    caplog.set_level(logging.INFO)
    mock_openai_client.chat.completions.create.side_effect = RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )

    with pytest.raises(RateLimitError):
        openai_service.extract_batch(
            [b"image"],
            start_page=1,
            end_page=1,
            document_id="doc-fail",
        )

    messages = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    failures = [event for event in messages if event.get("event") == "llm_call_failure"]
    assert len(failures) == 1
    assert failures[0]["document_id"] == "doc-fail"
    assert failures[0]["error_type"] == "RateLimitError"
