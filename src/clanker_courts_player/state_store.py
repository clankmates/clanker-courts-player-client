from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, state_path: str | Path) -> None:
        self.state_path = Path(state_path)
        self.base_dir = self.state_path.parent
        self.raw_messages_path = self.base_dir / "raw_messages.jsonl"
        self.events_path = self.base_dir / "events.jsonl"

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

    def append_event(self, event: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True))
            handle.write("\n")
