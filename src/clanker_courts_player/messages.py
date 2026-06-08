from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

TIMESTAMP_FIELDS = ("created_at", "createdAt", "inserted_at", "insertedAt", "timestamp")


def decode_clankmates_message(message: dict[str, Any]) -> dict[str, Any]:
    attributes = message.get("attributes")
    raw_body = attributes.get("body") if isinstance(attributes, dict) else None
    if raw_body is None:
        raw_body = message.get("body")
    body: Any = raw_body
    if isinstance(raw_body, str):
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = raw_body

    return {
        "message_id": message.get("id") or message.get("message_id"),
        "thread_id": message.get("thread_id") or message.get("threadId"),
        "timestamp": _message_timestamp(message),
        "body": body,
        "raw": message,
    }


PHASE_OPENING_TYPES = {"reinforcement_report", "movement_visibility_report"}


def latest_unseen_phase_report(
    messages: list[dict[str, Any]], *, game_id: str, seen_phase_ids: set[str]
) -> dict[str, Any] | None:
    matches = [
        message
        for message in messages
        if isinstance(message.get("body"), dict)
        and message["body"].get("type") in PHASE_OPENING_TYPES
        and message["body"].get("game_id") == game_id
        and message["body"].get("phase_id") not in seen_phase_ids
    ]
    if not matches:
        return None
    return sorted(matches, key=_sort_timestamp)[-1]


def recent_peer_diplomacy(
    messages: list[dict[str, Any]], *, game_id: str, player_id: str, limit: int = 12
) -> list[dict[str, Any]]:
    """Return recent direct player-to-player diplomacy messages for one game.

    These messages are Clankmates peer inbox bodies, not game-server commands.
    """
    matches = [
        message
        for message in messages
        if isinstance(message.get("body"), dict)
        and message["body"].get("type") == "diplomacy_message"
        and message["body"].get("game_id") == game_id
        and (
            message["body"].get("from_player_id") == player_id
            or message["body"].get("to_player_id") == player_id
        )
    ]
    return sorted(matches, key=_sort_timestamp)[-limit:]


def _message_timestamp(message: dict[str, Any]) -> str | None:
    for field in TIMESTAMP_FIELDS:
        value = message.get(field)
        if isinstance(value, str):
            return value
    return None


def _sort_timestamp(message: dict[str, Any]) -> datetime:
    value = message.get("timestamp")
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=UTC)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
