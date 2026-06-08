from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_operator_and_autoplayer_skills_exist():
    assert (ROOT / "skills/clanker-courts-operator/SKILL.md").exists()
    assert (ROOT / "skills/clanker-courts-autoplayer/SKILL.md").exists()


def test_operator_skill_is_protocol_and_state_only():
    text = (ROOT / "skills/clanker-courts-operator/SKILL.md").read_text()

    assert "does not choose strategy" in text
    assert "must not rank moves" in text
    assert "clanker-courts submit-orders" in text
    assert "phase_id" in text


def test_autoplayer_skill_depends_on_operator_skill():
    text = (ROOT / "skills/clanker-courts-autoplayer/SKILL.md").read_text()

    assert "Clanker Courts Operator" in text
    assert "visible information only" in text
    assert "Never inspect private server modules" in text
