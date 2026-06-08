import json
from pathlib import Path

from clanker_courts_player.messages import (
    decode_clankmates_message,
    latest_unseen_phase_report,
    recent_peer_diplomacy,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_decode_message_body_json_string_from_attributes():
    message = {"id": "m1", "attributes": {"body": '{"type":"setup_report","game_id":"g"}'}}

    decoded = decode_clankmates_message(message)

    assert decoded["message_id"] == "m1"
    assert decoded["body"] == {"type": "setup_report", "game_id": "g"}
    assert decoded["raw"] == message


def test_decode_message_body_leaves_plain_text_body_unparsed():
    message = {"id": "m2", "body": "plain text"}

    decoded = decode_clankmates_message(message)

    assert decoded["body"] == "plain text"


def test_selects_latest_unseen_matching_phase_report_for_game_id():
    page = json.loads((FIXTURES / "inbox_page_phase_reports.json").read_text())
    decoded = [decode_clankmates_message(message) for message in page["messages"]]

    selected = latest_unseen_phase_report(
        decoded, game_id="demo", seen_phase_ids={"demo:turn-01:reinforcement"}
    )

    assert selected is not None
    assert selected["body"]["phase_id"] == "demo:turn-01:movement"


def test_returns_none_when_all_matching_phase_reports_seen():
    page = json.loads((FIXTURES / "inbox_page_phase_reports.json").read_text())
    decoded = [decode_clankmates_message(message) for message in page["messages"]]

    selected = latest_unseen_phase_report(
        decoded,
        game_id="demo",
        seen_phase_ids={"demo:turn-01:reinforcement", "demo:turn-01:movement"},
    )

    assert selected is None


def test_ignores_terminal_movement_result_without_next_phase():
    decoded = [
        {
            "message_id": "terminal",
            "timestamp": "2026-06-07T10:03:00Z",
            "body": {
                "type": "movement_result_report",
                "game_id": "demo",
                "turn": 24,
                "phase": "movement",
                "battle_reports": [],
                "status": {"status": "ended"},
                "visibility": {},
            },
        }
    ]

    selected = latest_unseen_phase_report(decoded, game_id="demo", seen_phase_ids=set())

    assert selected is None


def test_recent_peer_diplomacy_filters_game_and_player_then_limits():
    page = json.loads((FIXTURES / "inbox_page_diplomacy.json").read_text())
    decoded = [decode_clankmates_message(message) for message in page["messages"]]

    messages = recent_peer_diplomacy(decoded, game_id="demo", player_id="blue", limit=3)

    assert [message["body"]["body"] for message in messages] == [
        "message 11",
        "message 12",
        "message 13",
    ]
