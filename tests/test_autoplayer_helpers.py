import json
from datetime import UTC, datetime
from pathlib import Path

from clanker_courts_autoplayer.context import (
    append_decision_journal,
    append_ledger_note,
    build_phase_context,
    safe_fallback_orders,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_phase_context_summarizes_visible_state_and_negotiation(tmp_path):
    current = json.loads((FIXTURES / "get_current_phase_open.json").read_text())
    state = {
        "schema_version": 1,
        "profile": "p",
        "server": "@server",
        "server_thread_id": "thread-1",
        "game_id": "demo",
        "status": "active",
        "player_id": "Blue",
        "players": ["Blue", "Orange"],
        "capital_location_id": "B",
        "latest_current_phase_response": current,
        "allowed_command": current["allowed_command"],
        "visible_state": {
            "locations": [
                {
                    "location_id": "B",
                    "reported_location_type": "capital",
                    "controller": "Blue",
                    "troops": 5,
                },
                {
                    "location_id": "M",
                    "reported_location_type": "town",
                    "controller": "Orange",
                    "troops": 2,
                },
            ],
            "connectivity_graph": {"B": ["M"]},
        },
    }
    (tmp_path / "state.json").write_text(json.dumps(state))
    raw_message = {
        "message_id": "m1",
        "thread_id": "thread-1",
        "server_timestamp": "2026-06-14T18:10:00Z",
        "body": {
            "type": "message",
            "game_id": "demo",
            "from": "Orange",
            "body": "I will hold M if you stay home.",
        },
    }
    (tmp_path / "raw_messages.jsonl").write_text(json.dumps(raw_message) + "\n")

    context = build_phase_context(
        tmp_path,
        now=datetime(2026, 6, 14, 18, 29, 0, tzinfo=UTC),
    )

    assert context["recommended_next"]["kind"] == "choose_and_submit_orders"
    assert context["deadline"]["seconds_remaining"] == 60
    digest = context["visible_state_digest"]
    assert digest["controlled_location_ids"] == ["B"]
    assert digest["adjacent_location_ids"] == ["M"]
    assert digest["visible_score_estimate"] == 3
    assert digest["visible_capital_threats"][0]["location_id"] == "M"
    assert context["recent_negotiation"]["accepted"][0]["from"] == "Orange"
    assert context["safe_fallback"]["orders_json"] == "[]"


def test_safe_fallback_orders_uses_empty_package_defaults(tmp_path):
    state = {
        "game_id": "demo",
        "phase": "reinforcement",
        "phase_id": "demo:turn-01:reinforcement",
        "allowed_command": {"command": "order_package", "accepting": True},
    }
    (tmp_path / "state.json").write_text(json.dumps(state))

    payload = safe_fallback_orders(tmp_path)

    assert payload["safe_to_submit"] is True
    assert payload["orders"] == []
    assert "reinforces the capital" in payload["reason"]


def test_decision_journal_and_ledger_append_jsonl_records(tmp_path):
    state = {
        "game_id": "demo",
        "turn": 2,
        "phase": "movement",
        "phase_id": "demo:turn-02:movement",
        "player_id": "Blue",
    }
    (tmp_path / "state.json").write_text(json.dumps(state))

    decision = append_decision_journal(
        tmp_path,
        phase_id="demo:turn-02:movement",
        rationale="Hold capital and wait.",
        orders=[],
        risks=["Orange may expand"],
        promises_made=[],
        promises_received=[{"from": "Orange", "body": "truce"}],
    )
    note = append_ledger_note(
        tmp_path,
        player="Orange",
        kind="promise_received",
        note="Offered a truce.",
        phase_id=None,
    )

    assert decision["player_id"] == "Blue"
    assert note["phase_id"] == "demo:turn-02:movement"
    journal_rows = (tmp_path / "decision_journal.jsonl").read_text().splitlines()
    ledger_rows = (tmp_path / "diplomacy_ledger.jsonl").read_text().splitlines()
    assert json.loads(journal_rows[0])["rationale"] == "Hold capital and wait."
    assert json.loads(ledger_rows[0])["player"] == "Orange"
