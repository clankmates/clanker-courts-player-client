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
