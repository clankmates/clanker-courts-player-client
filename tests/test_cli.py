import json
import subprocess
import sys


def test_module_help_lists_stage_0_to_3_commands():
    result = subprocess.run(
        [sys.executable, "-m", "clanker_courts_player", "--help"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    for command in [
        "preflight",
        "join",
        "poll",
        "summarize",
        "legal-actions",
        "build-response",
        "validate-response",
        "play-loop",
    ]:
        assert command in result.stdout


def test_preflight_dry_run_prints_planned_checks():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "clanker_courts_player",
            "preflight",
            "--profile",
            "test",
            "--base-url",
            "http://localhost:4000",
            "--dry-run",
        ],
        check=False,
        text=True,
        capture_output=True,
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
