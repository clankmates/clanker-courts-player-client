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
        "find-threads",
        "freshen",
        "watch-messages",
        "poll",
        "ready",
        "get-current-phase",
        "get-after-game-report",
        "submit-orders",
        "send-message",
        "send-diplomacy",
        "send-peer-diplomacy",
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


def test_get_current_phase_dry_run_uses_only_current_phase_contract_fields():
    result = run_cli(
        "get-current-phase",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--game-id",
        "demo",
        "--request-id",
        "current-1",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == "thread-1"
    assert payload["body"] == {
        "type": "get_current_phase",
        "game_id": "demo",
        "request_id": "current-1",
    }


def test_get_after_game_report_dry_run_uses_sender_derived_identity():
    result = run_cli(
        "get-after-game-report",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--game-id",
        "demo",
        "--request-id",
        "after-game-1",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == "thread-1"
    assert payload["body"] == {
        "type": "get_after_game_report",
        "game_id": "demo",
        "request_id": "after-game-1",
    }


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


def test_send_message_dry_run_replies_brokered_negotiation_to_server_thread():
    result = run_cli(
        "send-message",
        "--profile",
        "p",
        "--thread-id",
        "server-thread",
        "--game-id",
        "demo",
        "--destination",
        "Orange",
        "--body",
        "Hold the center and I will pressure Blue.",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == "server-thread"
    assert payload["body"] == {
        "type": "message",
        "game_id": "demo",
        "destination": "Orange",
        "body": "Hold the center and I will pressure Blue.",
    }


def test_send_peer_diplomacy_dry_run_is_historical_direct_fallback():
    result = run_cli(
        "send-peer-diplomacy",
        "--profile",
        "p",
        "--recipient",
        "@orange",
        "--game-id",
        "demo",
        "--from-player-id",
        "@blue",
        "--to-player-id",
        "@orange",
        "--turn",
        "1",
        "--phase",
        "movement",
        "--body",
        "legacy fallback",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["recipient"] == "@orange"
    assert payload["body"]["type"] == "diplomacy_message"


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


def test_freshen_dry_run_uses_changes_primitive(tmp_path):
    result = run_cli(
        "freshen",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--state",
        str(tmp_path / "state.json"),
        "--since-cache",
        "--save-cache",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["primitive"] == "inbox messages changes"
    assert payload["since_cache"] is True
    assert payload["save_cache"] is True


def test_find_threads_dry_run_uses_search_and_freshness_filters():
    result = run_cli(
        "find-threads",
        "--profile",
        "p",
        "--participant",
        "@gamemaster/clanker_courts",
        "--query",
        "server_manifest",
        "--since-cache",
        "--save-cache",
        "--limit",
        "5",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["primitive"] == "inbox list"
    assert payload["participant"] == "@gamemaster/clanker_courts"
    assert payload["query"] == "server_manifest"
    assert payload["since_cache"] is True
    assert payload["save_cache"] is True
    assert payload["limit"] == 5


def test_watch_messages_dry_run_uses_watch_primitive(tmp_path):
    result = run_cli(
        "watch-messages",
        "--profile",
        "p",
        "--thread-id",
        "thread-1",
        "--state",
        str(tmp_path / "state.json"),
        "--once",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["primitive"] == "inbox watch messages"
    assert payload["once"] is True
