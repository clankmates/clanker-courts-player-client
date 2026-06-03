import json
from pathlib import Path

from clanker_courts_player.messages import (
    decode_clankmates_message,
    latest_unseen_phase_request,
    recent_peer_diplomacy,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_decode_body_json_and_plain_text_and_timestamp_variants():
    json_message = {
        "id": "m1",
        "thread_id": "t1",
        "createdAt": "2026-06-03T00:00:00Z",
        "attributes": {"body": '{"type":"phase_request","game_id":"g"}'},
    }
    text_message = {
        "id": "m2",
        "thread_id": "t2",
        "inserted_at": "2026-06-03T00:01:00Z",
        "attributes": {"body": "hello"},
    }

    assert decode_clankmates_message(json_message)["body"] == {
        "type": "phase_request",
        "game_id": "g",
    }
    decoded_text = decode_clankmates_message(text_message)
    assert decoded_text["body"] == "hello"
    assert decoded_text["timestamp"] == "2026-06-03T00:01:00Z"


def test_decode_falls_back_to_top_level_body_when_attributes_body_missing():
    message = {
        "id": "m-top",
        "thread_id": "t-top",
        "created_at": "2026-06-03T00:00:00Z",
        "attributes": {},
        "body": '{"type":"phase_request","game_id":"demo"}',
    }

    decoded = decode_clankmates_message(message)

    assert decoded["body"] == {"type": "phase_request", "game_id": "demo"}


def test_timestamp_sorting_handles_mixed_naive_and_aware_iso_strings():
    messages = [
        {
            "message_id": "aware-old",
            "timestamp": "2026-06-03T00:00:00Z",
            "body": {
                "type": "phase_request",
                "game_id": "demo",
                "request_id": "req-aware",
            },
        },
        {
            "message_id": "naive-new",
            "timestamp": "2026-06-03T00:01:00",
            "body": {
                "type": "phase_request",
                "game_id": "demo",
                "request_id": "req-naive",
            },
        },
    ]

    selected = latest_unseen_phase_request(messages, game_id="demo", seen_request_ids=set())

    assert selected["message_id"] == "naive-new"


def test_selects_latest_unseen_matching_phase_request_for_game_id():
    page = json.loads((FIXTURES / "inbox_page_phase_request.json").read_text())
    decoded = [decode_clankmates_message(message) for message in page["messages"]]

    selected = latest_unseen_phase_request(decoded, game_id="demo", seen_request_ids={"req-old"})

    assert selected["message_id"] == "m-new"
    assert selected["body"]["request_id"] == "req-new"
    assert selected["body"]["phase"] == "movement"


def test_recent_peer_diplomacy_keeps_last_12_involving_current_player_and_ignores_other_games():
    page = json.loads((FIXTURES / "inbox_page_diplomacy.json").read_text())
    decoded = [decode_clankmates_message(message) for message in page["messages"]]

    selected = recent_peer_diplomacy(decoded, game_id="demo", player_id="blue", limit=12)

    assert len(selected) == 12
    assert selected[0]["body"]["body"] == "message 02"
    assert selected[-1]["body"]["body"] == "message 13"
    assert all(
        message["body"]["game_id"] == "demo"
        and (
            message["body"]["from_player_id"] == "blue" or message["body"]["to_player_id"] == "blue"
        )
        for message in selected
    )
