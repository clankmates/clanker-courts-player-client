import json
from pathlib import Path

import pytest
from clanker_courts_player.errors import StructuredValidationError
from clanker_courts_player.models import (
    AfterGameReport,
    AfterGameReportRejected,
    BrokeredNegotiationMessage,
    CurrentPhaseRejected,
    CurrentPhaseResponse,
    GetAfterGameReport,
    GetCurrentPhase,
    JoinAck,
    JoinGame,
    MessageAccepted,
    MessageRejected,
    MovementPhaseReport,
    OrderAccepted,
    OrderPackage,
    OrderRejected,
    PeerDiplomacyMessage,
    ReadyCheck,
    ReadyToStart,
    ServerManifest,
    SetupReport,
    StartCancelled,
    parse_current_phase_response,
    parse_get_after_game_report_request,
    parse_get_current_phase_request,
    parse_message_body,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture_name", "model"),
    [
        ("server_manifest.json", ServerManifest),
        ("join_game.json", JoinGame),
        ("join_ack.json", JoinAck),
        ("ready_check.json", ReadyCheck),
        ("ready_to_start.json", ReadyToStart),
        ("start_cancelled.json", StartCancelled),
        ("setup_report.json", SetupReport),
        ("movement_phase_report.json", MovementPhaseReport),
        ("after_game_report.json", AfterGameReport),
        ("after_game_report_rejected.json", AfterGameReportRejected),
        ("order_package.json", OrderPackage),
        ("order_accepted.json", OrderAccepted),
        ("order_rejected.json", OrderRejected),
        ("get_current_phase_open.json", CurrentPhaseResponse),
        ("current_phase_rejected.json", CurrentPhaseRejected),
        ("brokered_negotiation_command.json", BrokeredNegotiationMessage),
        ("brokered_negotiation_message.json", BrokeredNegotiationMessage),
        ("message_accepted.json", MessageAccepted),
        ("message_rejected.json", MessageRejected),
        ("peer_diplomacy_message.json", PeerDiplomacyMessage),
    ],
)
def test_valid_fixtures_parse_and_round_trip_preserving_unknown_fields(fixture_name, model):
    raw = json.loads((FIXTURES / fixture_name).read_text())

    parsed = model.model_validate(raw)
    dumped = parsed.model_dump(mode="json")

    assert dumped == raw
    assert dumped["unknown_future_field"] == raw["unknown_future_field"]


def test_current_setup_metadata_points_to_public_canonical_docs():
    raw = json.loads((FIXTURES / "setup_report.json").read_text())

    parsed = SetupReport.model_validate(raw)

    assert parsed.rules == "clanker-courts-v12"
    assert parsed.rules_metadata is not None
    assert parsed.rules_metadata["rules_path"] == "rules/clanker-courts.md"
    assert parsed.rules_metadata["protocol_path"] == "protocol/server.md"
    assert parsed.rules_metadata["canonical_manifest_path"] == "docs/canonical-manifest.json"
    assert parsed.player == "Blue"
    assert parsed.handle_mode == "random"
    assert parsed.players == ["Blue", "Orange"]
    visible_locations = parsed.visibility["locations"]
    assert visible_locations[0]["reported_location_type"] == "capital"
    assert visible_locations[1]["reported_location_type"] == "city"


def test_historical_v10_setup_fixture_is_supported_but_not_current_default():
    raw = json.loads((FIXTURES / "historical_v10_setup_report.json").read_text())

    parsed = SetupReport.model_validate(raw)

    assert parsed.rules == "clanker-courts-v10"
    assert parsed.rules_metadata is None
    assert raw["fixture_note"] == "Historical v10 payload retained for backward compatibility only."


def test_after_game_report_preserves_outcome_fields_final_standings_and_match_points():
    raw = json.loads((FIXTURES / "after_game_report.json").read_text())

    parsed = AfterGameReport.model_validate(raw)

    assert parsed.winners == ["@alice/bluebot", "@orange/orangebot"]
    assert parsed.outcome_reason == "final_turn_scoring"
    assert "tied on score, troops, and cities" in parsed.score_rationale
    assert parsed.final_standings is not None
    assert parsed.match_points is not None
    assert parsed.final_standings[0]["placement_rank"] == 1
    assert parsed.final_standings[1]["placement_rank"] == 1
    assert parsed.final_standings[2]["placement_rank"] == 3
    assert parsed.match_points[0]["total_points"] == 15.0


