from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .messages import raw_archive_record, stale_rejection_recovery_hints, unprocessed_messages


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
        for message in unseen:
            _apply_message_body(updated, message.get("body"))
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


def _apply_message_body(state: dict[str, Any], body: Any) -> None:
    if not isinstance(body, dict):
        return

    body_type = body.get("type")
    if body_type in {"setup_report", "movement_phase_report"}:
        _apply_open_phase_report(state, body)
    elif body_type == "movement_result_report":
        state["latest_movement_result_report"] = body
        status = body.get("status")
        if isinstance(status, dict) and status.get("status") == "ended":
            state["status"] = "ended"
            _apply_final_outcome(state, status)
        next_phase = body.get("next_phase")
        if isinstance(next_phase, dict):
            _apply_phase(state, next_phase)
        if isinstance(body.get("visibility"), dict):
            state["visible_state"] = body["visibility"]
    elif body_type == "after_game_report":
        state["latest_after_game_report"] = body
        state["status"] = "ended"
        _apply_final_outcome(state, body)
    elif body_type == "order_rejected":
        hints = stale_rejection_recovery_hints(body)
        if hints is not None:
            state["stale_rejection_recovery"] = hints
    elif "current_phase" in body and "allowed_command" in body:
        _apply_current_phase_response(state, body)


def _apply_open_phase_report(state: dict[str, Any], body: dict[str, Any]) -> None:
    key = (
        "latest_setup_report"
        if body.get("type") == "setup_report"
        else "latest_movement_phase_report"
    )
    state[key] = body
    _apply_phase(state, body)
    if isinstance(body.get("game_id"), str):
        state["game_id"] = body["game_id"]
    if isinstance(body.get("player"), str):
        state["player_id"] = body["player"]
    if isinstance(body.get("handle_mode"), str):
        state["handle_mode"] = body["handle_mode"]
    if isinstance(body.get("capital_location_id"), str):
        state["capital_location_id"] = body["capital_location_id"]
    if isinstance(body.get("players"), list):
        state["players"] = body["players"]
    if isinstance(body.get("visibility"), dict):
        state["visible_state"] = body["visibility"]


def _apply_current_phase_response(state: dict[str, Any], body: dict[str, Any]) -> None:
    state["latest_current_phase_response"] = body
    current_phase = body.get("current_phase")
    if isinstance(current_phase, dict):
        _apply_phase(state, current_phase)
        if isinstance(current_phase.get("status"), str):
            state["phase_status"] = current_phase["status"]
    else:
        state["current_phase"] = None
        state["status"] = "ended"
    if isinstance(body.get("visible_state"), dict):
        state["visible_state"] = body["visible_state"]
    if isinstance(body.get("allowed_command"), dict):
        state["allowed_command"] = body["allowed_command"]
    if isinstance(body.get("latest_report"), dict):
        state["latest_report"] = body["latest_report"]


def _apply_phase(state: dict[str, Any], payload: dict[str, Any]) -> None:
    phase = {
        "phase_id": payload.get("phase_id"),
        "turn": payload.get("turn"),
        "phase": payload.get("phase"),
    }
    state["current_phase"] = {
        key: value
        for key, value in phase.items()
        if isinstance(value, str | int)
    }
    if isinstance(payload.get("phase_id"), str):
        state["phase_id"] = payload["phase_id"]
    if isinstance(payload.get("turn"), int):
        state["turn"] = payload["turn"]
    if isinstance(payload.get("phase"), str):
        state["phase"] = payload["phase"]


def _apply_final_outcome(state: dict[str, Any], payload: dict[str, Any]) -> None:
    for field in (
        "winners",
        "outcome_reason",
        "score_rationale",
        "final_standings",
        "match_points",
    ):
        if field in payload:
            state[field] = payload[field]
