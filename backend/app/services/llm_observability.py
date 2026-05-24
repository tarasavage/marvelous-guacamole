import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_messages_for_debug(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role == "user" and isinstance(content, list):
            parts: list[dict[str, Any]] = []
            image_count = 0
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    image_count += 1
                else:
                    parts.append(part)
            if image_count:
                parts.append({"type": "image_placeholder", "count": image_count})
            sanitized.append({"role": role, "content": parts})
        else:
            sanitized.append(message)
    return sanitized


def log_llm_event(event: str, payload: dict[str, Any]) -> None:
    body = {"event": event, **payload}
    logger.info(json.dumps(body, default=str))


def write_debug_artifact(
    data_dir: str,
    document_id: str,
    filename: str,
    payload: dict[str, Any],
    *,
    enabled: bool,
) -> None:
    if not enabled or not document_id:
        return
    directory = Path(data_dir) / "debug" / document_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
