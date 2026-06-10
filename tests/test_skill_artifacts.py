import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_operator_and_autoplayer_skills_exist():
    assert (ROOT / "skills/clanker-courts-operator/SKILL.md").exists()
    assert (ROOT / "skills/clanker-courts-autoplayer/SKILL.md").exists()


def test_operator_skill_is_self_contained():
    skill_dir = ROOT / "skills/clanker-courts-operator"

    assert (skill_dir / "scripts/clanker-courts").exists()
    assert (skill_dir / "scripts/requirements.txt").read_text() == "pydantic>=2,<3\n"
    assert (skill_dir / "scripts/clanker_courts_player/cli.py").exists()
    assert (skill_dir / "references/message-types.md").exists()


def test_operator_skill_is_protocol_and_state_only():
    text = (ROOT / "skills/clanker-courts-operator/SKILL.md").read_text()

    assert "does not choose strategy" in text
    assert "must not rank moves" in text
    assert "clanker-courts submit-orders" in text
    assert "clanker-courts archive-thread" in text
    assert "Game Discovery" in text
    assert "phase_id" in text


def test_skill_local_wrapper_runs_without_global_install():
    skill_dir = ROOT / "skills/clanker-courts-operator"
    env = {
        **os.environ,
        "PYTHON": sys.executable,
        "PYTHONPATH": str(skill_dir / "scripts"),
    }

    result = subprocess.run(
        [str(skill_dir / "scripts/clanker-courts"), "--help"],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 0
    assert "archive-thread" in result.stdout


def test_autoplayer_skill_depends_on_operator_skill():
    text = (ROOT / "skills/clanker-courts-autoplayer/SKILL.md").read_text()

    assert "Clanker Courts Operator" in text
    assert "visible information only" in text
    assert "Never inspect private server modules" in text
