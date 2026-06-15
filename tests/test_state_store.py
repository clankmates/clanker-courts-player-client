import json
from pathlib import Path

from clanker_courts_player.messages import stale_rejection_recovery_hints
from clanker_courts_player.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures"


def test_state_store_atomic_save_and_load_json(tmp_path):
    store = StateStore(tmp_path / "state.json")
    state = {"schema_version": 1, "game_id": "demo", "seen": {"message_ids": []}}

    store.save(state)

    assert store.load() == state
    assert not list(tmp_path.glob("*.tmp"))


def test_state_store_appends_raw_jsonl_archive(tmp_path):
    store = StateStore(tmp_path / "state.json")

    store.append_raw_message({"id": "m1", "body": "one"})
    store.append_raw_message({"id": "m2", "body": {"nested": True}})

    archive = tmp_path / "raw_messages.jsonl"
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    assert rows == [{"id": "m1", "body": "one"}, {"id": "m2", "body": {"nested": True}}]


def test_apply_incremental_messages_archives_unseen_records_and_skips_duplicates(tmp_path):
    store = StateStore(tmp_path / "state.json")
    state = {"processed_message_ids": ["m1"]}
    messages = [
        {
            "message_id": "m1",
            "thread_id": "thread-1",
            "timestamp": "2026-06-14T10:00:00Z",
            "body": {"type": "ready_check", "game_id": "demo"},
            "raw": {"id": "m1"},
        },
        {
            "message_id": "m2",
            "thread_id": "thread-1",
            "timestamp": "2026-06-14T10:01:00Z",
            "body": {"type": "setup_report", "game_id": "demo"},
            "raw": {"id": "m2"},
        },
    ]

    result = store.apply_incremental_messages(state, messages)

    assert result["processed"] == 1
    assert result["duplicates_skipped"] == 1
    assert store.load()["processed_message_ids"] == ["m1", "m2"]
    rows = [json.loads(line) for line in (tmp_path / "raw_messages.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["message_id"] == "m2"
    assert rows[0]["thread_id"] == "thread-1"
    assert rows[0]["server_timestamp"] == "2026-06-14T10:01:00Z"
    assert rows[0]["local_timestamp"].endswith("Z")
    assert rows[0]["payload_type"] == "setup_report"


def test_apply_incremental_messages_no_change_cycle_saves_state_without_archive(tmp_path):
    store = StateStore(tmp_path / "state.json")

    result = store.apply_incremental_messages({"processed_message_ids": ["m1"]}, [])

    assert result["processed"] == 0
    assert result["duplicates_skipped"] == 0
    assert store.load()["processed_message_ids"] == ["m1"]
    assert not (tmp_path / "raw_messages.jsonl").exists()


def test_current_phase_response_updates_state_before_order_preparation(tmp_path):
    store = StateStore(tmp_path / "state.json")
    current_phase = json.loads((FIXTURES / "get_current_phase_open.json").read_text())

    result = store.apply_incremental_messages(
        {},
        [
            {
                "message_id": "m-current",
                "thread_id": "thread-1",
                "timestamp": "2026-06-14T18:01:00Z",
                "body": current_phase,
                "raw": {"id": "m-current"},
            }
        ],
    )

    state = store.load()
    assert result["processed"] == 1
    assert state["phase_id"] == "demo:turn-02:movement"
    assert state["phase_status"] == "open"
    assert state["allowed_command"]["accepting"] is True
    assert state["latest_report"]["report_hash"] == "sha256:open-phase-report"
    assert state["visible_state"]["locations"][0]["location_id"] == "B"


def test_stale_rejection_records_recovery_instructions_without_replay(tmp_path):
    store = StateStore(tmp_path / "state.json")
    stale_rejection = json.loads((FIXTURES / "order_rejected_stale_recovery.json").read_text())

    assert stale_rejection_recovery_hints(stale_rejection) == {
        "reason": "stale_phase",
        "action": "get_current_phase",
        "replay_stale_thread": False,
        "expected_phase_id": "demo:turn-02:reinforcement",
        "current_phase": {
            "phase_id": "demo:turn-02:reinforcement",
            "turn": 2,
            "phase": "reinforcement",
            "status": "open",
            "deadline_at": "2026-06-14T18:45:00Z",
        },
    }

    store.apply_incremental_messages(
        {},
        [
            {
                "message_id": "m-stale",
                "thread_id": "thread-1",
                "timestamp": "2026-06-14T18:02:00Z",
                "body": stale_rejection,
                "raw": {"id": "m-stale"},
            }
        ],
    )

    recovery = store.load()["stale_rejection_recovery"]
    assert recovery["action"] == "get_current_phase"
    assert recovery["replay_stale_thread"] is False
    assert recovery["expected_phase_id"] == "demo:turn-02:reinforcement"


def test_after_game_report_records_winners_and_final_standings(tmp_path):
    store = StateStore(tmp_path / "state.json")
    after_game = json.loads((FIXTURES / "after_game_report.json").read_text())

    store.apply_incremental_messages(
        {},
        [
            {
                "message_id": "m-final",
                "thread_id": "thread-1",
                "timestamp": "2026-06-14T18:03:00Z",
                "body": after_game,
                "raw": {"id": "m-final"},
            }
        ],
    )

    state = store.load()
    assert state["status"] == "ended"
    assert state["winners"] == ["@alice/bluebot", "@orange/orangebot"]
    assert state["final_standings"][0]["placement_rank"] == 1
    assert state["match_points"][0]["total_points"] == 15.0


def test_ended_current_phase_points_state_at_after_game_report(tmp_path):
    store = StateStore(tmp_path / "state.json")
    ended = json.loads((FIXTURES / "get_current_phase_ended.json").read_text())

    store.apply_incremental_messages(
        {},
        [
            {
                "message_id": "m-ended",
                "thread_id": "thread-1",
                "timestamp": "2026-06-14T18:04:00Z",
                "body": ended,
                "raw": {"id": "m-ended"},
            }
        ],
    )

    state = store.load()
    assert state["status"] == "ended"
    assert state["current_phase"] is None
    assert state["allowed_command"]["command"] == "get_after_game_report"
