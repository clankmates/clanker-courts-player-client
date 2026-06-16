from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_FILE = "state.json"
RAW_MESSAGES_FILE = "raw_messages.jsonl"
SUBMITTED_COMMANDS_FILE = "submitted_commands.jsonl"
DECISION_JOURNAL_FILE = "decision_journal.jsonl"
DIPLOMACY_LEDGER_FILE = "diplomacy_ledger.jsonl"


def build_phase_context(artifact_dir: Path, *, now: datetime | None = None) -> dict[str, Any]:
    state = _read_json(artifact_dir / STATE_FILE)
    raw_messages = _read_jsonl(artifact_dir / RAW_MESSAGES_FILE)
    submitted_commands = _read_jsonl(artifact_dir / SUBMITTED_COMMANDS_FILE)
    journal = _read_jsonl(artifact_dir / DECISION_JOURNAL_FILE)
    ledger = _read_jsonl(artifact_dir / DIPLOMACY_LEDGER_FILE)

    latest_current = _as_dict(state.get("latest_current_phase_response"))
    current_phase = _as_dict(latest_current.get("current_phase")) or _as_dict(
        state.get("current_phase")
    )
    allowed_command = _as_dict(state.get("allowed_command")) or _as_dict(
        latest_current.get("allowed_command")
    )
    visible_state = _as_dict(state.get("visible_state")) or _as_dict(
        latest_current.get("visible_state")
    )
    deadline = _deadline_summary(current_phase.get("deadline_at"), now=now)

    return {
        "ok": True,
        "artifact_dir": str(artifact_dir),
        "artifact_files": {
            "state": str(artifact_dir / STATE_FILE),
            "raw_messages": str(artifact_dir / RAW_MESSAGES_FILE),
            "submitted_commands": str(artifact_dir / SUBMITTED_COMMANDS_FILE),
            "decision_journal": str(artifact_dir / DECISION_JOURNAL_FILE),
            "diplomacy_ledger": str(artifact_dir / DIPLOMACY_LEDGER_FILE),
        },
        "game": {
            "game_id": state.get("game_id"),
            "status": state.get("status"),
            "profile": state.get("profile"),
            "server": state.get("server"),
            "server_thread_id": state.get("server_thread_id"),
        },
        "player": {
            "player_id": state.get("player_id"),
            "handle_mode": state.get("handle_mode"),
            "capital_location_id": state.get("capital_location_id"),
            "players": state.get("players", []),
        },
        "current_phase": current_phase or None,
        "deadline": deadline,
        "allowed_command": allowed_command or None,
        "latest_report": state.get("latest_report") or latest_current.get("latest_report"),
        "visible_state_digest": visible_state_digest(
            visible_state,
            player_id=_string_or_none(state.get("player_id")),
            capital_location_id=_string_or_none(state.get("capital_location_id")),
        ),
        "recent_negotiation": recent_negotiation(
            raw_messages,
            game_id=_string_or_none(state.get("game_id")),
            server_thread_id=_string_or_none(state.get("server_thread_id")),
            known_players=set(_strings(state.get("players"))),
        ),
        "recent_decisions": journal[-5:],
        "recent_ledger_notes": ledger[-10:],
        "submitted_command_count": len(submitted_commands),
        "safe_fallback": _fallback_from_state(state),
        "recommended_next": _recommended_next(state, current_phase, allowed_command),
        "warnings": _warnings(state, current_phase, allowed_command),
    }


