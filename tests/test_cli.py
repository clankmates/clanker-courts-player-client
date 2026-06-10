import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "skills/clanker-courts-operator/scripts"),
    }
    return subprocess.run(
        [sys.executable, "-m", "clanker_courts_player", *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def test_module_help_lists_published_protocol_commands():
    result = run_cli("--help")

    assert result.returncode == 0
    for command in [
        "preflight",
        "join",
        "poll",
        "ready",
        "submit-orders",
        "send-diplomacy",
        "archive-thread",
        "state",
        "operator-context",
    ]:
        assert command in result.stdout
    for obsolete in [
        "build-response",
        "done-phase",
        "legal-actions",
        "play-loop",
        "validate-response",
    ]:
        assert obsolete not in result.stdout


def test_preflight_dry_run_prints_planned_checks():
    result = run_cli(
        "preflight",
        "--profile",
        "test",
        "--base-url",
        "http://localhost:4000",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "profile": "test",
        "base_url": "http://localhost:4000",
        "dry_run": True,
        "planned_checks": ["clankm", "profile", "auth", "inbox"],
    }


def test_join_dry_run_omits_client_supplied_handle():
    result = run_cli(
        "join",
        "--profile",
        "p",
        "--server",
        "@gamemaster/clanker_courts",
        "--game-id",
        "demo",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["recipient"] == "@gamemaster/clanker_courts"
    assert payload["body"] == {"type": "join_game", "game_id": "demo"}


def test_ready_dry_run_uses_only_game_id():
    result = run_cli(
        "ready",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--game-id",
        "demo",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == "thread-1"
    assert payload["body"] == {"type": "ready_to_start", "game_id": "demo"}


def test_submit_orders_dry_run_uses_order_package_with_phase_id_not_player_identity():
    result = run_cli(
        "submit-orders",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--game-id",
        "demo",
        "--phase-id",
        "demo:turn-01:movement",
        "--orders-json",
        '[{"kind":"move","from":"B","to":"M","troops":3}]',
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == "thread-1"
    assert payload["body"] == {
        "type": "order_package",
        "game_id": "demo",
        "phase_id": "demo:turn-01:movement",
        "orders": [{"kind": "move", "from": "B", "to": "M", "troops": 3}],
    }


def test_archive_thread_dry_run_prints_thread_id():
    result = run_cli(
        "archive-thread",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "dry_run": True,
        "profile": "p",
        "thread_id": "thread-1",
    }
