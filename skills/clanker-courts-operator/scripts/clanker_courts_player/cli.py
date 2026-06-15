from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def _parse_json_array(value: str, *, field: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise argparse.ArgumentTypeError(f"{field} must be a JSON array")
    return parsed


def _clankmates_client():
    from .clankmates import ClankmatesClient

    return ClankmatesClient()


def _store(artifact_dir: str):
    from .state_store import StateStore

    return StateStore(Path(artifact_dir) / "state.json")


def _missing_thread_error(store) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": "missing_server_thread",
            "message": "state.json does not contain server_thread_id",
            "recovery": "run recover-thread with the known server thread id",
        },
        "state": str(store.state_path),
    }


def _load_state_with_thread(store) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        state = store.load()
    except FileNotFoundError:
        return None, _missing_thread_error(store)

    thread_id = state.get("server_thread_id")
    if not isinstance(thread_id, str) or thread_id.strip() == "":
        return state, _missing_thread_error(store)
    return state, None


def _thread_id_from_send_result(result: dict[str, Any]) -> str | None:
    for key in ("thread_id", "threadId"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value
    data = result.get("data")
    if isinstance(data, dict):
        for key in ("thread_id", "threadId"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _run_clankmates(
    action: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    from .clankmates import ClankmatesError

    try:
        return action(), None
    except ClankmatesError as exc:
        return None, {
            "ok": False,
            "error": {
                "code": "clankm_failed",
                "command": exc.command,
                "returncode": exc.returncode,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            },
        }


def _record_and_print_command(
    *,
    store,
    state: dict[str, Any],
    command_type: str,
    body: dict[str, Any],
    action: Callable[[], dict[str, Any]],
    thread_id: str | None = None,
    recipient: str | None = None,
) -> int:
    result, error = _run_clankmates(action)
    store.append_submitted_command(
        {
            "command_type": command_type,
            "game_id": body.get("game_id"),
            "thread_id": thread_id,
            "recipient": recipient,
            "body": body,
            "result": result,
            "ok": error is None,
        }
    )
    if error is not None:
        _print_json(error)
        return 1

    _print_json(
        {
            "ok": True,
            "action": command_type,
            "game_id": body.get("game_id"),
            "server_thread_id": thread_id or state.get("server_thread_id"),
            "result": result,
        }
    )
    return 0


def _join(args: argparse.Namespace) -> int:
    store = _store(args.artifact_dir)
    body = {"type": "join_game", "game_id": args.game_id}
    result, error = _run_clankmates(
        lambda: _clankmates_client().send(args.profile, args.server, body)
    )
    store.append_submitted_command(
        {
            "command_type": "join_game",
            "game_id": args.game_id,
            "recipient": args.server,
            "body": body,
            "result": result,
            "ok": error is None,
        }
    )
    if error is not None:
        _print_json(error)
        return 1

    thread_id = _thread_id_from_send_result(result or {})
    if thread_id is None:
        _print_json(
            {
                "ok": False,
                "error": {
                    "code": "missing_thread_id",
                    "message": "clankm send result did not include thread_id",
                    "result": result,
                },
            }
        )
        return 1

    state = store.initialize_session(
        profile=args.profile,
        server=args.server,
        game_id=args.game_id,
        server_thread_id=thread_id,
        join_result=result or {},
    )
    _print_json(
        {
            "ok": True,
            "action": "join_game",
            "game_id": args.game_id,
            "server_thread_id": thread_id,
            "state": str(store.state_path),
            "status": state.get("status"),
        }
    )
    return 0


def _watch(args: argparse.Namespace) -> int:
    from .clankmates import ClankmatesError
    from .messages import decode_clankmates_message

    store = _store(args.artifact_dir)
    state, error = _load_state_with_thread(store)
    if error is not None:
        _print_json(error)
        return 1

    assert state is not None
    thread_id = state["server_thread_id"]
    try:
        records = _clankmates_client().iter_watch_messages(
            state["profile"],
            thread_id,
            once=args.once,
        )
        processed = 0
        duplicates_skipped = 0
        records_seen = 0
        for record in records:
            records_seen += 1
            message = decode_clankmates_message(record)
            state = store.load()
            apply_result = store.apply_incremental_messages(state, [message])
            processed += apply_result["processed"]
            duplicates_skipped += apply_result["duplicates_skipped"]
            _print_json(
                {
                    "ok": True,
                    "event": "message",
                    "game_id": state.get("game_id"),
                    "server_thread_id": thread_id,
                    "processed": apply_result["processed"],
                    "duplicates_skipped": apply_result["duplicates_skipped"],
                    "no_messages": False,
                }
            )
    except ClankmatesError as exc:
        payload = exc.to_dict()
        code = "invalid_clankm_json" if payload.get("decode_error") is not None else "clankm_failed"
        _print_json({"ok": False, "error": {"code": code, **payload}})
        return 1

    _print_json(
        {
            "ok": True,
            "event": "watch_complete",
            "game_id": state.get("game_id"),
            "server_thread_id": thread_id,
            "records_seen": records_seen,
            "processed": processed,
            "duplicates_skipped": duplicates_skipped,
            "no_messages": records_seen == 0 or processed == 0,
        }
    )
    return 0


def _reply_from_state(
    args: argparse.Namespace, command_type: str, partial_body: dict[str, Any]
) -> int:
    store = _store(args.artifact_dir)
    state, error = _load_state_with_thread(store)
    if error is not None:
        _print_json(error)
        return 1

    assert state is not None
    body = {**partial_body, "game_id": state["game_id"]}
    thread_id = state["server_thread_id"]
    return _record_and_print_command(
        store=store,
        state=state,
        command_type=command_type,
        body=body,
        thread_id=thread_id,
        action=lambda: _clankmates_client().reply(state["profile"], thread_id, body),
    )


def _ready(args: argparse.Namespace) -> int:
    return _reply_from_state(args, "ready_to_start", {"type": "ready_to_start"})


def _current(args: argparse.Namespace) -> int:
    body: dict[str, Any] = {"type": "get_current_phase"}
    if args.request_id is not None:
        body["request_id"] = args.request_id
    return _reply_from_state(args, "get_current_phase", body)


def _orders(args: argparse.Namespace) -> int:
    return _reply_from_state(
        args,
        "order_package",
        {
            "type": "order_package",
            "phase_id": args.phase_id,
            "orders": _parse_json_array(args.orders_json, field="orders"),
        },
    )


def _message(args: argparse.Namespace) -> int:
    return _reply_from_state(
        args,
        "message",
        {
            "type": "message",
            "destination": args.destination,
            "body": args.body,
        },
    )


def _final_report(args: argparse.Namespace) -> int:
    body: dict[str, Any] = {"type": "get_after_game_report"}
    if args.request_id is not None:
        body["request_id"] = args.request_id
    return _reply_from_state(args, "get_after_game_report", body)


def _status(args: argparse.Namespace) -> int:
    store = _store(args.artifact_dir)
    try:
        state = store.load()
    except FileNotFoundError:
        _print_json(
            {
                "ok": False,
                "error": {"code": "missing_state"},
                "state": str(store.state_path),
            }
        )
        return 1

    _print_json(
        {
            "ok": True,
            "state": str(store.state_path),
            "game_id": state.get("game_id"),
            "profile": state.get("profile"),
            "server": state.get("server"),
            "server_thread_id": state.get("server_thread_id"),
            "status": state.get("status"),
            "player_id": state.get("player_id"),
            "turn": state.get("turn"),
            "phase": state.get("phase"),
            "phase_id": state.get("phase_id"),
            "phase_status": state.get("phase_status"),
            "processed_messages": len(state.get("processed_message_ids", [])),
        }
    )
    return 0


def _recover_thread(args: argparse.Namespace) -> int:
    store = _store(args.artifact_dir)
    try:
        state = store.load()
    except FileNotFoundError:
        state = {
            "schema_version": 1,
            "processed_message_ids": [],
        }
    state["schema_version"] = state.get("schema_version", 1)
    state["profile"] = args.profile
    state["server"] = args.server
    state["game_id"] = args.game_id
    state.setdefault("processed_message_ids", [])
    state["server_thread_id"] = args.thread_id
    store.save(state)
    _print_json(
        {
            "ok": True,
            "action": "recover_thread",
            "game_id": state.get("game_id"),
            "server_thread_id": args.thread_id,
            "state": str(store.state_path),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clanker-courts")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    join = subparsers.add_parser("join", help="join one game and persist the server thread")
    join.add_argument("--profile", required=True)
    join.add_argument("--server", required=True)
    join.add_argument("--game-id", required=True)
    join.add_argument("--artifact-dir", required=True)
    join.set_defaults(func=_join)

    watch = subparsers.add_parser("watch", help="watch the saved server thread")
    watch.add_argument("--artifact-dir", required=True)
    watch.add_argument("--once", action="store_true")
    watch.set_defaults(func=_watch)

    ready = subparsers.add_parser("ready", help="reply ready_to_start on the saved thread")
    ready.add_argument("--artifact-dir", required=True)
    ready.set_defaults(func=_ready)

    current = subparsers.add_parser("current", help="request current phase/state")
    current.add_argument("--artifact-dir", required=True)
    current.add_argument("--request-id")
    current.set_defaults(func=_current)

    orders = subparsers.add_parser("orders", help="submit an order_package")
    orders.add_argument("--artifact-dir", required=True)
    orders.add_argument("--phase-id", required=True)
    orders.add_argument("--orders-json", default="[]")
    orders.set_defaults(func=_orders)

    message = subparsers.add_parser("message", help="send brokered negotiation")
    message.add_argument("--artifact-dir", required=True)
    message.add_argument("--destination", required=True)
    message.add_argument("--body", required=True)
    message.set_defaults(func=_message)

    final_report = subparsers.add_parser("final-report", help="request the after-game report")
    final_report.add_argument("--artifact-dir", required=True)
    final_report.add_argument("--request-id")
    final_report.set_defaults(func=_final_report)

    status = subparsers.add_parser("status", help="print concise saved state")
    status.add_argument("--artifact-dir", required=True)
    status.set_defaults(func=_status)

    recover = subparsers.add_parser(
        "recover-thread", help="store a known server thread after local state loss"
    )
    recover.add_argument("--artifact-dir", required=True)
    recover.add_argument("--thread-id", required=True)
    recover.add_argument("--profile", required=True)
    recover.add_argument("--server", required=True)
    recover.add_argument("--game-id", required=True)
    recover.set_defaults(func=_recover_thread)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
