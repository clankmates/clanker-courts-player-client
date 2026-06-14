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


PHASE_OPENING_TYPES = {"setup_report", "movement_phase_report", "movement_result_report"}


def latest_unseen_phase_report(
    messages: list[dict[str, Any]], *, game_id: str, seen_phase_ids: set[str]
) -> dict[str, Any] | None:
    matches = [
        message
        for message in messages
        if isinstance(message.get("body"), dict)
        and message["body"].get("type") in PHASE_OPENING_TYPES
        and message["body"].get("game_id") == game_id
        and _phase_id(message["body"]) is not None
        and _phase_id(message["body"]) not in seen_phase_ids
    ]
    if not matches:
        return None
    return sorted(matches, key=_sort_timestamp)[-1]


def _phase_id(body: dict[str, Any]) -> str | None:
    value = body.get("phase_id")
    if isinstance(value, str):
        return value
    next_phase = body.get("next_phase")
    if isinstance(next_phase, dict) and isinstance(next_phase.get("phase_id"), str):
        return next_phase["phase_id"]
    return None


def recent_peer_diplomacy(
    messages: list[dict[str, Any]], *, game_id: str, player_id: str, limit: int = 12
) -> list[dict[str, Any]]:
    """Return recent historical direct player-to-player diplomacy messages.

    Normal current games use server-brokered `message` traffic instead.
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


def recent_brokered_negotiation(
    messages: list[dict[str, Any]], *, game_id: str, player_id: str | None = None, limit: int = 12
) -> list[dict[str, Any]]:
    """Return recent server-brokered private negotiation for one game.

    Incoming messages contain `from`; locally archived sent messages contain
    `destination`. When `player_id` is supplied, sent archives are included only
    if they name that player as the destination.
    """
    matches = [
        message
        for message in messages
        if isinstance(message.get("body"), dict)
        and message["body"].get("type") == "message"
        and message["body"].get("game_id") == game_id
        and (
            isinstance(message["body"].get("from"), str)
            or (
                isinstance(message["body"].get("destination"), str)
                and (player_id is None or message["body"].get("destination") == player_id)
            )
        )
    ]
    return sorted(matches, key=_sort_timestamp)[-limit:]


def screen_brokered_negotiation(
    message: dict[str, Any],
    *,
    game_id: str,
    server_thread_id: str,
    known_players: set[str],
) -> dict[str, Any]:
    """Screen one inbound server-brokered negotiation before strategy use."""
    body = message.get("body")
    if not isinstance(body, dict):
        return _screening_result(False, "non_json_body")
    if message.get("thread_id") != server_thread_id:
        return _screening_result(False, "unexpected_thread")
    if body.get("type") != "message":
        return _screening_result(False, "wrong_type")
    if body.get("game_id") != game_id:
        return _screening_result(False, "wrong_game")
    sender = body.get("from")
    if not isinstance(sender, str) or sender.strip() == "":
        return _screening_result(False, "missing_from")
    if sender not in known_players:
        return _screening_result(False, "unknown_sender", sender=sender)
    text = body.get("body")
    if not isinstance(text, str) or text.strip() == "":
        return _screening_result(False, "empty_body", sender=sender)
    return _screening_result(True, "accepted", sender=sender)


def _screening_result(accepted: bool, reason: str, **extra: Any) -> dict[str, Any]:
    return {"accepted": accepted, "reason": reason, **extra}


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
