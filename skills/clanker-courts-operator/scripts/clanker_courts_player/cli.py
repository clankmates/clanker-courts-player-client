from __future__ import annotations

import argparse
import json
from typing import Any

COMMANDS = [
    "preflight",
    "join",
    "poll",
    "ready",
    "submit-orders",
    "send-message",
    "send-diplomacy",
    "send-peer-diplomacy",
    "archive-thread",
    "state",
    "operator-context",
]


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def _parse_json_object(value: str, *, field: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError(f"{field} must be a JSON object")
    return parsed


def _parse_json_array(value: str, *, field: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise argparse.ArgumentTypeError(f"{field} must be a JSON array")
    return parsed


def _clankmates_client():
    from .clankmates import ClankmatesClient

    return ClankmatesClient()


def _send_or_preview(
    *,
    profile: str,
    recipient: str,
    body: dict[str, Any],
    dry_run: bool,
) -> int:
    if dry_run:
        _print_json({"ok": True, "dry_run": True, "recipient": recipient, "body": body})
        return 0

    from .clankmates import ClankmatesError

    try:
        result = _clankmates_client().send(profile, recipient, body)
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    _print_json({"ok": True, "recipient": recipient, "body": body, "result": result})
    return 0


def _reply_or_preview(
    *,
    profile: str,
    thread_id: str,
    body: dict[str, Any],
    dry_run: bool,
) -> int:
    if dry_run:
        _print_json({"ok": True, "dry_run": True, "thread_id": thread_id, "body": body})
        return 0

    from .clankmates import ClankmatesError

    try:
        result = _clankmates_client().reply(profile, thread_id, body)
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    _print_json({"ok": True, "thread_id": thread_id, "body": body, "result": result})
    return 0


def _preflight(args: argparse.Namespace) -> int:
    if args.dry_run:
        _print_json(
            {
                "ok": True,
                "profile": args.profile,
                "base_url": args.base_url,
                "dry_run": True,
                "planned_checks": ["clankm", "profile", "auth", "inbox"],
            }
        )
        return 0

    from .clankmates import ClankmatesError

    client = _clankmates_client()
    try:
        whoami = client.whoami(args.profile)
        client.list_threads(args.profile)
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    _print_json(
        {
            "ok": True,
            "profile": args.profile,
            "base_url": args.base_url,
            "clankm_version": "present",
            "whoami": whoami,
            "inbox_readable": True,
        }
    )
    return 0


def _join(args: argparse.Namespace) -> int:
    body = {"type": "join_game", "game_id": args.game_id}
    return _send_or_preview(
        profile=args.profile,
        recipient=args.server,
        body=body,
        dry_run=args.dry_run,
    )


def _ready(args: argparse.Namespace) -> int:
    body = {
        "type": "ready_to_start",
        "game_id": args.game_id,
    }
    return _reply_or_preview(
        profile=args.profile,
        thread_id=args.thread_id,
        body=body,
        dry_run=args.dry_run,
    )


def _submit_orders(args: argparse.Namespace) -> int:
    body = {
        "type": "order_package",
        "game_id": args.game_id,
        "phase_id": args.phase_id,
        "orders": _parse_json_array(args.orders_json, field="orders"),
    }
    return _reply_or_preview(
        profile=args.profile,
        thread_id=args.thread_id,
        body=body,
        dry_run=args.dry_run,
    )


def _send_message(args: argparse.Namespace) -> int:
    body = {
        "type": "message",
        "game_id": args.game_id,
        "destination": args.destination,
        "body": args.body,
    }
    return _reply_or_preview(
        profile=args.profile,
        thread_id=args.thread_id,
        body=body,
        dry_run=args.dry_run,
    )


def _send_peer_diplomacy(args: argparse.Namespace) -> int:
    body = {
        "type": "diplomacy_message",
        "game_id": args.game_id,
        "from_player_id": args.from_player_id,
        "to_player_id": args.to_player_id,
        "turn": args.turn,
        "phase": args.phase,
        "body": args.body,
    }
    return _send_or_preview(
        profile=args.profile,
        recipient=args.recipient,
        body=body,
        dry_run=args.dry_run,
    )


def _poll(args: argparse.Namespace) -> int:
    from .clankmates import ClankmatesError

    if args.dry_run:
        _print_json(
            {
                "ok": True,
                "dry_run": True,
                "profile": args.profile,
                "thread_id": args.thread_id,
                "limit": args.limit,
            }
        )
        return 0

    try:
        result = _clankmates_client().show_thread(
            args.profile, args.thread_id, limit=args.limit, cursor=args.cursor
        )
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    _print_json({"ok": True, "thread_id": args.thread_id, "result": result})
    return 0


def _archive_thread(args: argparse.Namespace) -> int:
    from .clankmates import ClankmatesError

    if args.dry_run:
        _print_json(
            {
                "ok": True,
                "dry_run": True,
                "profile": args.profile,
                "thread_id": args.thread_id,
            }
        )
        return 0

    try:
        result = _clankmates_client().archive_thread(args.profile, args.thread_id)
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    _print_json({"ok": True, "thread_id": args.thread_id, "result": result})
    return 0


def _state(args: argparse.Namespace) -> int:
    from .state_store import StateStore

    store = StateStore(args.state)
    _print_json({"ok": True, "state": store.load()})
    return 0


def _operator_context(args: argparse.Namespace) -> int:
    state = _parse_json_object(args.state_json, field="state")
    _print_json(
        {
            "ok": True,
            "game_id": state.get("game_id"),
            "player_id": state.get("player_id"),
            "turn": state.get("turn"),
            "phase": state.get("phase"),
            "phase_id": state.get("phase_id"),
            "server": state.get("server"),
            "pending_promises": len(state.get("promises", [])),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clanker-courts")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    preflight = subparsers.add_parser("preflight", help="verify Clankmates access")
    preflight.add_argument("--profile", required=True)
    preflight.add_argument("--base-url", required=True)
    preflight.add_argument("--dry-run", action="store_true")
    preflight.set_defaults(func=_preflight)

    join = subparsers.add_parser("join", help="send join_game to the server inbox")
    join.add_argument("--profile", required=True)
    join.add_argument("--server", required=True)
    join.add_argument("--game-id", required=True)
    join.add_argument("--dry-run", action="store_true")
    join.set_defaults(func=_join)

    poll = subparsers.add_parser("poll", help="read one Clankmates thread")
    poll.add_argument("--profile", required=True)
    poll.add_argument("--thread-id", required=True)
    poll.add_argument("--limit", type=int, default=20)
    poll.add_argument("--cursor")
    poll.add_argument("--dry-run", action="store_true")
    poll.set_defaults(func=_poll)

    archive = subparsers.add_parser("archive-thread", help="archive one processed inbox thread")
    archive.add_argument("--profile", required=True)
    archive.add_argument("--thread-id", required=True)
    archive.add_argument("--dry-run", action="store_true")
    archive.set_defaults(func=_archive_thread)

    ready = subparsers.add_parser("ready", help="reply ready_to_start on the server thread")
    ready.add_argument("--profile", required=True)
    ready.add_argument("--thread-id", required=True)
    ready.add_argument("--game-id", required=True)
    ready.add_argument("--dry-run", action="store_true")
    ready.set_defaults(func=_ready)

    submit = subparsers.add_parser("submit-orders", help="reply order_package on the server thread")
    submit.add_argument("--profile", required=True)
    submit.add_argument("--thread-id", required=True)
    submit.add_argument("--game-id", required=True)
    submit.add_argument("--phase-id", required=True)
    submit.add_argument("--orders-json", default="[]")
    submit.add_argument("--dry-run", action="store_true")
    submit.set_defaults(func=_submit_orders)

    message = subparsers.add_parser(
        "send-message", help="reply brokered negotiation on the server thread"
    )
    message.add_argument("--profile", required=True)
    message.add_argument("--thread-id", required=True)
    message.add_argument("--game-id", required=True)
    message.add_argument("--destination", required=True)
    message.add_argument("--body", required=True)
    message.add_argument("--dry-run", action="store_true")
    message.set_defaults(func=_send_message)

    diplomacy = subparsers.add_parser(
        "send-diplomacy", help="deprecated alias for send-message"
    )
    diplomacy.add_argument("--profile", required=True)
    diplomacy.add_argument("--thread-id", required=True)
    diplomacy.add_argument("--game-id", required=True)
    diplomacy.add_argument("--destination", required=True)
    diplomacy.add_argument("--body", required=True)
    diplomacy.add_argument("--dry-run", action="store_true")
    diplomacy.set_defaults(func=_send_message)

    peer_diplomacy = subparsers.add_parser(
        "send-peer-diplomacy", help="send historical direct peer diplomacy"
    )
    peer_diplomacy.add_argument("--profile", required=True)
    peer_diplomacy.add_argument("--recipient", required=True)
    peer_diplomacy.add_argument("--game-id", required=True)
    peer_diplomacy.add_argument("--from-player-id", required=True)
    peer_diplomacy.add_argument("--to-player-id", required=True)
    peer_diplomacy.add_argument("--turn", type=int, required=True)
    peer_diplomacy.add_argument("--phase", choices=["reinforcement", "movement"], required=True)
    peer_diplomacy.add_argument("--body", required=True)
    peer_diplomacy.add_argument("--dry-run", action="store_true")
    peer_diplomacy.set_defaults(func=_send_peer_diplomacy)

    state = subparsers.add_parser("state", help="print saved state")
    state.add_argument("--state", required=True)
    state.set_defaults(func=_state)

    context = subparsers.add_parser("operator-context", help="print local state context")
    context.add_argument("--state-json", required=True)
    context.set_defaults(func=_operator_context)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