def visible_state_digest(
    visible_state: dict[str, Any],
    *,
    player_id: str | None,
    capital_location_id: str | None,
) -> dict[str, Any]:
    locations = [_as_dict(item) for item in _as_list(visible_state.get("locations"))]
    locations = [item for item in locations if item]
    graph = {
        key: _strings(value)
        for key, value in _as_dict(visible_state.get("connectivity_graph")).items()
        if isinstance(key, str)
    }
    by_id = {
        location["location_id"]: location
        for location in locations
        if isinstance(location.get("location_id"), str)
    }
    controlled = [
        location
        for location in locations
        if player_id is not None and location.get("controller") == player_id
    ]
    controlled_ids = {location["location_id"] for location in controlled}
    adjacent_ids = {
        neighbor
        for location_id in controlled_ids
        for neighbor in graph.get(location_id, [])
        if neighbor not in controlled_ids
    }
    distance_two_ids = {
        neighbor
        for location_id in adjacent_ids
        for neighbor in graph.get(location_id, [])
        if neighbor not in controlled_ids and neighbor not in adjacent_ids
    }
    for location_id in by_id:
        if location_id not in controlled_ids and location_id not in adjacent_ids:
            distance_two_ids.add(location_id)

    visible_enemies = [
        location
        for location in locations
        if isinstance(location.get("controller"), str)
        and player_id is not None
        and location.get("controller") != player_id
    ]
    capital_neighbors = graph.get(capital_location_id or "", [])
    capital_threats = [
        by_id[location_id]
        for location_id in capital_neighbors
        if location_id in by_id
        and isinstance(by_id[location_id].get("controller"), str)
        and by_id[location_id].get("controller") != player_id
    ]

    return {
        "controlled_locations": controlled,
        "controlled_location_ids": sorted(controlled_ids),
        "adjacent_location_ids": sorted(adjacent_ids),
        "distance_two_location_ids": sorted(distance_two_ids),
        "visible_enemy_locations": visible_enemies,
        "capital": by_id.get(capital_location_id) if capital_location_id else None,
        "capital_neighbor_ids": capital_neighbors,
        "visible_capital_threats": capital_threats,
        "controlled_troops_known": sum(
            location.get("troops", 0)
            for location in controlled
            if isinstance(location.get("troops"), int)
        ),
        "controlled_city_count": sum(
            1 for location in controlled if _reported_type(location) in {"city", "capital"}
        ),
        "controlled_town_count": sum(
            1 for location in controlled if _reported_type(location) == "town"
        ),
        "visible_score_estimate": sum(_score_value(location) for location in controlled),
    }


def recent_negotiation(
    messages: list[dict[str, Any]],
    *,
    game_id: str | None,
    server_thread_id: str | None,
    known_players: set[str],
    limit: int = 12,
) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []
    if game_id is None:
        return {"accepted": [], "rejected": [], "sent": []}

    for message in messages:
        body = _as_dict(message.get("body"))
        if body.get("type") != "message" or body.get("game_id") != game_id:
            continue
        if isinstance(body.get("destination"), str):
            sent.append(_compact_message(message, body, "sent"))
            continue
        screening = _screen_message(
            message,
            body,
            game_id=game_id,
            server_thread_id=server_thread_id,
            known_players=known_players,
        )
        compact = {**_compact_message(message, body, "received"), "screening": screening}
        if screening["accepted"]:
            accepted.append(compact)
        else:
            rejected.append(compact)

    return {
        "accepted": accepted[-limit:],
        "rejected": rejected[-limit:],
        "sent": sent[-limit:],
    }


def safe_fallback_orders(artifact_dir: Path) -> dict[str, Any]:
    state = _read_json(artifact_dir / STATE_FILE)
    return {"ok": True, **_fallback_from_state(state)}


def append_decision_journal(
    artifact_dir: Path,
    *,
    phase_id: str,
    rationale: str,
    orders: Any,
    risks: Any,
    promises_made: Any,
    promises_received: Any,
) -> dict[str, Any]:
    state = _read_json(artifact_dir / STATE_FILE)
    record = {
        "local_timestamp": _utc_now(),
        "game_id": state.get("game_id"),
        "phase_id": phase_id,
        "turn": state.get("turn"),
        "phase": state.get("phase"),
        "player_id": state.get("player_id"),
        "rationale": rationale,
        "orders": orders,
        "risks": risks,
        "promises_made": promises_made,
        "promises_received": promises_received,
    }
    _append_jsonl(artifact_dir / DECISION_JOURNAL_FILE, record)
    return record


def append_ledger_note(
    artifact_dir: Path,
    *,
    player: str,
    kind: str,
    note: str,
    phase_id: str | None,
) -> dict[str, Any]:
    state = _read_json(artifact_dir / STATE_FILE)
    record = {
        "local_timestamp": _utc_now(),
        "game_id": state.get("game_id"),
        "phase_id": phase_id or state.get("phase_id"),
        "turn": state.get("turn"),
        "phase": state.get("phase"),
        "player": player,
        "kind": kind,
        "note": note,
    }
    _append_jsonl(artifact_dir / DIPLOMACY_LEDGER_FILE, record)
    return record


