import json

import pytest

from clanker_courts_player.cli import main


def _json_body(body):
    return json.dumps(body, separators=(",", ":"), sort_keys=True)


@pytest.mark.parametrize(
    ("send_response", "expected_thread_id"),
    [
        ({"thread_id": "thread-direct"}, "thread-direct"),
        ({"threadId": "thread-camel"}, "thread-camel"),
        ({"thread": {"id": "thread-nested"}}, "thread-nested"),
        ({"data": {"thread_id": "thread-data"}}, "thread-data"),
        ({"message": {"thread_id": "thread-message"}}, "thread-message"),
    ],
)
def test_join_sends_join_game_and_records_initial_state(
    tmp_path, monkeypatch, capsys, send_response, expected_thread_id
):
    calls = []

    class FakeClient:
        def whoami(self, profile):
            calls.append(("whoami", profile))
            return {"handle": "bluebot", "base_url": "ignored"}

        def send(self, profile, recipient, body):
            calls.append(("send", profile, recipient, body))
            return send_response

    import clanker_courts_player.clankmates as clankmates_module

    monkeypatch.setattr(clankmates_module, "ClankmatesClient", FakeClient)
    state_path = tmp_path / "demo" / "state.json"

    exit_code = main(
        [
            "join",
            "--profile",
            "local-blue",
            "--base-url",
            "http://localhost:4000",
            "--server",
            "@courts-server",
            "--game-id",
            "demo",
            "--state",
            str(state_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    state = json.loads(state_path.read_text())
    assert exit_code == 0
    assert calls == [
        ("whoami", "local-blue"),
        (
            "send",
            "local-blue",
            "@courts-server",
            {"type": "join_game", "game_id": "demo", "handle": "bluebot"},
        ),
    ]
    assert payload["ok"] is True
    assert payload["thread_id"] == expected_thread_id
    assert payload["send_response"] == send_response
    assert state["schema_version"] == 1
    assert state["game_id"] == "demo"
    assert state["server"] == {
        "recipient": "@courts-server",
        "thread_id": expected_thread_id,
        "base_url": "http://localhost:4000",
    }
    assert state["clankmates"] == {"profile": "local-blue", "handle": "bluebot"}
    assert state["seen"] == {"message_ids": [], "request_ids": []}
    assert state["reports"] == []
    assert state["submissions"] == []
    assert state["diplomacy"] == {"sent": [], "received": []}
    assert state["promises"] == {"made": [], "received": [], "resolved": []}


def test_poll_archives_raw_messages_and_updates_state_from_server_events(
    tmp_path, monkeypatch, capsys
):
    state_path = tmp_path / "demo" / "state.json"
    state_path.parent.mkdir()
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "game_id": "demo",
                "server": {
                    "recipient": "@courts-server",
                    "thread_id": "thread-server",
                    "base_url": "http://localhost:4000",
                },
                "clankmates": {"profile": "local-blue", "handle": "bluebot"},
                "seen": {"message_ids": ["m-seen"], "request_ids": []},
                "reports": [],
                "submissions": [],
                "diplomacy": {"sent": [], "received": []},
                "promises": {"made": [], "received": [], "resolved": []},
            }
        )
        + "\n"
    )

    join_ack = {
        "id": "m-ack",
        "thread_id": "thread-server",
        "created_at": "2026-06-03T00:00:00Z",
        "attributes": {
            "body": _json_body(
                {
                    "type": "join_ack",
                    "game_id": "demo",
                    "status": "waiting",
                    "joined": 1,
                    "required": 3,
                }
            )
        },
    }
    game_started = {
        "id": "m-started",
        "thread_id": "thread-server",
        "created_at": "2026-06-03T00:01:00Z",
        "attributes": {
            "body": _json_body(
                {
                    "type": "game_started",
                    "game_id": "demo",
                    "player_id": "blue",
                    "ruleset_id": "clanker-courts-v9",
                    "reports": [
                        {
                            "type": "setup_report",
                            "player_id": "blue",
                            "capital_location_id": "B",
                            "players": [{"player_id": "blue"}, {"player_id": "red"}],
                        }
                    ],
                    "communication_rules": {},
                    "status": {"turn": 1, "phase": "reinforcement"},
                }
            )
        },
    }
    old_phase_request = {
        "id": "m-old-request",
        "thread_id": "thread-server",
        "created_at": "2026-06-03T00:02:00Z",
        "attributes": {
            "body": _json_body(
                {
                    "type": "phase_request",
                    "game_id": "demo",
                    "request_id": "req-old",
                    "player_id": "blue",
                    "turn": 1,
                    "phase": "reinforcement",
                    "status": {},
                    "reports": [{"type": "reinforcement_report", "turn": 1}],
                    "deadline_ms": 5000,
                }
            )
        },
    }
    latest_phase_request = {
        "id": "m-new-request",
        "thread_id": "thread-server",
        "created_at": "2026-06-03T00:03:00Z",
        "attributes": {
            "body": _json_body(
                {
                    "type": "phase_request",
                    "game_id": "demo",
                    "request_id": "req-new",
                    "player_id": "blue",
                    "turn": 1,
                    "phase": "movement",
                    "status": {"phase": "movement"},
                    "reports": [{"type": "movement_visibility_report", "turn": 1}],
                    "deadline_ms": 6000,
                }
            )
        },
    }
    seen_duplicate = {
        "id": "m-seen",
        "thread_id": "thread-server",
        "created_at": "2026-06-03T00:04:00Z",
        "attributes": {
            "body": _json_body(
                {
                    "type": "phase_request",
                    "game_id": "demo",
                    "request_id": "req-seen",
                    "player_id": "blue",
                    "turn": 99,
                    "phase": "movement",
                    "status": {},
                    "reports": [],
                }
            )
        },
    }
    other_game = {
        "id": "m-other",
        "thread_id": "thread-server",
        "created_at": "2026-06-03T00:05:00Z",
        "attributes": {"body": _json_body({"type": "join_ack", "game_id": "other"})},
    }

    class FakeClient:
        def show_thread(self, profile, thread_id, *, limit=10, cursor=None):
            assert profile == "local-blue"
            assert thread_id == "thread-server"
            assert limit == 25
            assert cursor is None
            return {
                "messages": [
                    seen_duplicate,
                    join_ack,
                    other_game,
                    game_started,
                    old_phase_request,
                    latest_phase_request,
                ]
            }

    import clanker_courts_player.clankmates as clankmates_module

    monkeypatch.setattr(clankmates_module, "ClankmatesClient", FakeClient)

    exit_code = main(["poll", "--state", str(state_path), "--limit", "25"])

    payload = json.loads(capsys.readouterr().out)
    state = json.loads(state_path.read_text())
    raw_rows = [
        json.loads(line)
        for line in (state_path.parent / "raw_messages.jsonl").read_text().splitlines()
    ]
    event_rows = [
        json.loads(line) for line in (state_path.parent / "events.jsonl").read_text().splitlines()
    ]
    assert exit_code == 0
    assert [row["id"] for row in raw_rows] == [
        "m-seen",
        "m-ack",
        "m-other",
        "m-started",
        "m-old-request",
        "m-new-request",
    ]
    assert payload["ok"] is True
    assert payload["processed"] == 4
    assert payload["ignored"]["duplicate_message_ids"] == ["m-seen"]
    assert payload["ignored"]["unrelated_game_ids"] == ["m-other"]
    assert [event["type"] for event in payload["events"]] == [
        "join_ack",
        "game_started",
        "phase_request",
    ]
    assert state["join"] == {"status": "waiting", "joined": 1, "required": 3}
    assert state["player"]["player_id"] == "blue"
    assert state["player"]["capital_location_id"] == "B"
    assert state["player"]["known_players"] == ["blue", "red"]
    assert state["phase"] == {
        "turn": 1,
        "phase": "movement",
        "request_id": "req-new",
        "deadline_ms": 6000,
    }
    assert state["reports"] == [{"type": "movement_visibility_report", "turn": 1}]
    assert state["seen"]["message_ids"] == [
        "m-seen",
        "m-ack",
        "m-started",
        "m-old-request",
        "m-new-request",
    ]
    assert event_rows == payload["events"]


def test_poll_requires_join_state_with_server_thread(tmp_path, capsys):
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"schema_version": 1, "game_id": "demo"}) + "\n")

    exit_code = main(["poll", "--state", str(state_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert "server.thread_id" in payload["error"]
