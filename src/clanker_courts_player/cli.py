from __future__ import annotations

import argparse
import json
from typing import Any

COMMANDS = [
    "preflight",
    "join",
    "poll",
    "summarize",
    "legal-actions",
    "build-response",
    "validate-response",
    "play-loop",
]


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


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

    from .clankmates import ClankmatesClient, ClankmatesError

    client = ClankmatesClient()
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
    from .clankmates import ClankmatesClient, ClankmatesError
    from .session import join_game
    from .state_store import StateStore

    client = ClankmatesClient()
    try:
        payload = join_game(
            client=client,
            profile=args.profile,
            base_url=args.base_url,
            server=args.server,
            game_id=args.game_id,
            store=StateStore(args.state),
        )
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    except ValueError as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 1
    _print_json(payload)
    return 0


def _poll(args: argparse.Namespace) -> int:
    from .clankmates import ClankmatesClient, ClankmatesError
    from .session import poll_server_thread
    from .state_store import StateStore

    client = ClankmatesClient()
    try:
        payload = poll_server_thread(client=client, store=StateStore(args.state), limit=args.limit)
    except ClankmatesError as exc:
        _print_json(exc.to_dict())
        return 1
    except (OSError, ValueError) as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 1
    _print_json(payload)
    return 0


def _placeholder(command: str):
    def run(_args: argparse.Namespace) -> int:
        _print_json({"ok": False, "command": command, "error": "not implemented"})
        return 2

    return run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clanker-courts")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    preflight = subparsers.add_parser("preflight", help="verify Clankmates access")
    preflight.add_argument("--profile", required=True)
    preflight.add_argument("--base-url", required=True)
    preflight.add_argument("--dry-run", action="store_true")
    preflight.set_defaults(func=_preflight)

    for command in COMMANDS:
        if command == "preflight":
            continue
        if command == "join":
            join = subparsers.add_parser("join", help="join a Clanker Courts game")
            join.add_argument("--profile", required=True)
            join.add_argument("--base-url", required=True)
            join.add_argument("--server", required=True)
            join.add_argument("--game-id", required=True)
            join.add_argument("--state", required=True)
            join.set_defaults(func=_join)
            continue
        if command == "poll":
            poll = subparsers.add_parser("poll", help="poll the joined server thread")
            poll.add_argument("--state", required=True)
            poll.add_argument("--limit", type=int, default=25)
            poll.set_defaults(func=_poll)
            continue
        subparser = subparsers.add_parser(command, help=f"{command} placeholder")
        subparser.set_defaults(func=_placeholder(command))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
