from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .messages import decode_clankmates_message
from .models import parse_message_body
from .state_store import StateStore


def join_game(
    *,
    client: Any,
    profile: str,
    base_url: str,
    server: str,
    game_id: str,
    store: StateStore,
) -> dict[str, Any]:
    whoami = client.whoami(profile)
    handle = _extract_handle(whoami)
    body = {"type": "join_game", "game_id": game_id, "handle": handle}
    send_response = client.send(profile, server, body)
    thread_id = extract_thread_id(send_response)
    if thread_id is None:
        raise ValueError("send response did not include a server thread_id")

    state = initial_state(
        game_id=game_id,
        server=server,
        thread_id=thread_id,
        base_url=base_url,
        profile=profile,
        handle=handle,
    )
    store.save(state)
    return {
        "ok": True,
        "game_id": game_id,
        "profile": profile,
        "handle": handle,
        "server": server,
        "thread_id": thread_id,
        "send_response": send_response,
    }


def poll_server_thread(*, client: Any, store: StateStore, limit: int) -> dict[str, Any]:
    state = store.load()
    game_id = state.get("game_id")
    profile = _nested_str(state, "clankmates", "profile")
    thread_id = _nested_str(state, "server", "thread_id")
    if not isinstance(game_id, str) or not game_id:
        raise ValueError("state.game_id is required")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("state.server.thread_id is required")
    if not isinstance(profile, str) or not profile:
        raise ValueError("state.clankmates.profile is required")

    response = client.show_thread(profile, thread_id, limit=limit)
    messages = _extract_messages(response)

    seen = state.setdefault("seen", {})
    seen_message_ids = list(seen.get("message_ids") or [])
    seen_set = {message_id for message_id in seen_message_ids if isinstance(message_id, str)}
    decoded_matching: list[dict[str, Any]] = []
    ignored_duplicates: list[str] = []
    ignored_unrelated: list[str] = []

    for raw_message in messages:
        store.append_raw_message(raw_message)
        decoded = decode_clankmates_message(raw_message)
        message_id = decoded.get("message_id")
        if isinstance(message_id, str) and message_id in seen_set:
            ignored_duplicates.append(message_id)
            continue
        body = decoded.get("body")
        if not isinstance(body, dict):
            continue
        if body.get("game_id") != game_id:
            if isinstance(message_id, str):
                ignored_unrelated.append(message_id)
            continue
        if body.get("type") not in {"join_ack", "game_started", "phase_request"}:
            continue
        decoded_matching.append(decoded)
        if isinstance(message_id, str):
            seen_set.add(message_id)
            seen_message_ids.append(message_id)

    events = _process_decoded_events(state, decoded_matching)
    for event in events:
        store.append_event(event)

    seen["message_ids"] = seen_message_ids
    seen.setdefault("request_ids", [])
    state["updated_at"] = _now_iso()
    store.save(state)

    return {
        "ok": True,
        "game_id": game_id,
        "thread_id": thread_id,
        "processed": len(decoded_matching),
        "ignored": {
            "duplicate_message_ids": ignored_duplicates,
            "unrelated_game_ids": ignored_unrelated,
        },
        "events": events,
        "state_path": str(store.state_path),
    }


def initial_state(
    *,
    game_id: str,
    server: str,
    thread_id: str,
    base_url: str,
    profile: str,
    handle: str,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "schema_version": 1,
        "game_id": game_id,
        "server": {"recipient": server, "thread_id": thread_id, "base_url": base_url},
        "clankmates": {"profile": profile, "handle": handle},
        "player": {},
        "phase": {},
        "seen": {"message_ids": [], "request_ids": []},
        "reports": [],
        "latest_visible_report": None,
        "submissions": [],
        "diplomacy": {"sent": [], "received": []},
        "promises": {"made": [], "received": [], "resolved": []},
        "opponents": {},
        "current_plan": None,
        "created_at": now,
        "updated_at": now,
    }


