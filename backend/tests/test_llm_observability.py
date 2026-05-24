import json
import logging

import pytest

from app.services import llm_observability


def test_sanitize_messages_replaces_images_with_placeholder():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "extract pages"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,def"}},
            ],
        }
    ]

    sanitized = llm_observability.sanitize_messages_for_debug(messages)

    content = sanitized[0]["content"]
    assert content[0]["type"] == "text"
    assert content[-1] == {"type": "image_placeholder", "count": 2}


def test_log_llm_event_emits_json(caplog):
    caplog.set_level(logging.INFO, logger="app.services.llm_observability")

    llm_observability.log_llm_event("llm_call_success", {"document_id": "doc-1", "operation": "extraction"})

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].message)
    assert payload["event"] == "llm_call_success"
    assert payload["document_id"] == "doc-1"


def test_write_debug_artifact_skips_when_disabled(tmp_path):
    llm_observability.write_debug_artifact(
        str(tmp_path),
        "doc-1",
        "test.json",
        {"ok": True},
        enabled=False,
    )

    assert not (tmp_path / "debug").exists()


def test_write_debug_artifact_writes_when_enabled(tmp_path):
    llm_observability.write_debug_artifact(
        str(tmp_path),
        "doc-1",
        "batch-1.json",
        {"ok": True},
        enabled=True,
    )

    path = tmp_path / "debug" / "doc-1" / "batch-1.json"
    assert path.is_file()
    assert json.loads(path.read_text())["ok"] is True