def _fallback_from_state(state: dict[str, Any]) -> dict[str, Any]:
    latest_current = _as_dict(state.get("latest_current_phase_response"))
    current_phase = _as_dict(latest_current.get("current_phase")) or _as_dict(
        state.get("current_phase")
    )
    allowed_command = _as_dict(state.get("allowed_command")) or _as_dict(
        latest_current.get("allowed_command")
    )
    phase = current_phase.get("phase") or state.get("phase")
    accepting = allowed_command.get("accepting")
    safe_to_submit = allowed_command.get("command") == "order_package" and accepting is not False
    if current_phase.get("status") == "expired":
        safe_to_submit = False

    if phase == "reinforcement":
        reason = "empty reinforcement package uses the server default: reinforces the capital"
    elif phase == "movement":
        reason = "empty movement package uses the server default: leave all troops in place"
    else:
        reason = "phase is unknown; empty package is the only strategy-neutral fallback"

    return {
        "safe_to_submit": safe_to_submit,
        "phase_id": current_phase.get("phase_id") or state.get("phase_id"),
        "phase": phase,
        "orders": [],
        "orders_json": "[]",
        "reason": reason,
    }


def _recommended_next(
    state: dict[str, Any], current_phase: dict[str, Any], allowed_command: dict[str, Any]
) -> dict[str, Any]:
    if state.get("status") == "ended":
        return {"kind": "stop_or_final_report", "reason": "state is ended"}
    if current_phase.get("status") == "expired":
        return {"kind": "watch", "reason": "current phase is expired"}
    if allowed_command.get("command") == "get_after_game_report":
        return {"kind": "final_report", "reason": "server says after-game report is available"}
    if (
        allowed_command.get("command") == "order_package"
        and allowed_command.get("accepting") is not False
    ):
        return {"kind": "choose_and_submit_orders", "reason": "current phase accepts orders"}
    return {"kind": "current", "reason": "refresh server-owned current phase before acting"}


def _warnings(
    state: dict[str, Any], current_phase: dict[str, Any], allowed_command: dict[str, Any]
) -> list[str]:
    warnings: list[str] = []
    if not state.get("latest_current_phase_response"):
        warnings.append("run operator current before preparing orders")
    if current_phase.get("status") == "expired":
        warnings.append("do not submit orders for an expired phase")
    if allowed_command.get("command") != "order_package" and state.get("status") != "ended":
        warnings.append("allowed command is not order_package")
    if state.get("stale_rejection_recovery"):
        warnings.append("stale_phase recovery is present; run operator current and rebuild orders")
    return warnings


def _deadline_summary(deadline_at: Any, *, now: datetime | None) -> dict[str, Any]:
    if not isinstance(deadline_at, str) or deadline_at.strip() == "":
        return {"deadline_at": None, "seconds_remaining": None, "expired": None}
    parsed = _parse_datetime(deadline_at)
    if parsed is None:
        return {"deadline_at": deadline_at, "seconds_remaining": None, "expired": None}
    current = now or datetime.now(UTC)
    seconds = int((parsed - current).total_seconds())
    return {"deadline_at": deadline_at, "seconds_remaining": seconds, "expired": seconds <= 0}


def _screen_message(
    message: dict[str, Any],
    body: dict[str, Any],
    *,
    game_id: str,
    server_thread_id: str | None,
    known_players: set[str],
) -> dict[str, Any]:
    if server_thread_id is not None and message.get("thread_id") != server_thread_id:
        return {"accepted": False, "reason": "unexpected_thread"}
    if body.get("game_id") != game_id:
        return {"accepted": False, "reason": "wrong_game"}
    sender = body.get("from")
    if not isinstance(sender, str) or sender.strip() == "":
        return {"accepted": False, "reason": "missing_from"}
    if known_players and sender not in known_players:
        return {"accepted": False, "reason": "unknown_sender", "sender": sender}
    text = body.get("body")
    if not isinstance(text, str) or text.strip() == "":
        return {"accepted": False, "reason": "empty_body", "sender": sender}
    return {"accepted": True, "reason": "accepted", "sender": sender}


def _compact_message(
    message: dict[str, Any], body: dict[str, Any], direction: str
) -> dict[str, Any]:
    return {
        "message_id": message.get("message_id"),
        "thread_id": message.get("thread_id"),
        "timestamp": message.get("server_timestamp") or message.get("timestamp"),
        "direction": direction,
        "from": body.get("from"),
        "destination": body.get("destination"),
        "body": body.get("body"),
    }


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip() == "":
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")


def _reported_type(location: dict[str, Any]) -> str | None:
    value = location.get("reported_location_type") or location.get("kind")
    return value if isinstance(value, str) else None


def _score_value(location: dict[str, Any]) -> int:
    reported = _reported_type(location)
    if reported in {"city", "capital"}:
        return 3
    if reported == "town":
        return 1
    return 0


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
