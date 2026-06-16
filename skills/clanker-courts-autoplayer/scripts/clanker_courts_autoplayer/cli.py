from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .context import (
    append_decision_journal,
    append_ledger_note,
    build_phase_context,
    safe_fallback_orders,
)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def _parse_json(value: str, *, field: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"{field} must be valid JSON: {exc}") from exc


def _context(args: argparse.Namespace) -> int:
    _print_json(build_phase_context(Path(args.artifact_dir)))
    return 0


def _fallback_orders(args: argparse.Namespace) -> int:
    _print_json(safe_fallback_orders(Path(args.artifact_dir)))
    return 0


def _record_decision(args: argparse.Namespace) -> int:
    record = append_decision_journal(
        Path(args.artifact_dir),
        phase_id=args.phase_id,
        rationale=args.rationale,
        orders=_parse_json(args.orders_json, field="orders-json"),
        risks=_parse_json(args.risks_json, field="risks-json"),
        promises_made=_parse_json(args.promises_made_json, field="promises-made-json"),
        promises_received=_parse_json(args.promises_received_json, field="promises-received-json"),
    )
    _print_json({"ok": True, "action": "record_decision", "record": record})
    return 0


def _ledger_note(args: argparse.Namespace) -> int:
    record = append_ledger_note(
        Path(args.artifact_dir),
        player=args.player,
        kind=args.kind,
        note=args.note,
        phase_id=args.phase_id,
    )
    _print_json({"ok": True, "action": "ledger_note", "record": record})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clanker-courts-autoplayer")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    context = subparsers.add_parser("context", help="print the current decision surface")
    context.add_argument("--artifact-dir", required=True)
    context.set_defaults(func=_context)

    fallback = subparsers.add_parser(
        "fallback-orders", help="print safe default orders for the current phase"
    )
    fallback.add_argument("--artifact-dir", required=True)
    fallback.set_defaults(func=_fallback_orders)

    decision = subparsers.add_parser(
        "record-decision", help="append one decision journal record"
    )
    decision.add_argument("--artifact-dir", required=True)
    decision.add_argument("--phase-id", required=True)
    decision.add_argument("--rationale", required=True)
    decision.add_argument("--orders-json", default="[]")
    decision.add_argument("--risks-json", default="[]")
    decision.add_argument("--promises-made-json", default="[]")
    decision.add_argument("--promises-received-json", default="[]")
    decision.set_defaults(func=_record_decision)

    ledger = subparsers.add_parser("ledger-note", help="append one diplomacy ledger note")
    ledger.add_argument("--artifact-dir", required=True)
    ledger.add_argument("--player", required=True)
    ledger.add_argument(
        "--kind",
        required=True,
        choices=[
            "promise_made",
            "promise_received",
            "promise_kept",
            "promise_broken",
            "trust",
            "suspicion",
            "threat",
            "note",
        ],
    )
    ledger.add_argument("--note", required=True)
    ledger.add_argument("--phase-id")
    ledger.set_defaults(func=_ledger_note)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
