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


def test_module_help_lists_clean_stateful_commands_only():
    result = run_cli("--help")

    assert result.returncode == 0
    for command in [
        "join",
        "watch",
        "ready",
        "current",
        "orders",
        "message",
        "final-report",
        "status",
        "recover-thread",
    ]:
        assert command in result.stdout
    for obsolete in [
        "preflight",
        "find-threads",
        "freshen",
        "watch-messages",
        "poll",
        "archive-thread",
        "send-diplomacy",
        "send-peer-diplomacy",
        "get-current-phase",
        "submit-orders",
        "--thread-id",
        "--dry-run",
    ]:
        assert obsolete not in result.stdout


def test_status_reports_missing_state(tmp_path):
    result = run_cli("status", "--artifact-dir", str(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "missing_state"
    assert payload["state"] == str(tmp_path / "state.json")
