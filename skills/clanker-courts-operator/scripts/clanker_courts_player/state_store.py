from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .messages import raw_archive_record, unprocessed_messages


class StateStore:
    def __init__(self, state_path: str | Path) -> None:
        self.state_path = Path(state_path)
        self.base_dir = self.state_path.parent
        self.raw_messages_path = self.base_dir / "raw_messages.jsonl"

    def load(self) -> dict[str, Any]:
        with self.state_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("state file must contain a JSON object")
        return payload

    def save(self, state: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_name(f".{self.state_path.name}.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, self.state_path)

    def append_raw_message(self, message: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.raw_messages_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, sort_keys=True))
            handle.write("\n")

    def append_raw_messages(self, messages: list[dict[str, Any]]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.raw_messages_path.open("a", encoding="utf-8") as handle:
            for message in messages:
                handle.write(json.dumps(message, sort_keys=True))
                handle.write("\n")

    def apply_incremental_messages(
        self, state: dict[str, Any], messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        processed = _processed_message_ids(state)
        unseen = unprocessed_messages(messages, processed_message_ids=processed)
        if unseen:
            self.append_raw_messages([raw_archive_record(message) for message in unseen])
        for message in unseen:
            message_id = message.get("message_id")
            if isinstance(message_id, str):
                processed.add(message_id)
        updated = dict(state)
        updated["processed_message_ids"] = sorted(processed)
        self.save(updated)
        return {
            "ok": True,
            "processed": len(unseen),
            "duplicates_skipped": len(messages) - len(unseen),
            "processed_message_ids": updated["processed_message_ids"],
        }


def _processed_message_ids(state: dict[str, Any]) -> set[str]:
    value = state.get("processed_message_ids")
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}
