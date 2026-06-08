import json
from pathlib import Path

import pytest

from clanker_courts_player.errors import StructuredValidationError
from clanker_courts_player.models import (
    JoinAck,
    JoinGame,
    MovementPhaseReport,
    OrderAccepted,
    OrderPackage,
    OrderRejected,
    PeerDiplomacyMessage,
    ReadyCheck,
    ReadyToStart,
    SetupReport,
    StartCancelled,
    parse_message_body,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture_name", "model"),
    [
        ("join_game.json", JoinGame),
        ("join_ack.json", JoinAck),
        ("ready_check.json", ReadyCheck),
        ("ready_to_start.json", ReadyToStart),
        ("start_cancelled.json", StartCancelled),
        ("setup_report.json", SetupReport),
        ("movement_phase_report.json", MovementPhaseReport),
        ("order_package.json", OrderPackage),
        ("order_accepted.json", OrderAccepted),
        ("order_rejected.json", OrderRejected),
        ("peer_diplomacy_message.json", PeerDiplomacyMessage),
    ],
)
def test_valid_fixtures_parse_and_round_trip_preserving_unknown_fields(fixture_name, model):
    raw = json.loads((FIXTURES / fixture_name).read_text())

    parsed = model.model_validate(raw)
    dumped = parsed.model_dump(mode="json")

    assert dumped == raw
    assert dumped["unknown_future_field"] == raw["unknown_future_field"]


@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        (
            {"type": "join_game", "game_id": "g", "handle": "@legacy"},
            "handle",
        ),
        (
            {
                "type": "order_package",
                "game_id": "g",
                "phase_id": "g:turn-01:movement",
                "player_id": "blue",
                "orders": [],
            },
            "player_id",
        ),
        (
            {
                "type": "diplomacy_message",
                "game_id": "g",
                "from_player_id": "blue",
                "to_player_id": "blue",
                "turn": 1,
                "phase": "movement",
                "body": "hi",
            },
            "to_player_id",
        ),
    ],
)
def test_invalid_messages_fail_with_structured_errors(payload, expected_field):
    with pytest.raises(StructuredValidationError) as exc_info:
        parse_message_body(payload)

    error = exc_info.value.to_dict()
    assert error["ok"] is False
    assert error["errors"][0]["field"] == expected_field


@pytest.mark.parametrize(
    "message_type",
    ["done_phase", "game_started", "movement_visibility_report", "order_response", "phase_request"],
)
def test_legacy_server_messages_are_unknown(message_type):
    with pytest.raises(StructuredValidationError) as exc_info:
        parse_message_body({"type": message_type, "game_id": "g"})

    assert exc_info.value.to_dict()["errors"][0] == {
        "field": "type",
        "message": "unknown message type",
    }


def test_non_object_json_fails_with_structured_error():
    with pytest.raises(StructuredValidationError) as exc_info:
        parse_message_body(["not", "an", "object"])

    assert exc_info.value.to_dict() == {
        "ok": False,
        "errors": [{"field": "$", "message": "expected JSON object"}],
    }
