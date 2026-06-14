import json

from clanker_courts_player.state_store import StateStore


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