@pytest.mark.parametrize(
    "fixture_name",
    [
        "get_current_phase_open.json",
        "get_current_phase_expired.json",
        "get_current_phase_ended.json",
    ],
)
def test_current_phase_responses_parse_and_preserve_unknown_fields(fixture_name):
    raw = json.loads((FIXTURES / fixture_name).read_text())

    parsed = parse_current_phase_response(raw)
    dumped = parsed.model_dump(mode="json")
    if dumped.get("allowed_command", {}).get("accepting") is None:
        dumped["allowed_command"].pop("accepting")

    assert isinstance(parsed, CurrentPhaseResponse)
    assert dumped == raw
    assert dumped["unknown_future_field"] == "preserved"


def test_open_current_phase_response_supplies_order_preparation_surface():
    raw = json.loads((FIXTURES / "get_current_phase_open.json").read_text())

    parsed = CurrentPhaseResponse.model_validate(raw)

    assert parsed.current_phase is not None
    assert parsed.current_phase.phase_id == "demo:turn-02:movement"
    assert parsed.current_phase.status == "open"
    assert parsed.allowed_command.accepting is True
    assert parsed.allowed_command.request == {
        "type": "order_package",
        "game_id": "demo",
        "phase_id": "demo:turn-02:movement",
        "orders": [],
    }
    assert parsed.latest_report.report_hash == "sha256:open-phase-report"
    assert parsed.visible_state is not None
    assert parsed.visible_state["locations"][0]["reported_location_type"] == "capital"


def test_expired_current_phase_does_not_advance_game_or_accept_orders():
    raw = json.loads((FIXTURES / "get_current_phase_expired.json").read_text())

    parsed = CurrentPhaseResponse.model_validate(raw)

    assert parsed.current_phase is not None
    assert parsed.current_phase.status == "expired"
    assert parsed.current_phase.phase_id == "demo:turn-02:movement"
    assert parsed.allowed_command.accepting is False


def test_ended_current_phase_points_to_after_game_report():
    raw = json.loads((FIXTURES / "get_current_phase_ended.json").read_text())

    parsed = CurrentPhaseResponse.model_validate(raw)

    assert parsed.current_phase is None
    assert parsed.allowed_command.command == "get_after_game_report"
    assert parsed.latest_report.report_type == "after_game_report"


def test_get_current_phase_request_uses_only_server_contract_fields():
    parsed = GetCurrentPhase.model_validate(
        {
            "type": "get_current_phase",
            "game_id": "demo",
            "request_id": "current-1",
        }
    )

    assert parsed.model_dump(mode="json") == {
        "type": "get_current_phase",
        "game_id": "demo",
        "request_id": "current-1",
    }


def test_get_after_game_report_request_uses_sender_derived_identity():
    parsed = GetAfterGameReport.model_validate(
        {
            "type": "get_after_game_report",
            "game_id": "demo",
            "request_id": "after-game-1",
        }
    )

    assert parsed.model_dump(mode="json") == {
        "type": "get_after_game_report",
        "game_id": "demo",
        "request_id": "after-game-1",
    }


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
                "type": "message",
                "game_id": "g",
                "body": "hi",
            },
            "destination",
        ),
        (
            {
                "type": "message",
                "game_id": "g",
                "body": "hi",
                "destination": "Orange",
                "from": "Blue",
            },
            "destination",
        ),
        (
            {
                "type": "message",
                "game_id": "g",
                "destination": "Orange",
                "body": " ",
            },
            "body",
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
        (
            {
                "type": "get_current_phase",
                "request_id": "current-1",
                "game_id": "demo",
                "player_id": "Blue",
            },
            "player_id",
        ),
        (
            {
                "type": "get_after_game_report",
                "request_id": "after-game-1",
                "game_id": "demo",
                "command": "get_after_game_report",
            },
            "command",
        ),
        (
            {
                "type": "get_after_game_report",
                "request_id": "after-game-1",
                "game_id": "demo",
                "phase_id": "demo:turn-24:movement",
            },
            "phase_id",
        ),
    ],
)
def test_invalid_messages_fail_with_structured_errors(payload, expected_field):
    if payload.get("type") == "get_current_phase":
        parser = parse_get_current_phase_request
    elif payload.get("type") == "get_after_game_report":
        parser = parse_get_after_game_report_request
    else:
        parser = parse_message_body

    with pytest.raises(StructuredValidationError) as exc_info:
        parser(payload)

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
