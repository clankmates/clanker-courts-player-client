import json
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "clanker_courts_player", *args],
        check=False,
        text=True,
        capture_output=True,
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
        "done-phase",
        "send-diplomacy",
        "state",
        "operator-context",
    ]:
        assert command in result.stdout
    for obsolete in ["summarize", "legal-actions", "build-response", "validate-response"]:
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


def test_submit_orders_dry_run_uses_phase_id_not_player_identity():
    result = run_cli(
        "submit-orders",
        "--profile",
        "p",
        "--server",
        "@gamemaster/clanker_courts",
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
    assert payload["body"] == {
        "type": "order_response",
        "game_id": "demo",
        "phase_id": "demo:turn-01:movement",
        "orders": [{"kind": "move", "from": "B", "to": "M", "troops": 3}],
    }


def test_done_phase_dry_run_uses_only_game_and_phase_tokens():
    result = run_cli(
        "done-phase",
        "--profile",
        "p",
        "--server",
        "@gamemaster/clanker_courts",
        "--game-id",
        "demo",
        "--phase-id",
        "demo:turn-01:movement",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["body"] == {
        "type": "done_phase",
        "game_id": "demo",
        "phase_id": "demo:turn-01:movement",
    }