def extract_thread_id(send_response: dict[str, Any]) -> str | None:
    candidates = [
        send_response.get("thread_id"),
        send_response.get("threadId"),
        _nested_str(send_response, "thread", "id"),
        _nested_str(send_response, "data", "thread_id"),
        _nested_str(send_response, "message", "thread_id"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _process_decoded_events(
    state: dict[str, Any], decoded_messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    join_ack_messages: list[dict[str, Any]] = []
    game_started_messages: list[dict[str, Any]] = []
    phase_request_messages: list[dict[str, Any]] = []

    for decoded in sorted(decoded_messages, key=lambda message: message.get("timestamp") or ""):
        body = decoded.get("body")
        if not isinstance(body, dict):
            continue
        try:
            parsed = parse_message_body(body).model_dump()
        except Exception:
            continue
        message_type = parsed.get("type")
        if message_type == "join_ack":
            join_ack_messages.append({**decoded, "parsed_body": parsed})
        elif message_type == "game_started":
            game_started_messages.append({**decoded, "parsed_body": parsed})
        elif message_type == "phase_request":
            phase_request_messages.append({**decoded, "parsed_body": parsed})

    events: list[dict[str, Any]] = []

    for decoded in join_ack_messages:
        body = decoded["parsed_body"]
        state["join"] = {
            "status": body.get("status"),
            "joined": body.get("joined"),
            "required": body.get("required"),
        }
        events.append(_event(decoded, body))

    for decoded in game_started_messages:
        body = decoded["parsed_body"]
        _apply_game_started(state, body)
        events.append(_event(decoded, body))

    latest_phase = phase_request_messages[-1] if phase_request_messages else None
    if latest_phase is not None:
        body = latest_phase["parsed_body"]
        _apply_phase_request(state, body)
        events.append(_event(latest_phase, body))

    return events


def _apply_game_started(state: dict[str, Any], body: dict[str, Any]) -> None:
    player = state.setdefault("player", {})
    player["player_id"] = body.get("player_id")
    reports = body.get("reports") if isinstance(body.get("reports"), list) else []
    state["reports"] = reports
    latest_visible = reports[-1] if reports else None
    state["latest_visible_report"] = latest_visible
    if isinstance(body.get("status"), dict):
        status = body["status"]
        state["status"] = status
        phase = state.setdefault("phase", {})
        if isinstance(status.get("turn"), int):
            phase["turn"] = status["turn"]
        if isinstance(status.get("phase"), str):
            phase["phase"] = status["phase"]
    _apply_report_player_metadata(player, reports)


def _apply_phase_request(state: dict[str, Any], body: dict[str, Any]) -> None:
    state["phase"] = {
        "turn": body.get("turn"),
        "phase": body.get("phase"),
        "request_id": body.get("request_id"),
        "deadline_ms": body.get("deadline_ms"),
    }
    player = state.setdefault("player", {})
    if isinstance(body.get("player_id"), str):
        player["player_id"] = body["player_id"]
    reports = body.get("reports") if isinstance(body.get("reports"), list) else []
    state["reports"] = reports
    state["latest_visible_report"] = reports[-1] if reports else None
    if isinstance(body.get("status"), dict):
        state["status"] = body["status"]
    _apply_report_player_metadata(player, reports)


def _apply_report_player_metadata(player: dict[str, Any], reports: list[dict[str, Any]]) -> None:
    known_players: list[str] = list(player.get("known_players") or [])
    for report in reports:
        if not isinstance(report, dict):
            continue
        if isinstance(report.get("capital_location_id"), str):
            player["capital_location_id"] = report["capital_location_id"]
        for player_id in _report_player_ids(report):
            if player_id not in known_players:
                known_players.append(player_id)
    if known_players:
        player["known_players"] = known_players


def _report_player_ids(report: dict[str, Any]) -> list[str]:
    players = report.get("players")
    if not isinstance(players, list):
        return []
    ids: list[str] = []
    for player in players:
        if isinstance(player, str):
            ids.append(player)
        elif isinstance(player, dict):
            player_id = player.get("player_id") or player.get("id")
            if isinstance(player_id, str):
                ids.append(player_id)
    return ids


def _event(decoded: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": body.get("type"),
        "message_id": decoded.get("message_id"),
        "thread_id": decoded.get("thread_id"),
        "timestamp": decoded.get("timestamp"),
        "body": body,
    }


def _extract_handle(whoami: dict[str, Any]) -> str:
    for field in ("handle", "username", "name"):
        value = whoami.get(field)
        if isinstance(value, str) and value:
            return value
    user = whoami.get("user")
    if isinstance(user, dict):
        for field in ("handle", "username", "name"):
            value = user.get(field)
            if isinstance(value, str) and value:
                return value
    raise ValueError("whoami response did not include a handle")


def _extract_messages(response: dict[str, Any]) -> list[dict[str, Any]]:
    messages = response.get("messages")
    if isinstance(messages, list):
        return [message for message in messages if isinstance(message, dict)]
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return [message for message in data["messages"] if isinstance(message, dict)]
    thread = response.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("messages"), list):
        return [message for message in thread["messages"] if isinstance(message, dict)]
    return []


def _nested_str(payload: dict[str, Any], *path: str) -> str | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
