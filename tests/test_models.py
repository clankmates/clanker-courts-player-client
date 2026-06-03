import json
from pathlib import Path

import pytest

from clanker_courts_player.errors import StructuredValidationError
from clanker_courts_player.models import (
    GameStarted,
    JoinAck,
    JoinGame,
    OrderResponse,
    PeerDiplomacyMessage,
    PhaseRequest,
    parse_message_body,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture_name", "model"),
    [
        ("join_game.json", JoinGame),
        ("join_ack.json", JoinAck),
        ("game_started.json", GameStarted),
        ("phase_request_reinforcement.json", PhaseRequest),
        ("phase_request_movement.json", PhaseRequest),
        ("order_response.json", OrderResponse),
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
            {
                "type": "phase_request",
                "game_id": "g",
                "request_id": "r",
                "player_id": "blue",
                "turn": 1,
                "phase": "trade",
                "status": {},
                "reports": [],
            },
            "phase",
        ),
        (
            {
                "type": "phase_request",
                "request_id": "r",
                "player_id": "blue",
                "turn": 1,
                "phase": "movement",
                "status": {},
                "reports": [],
            },
            "game_id",
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


def test_non_object_json_fails_with_structured_error():
    with pytest.raises(StructuredValidationError) as exc_info:
        parse_message_body(["not", "an", "object"])

    assert exc_info.value.to_dict() == {
        "ok": False,
        "errors": [{"field": "$", "message": "expected JSON object"}],
    }
