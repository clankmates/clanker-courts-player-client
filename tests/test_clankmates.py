import json
import subprocess
from io import StringIO

import pytest
from clanker_courts_player.clankmates import ClankmatesClient, ClankmatesError
from clanker_courts_player.cli import main


def test_send_and_reply_use_exact_clankm_argv_and_json_body():
    calls = []
    responses = iter(['{"thread_id":"thread-1"}', '{"ok":true}'])

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout=next(responses), stderr="")

    client = ClankmatesClient(runner=runner)

    assert client.send("p1", "@server", {"type": "join_game", "game_id": "demo"}) == {
        "thread_id": "thread-1"
    }
    assert client.reply("p1", "thread-1", {"type": "ready_to_start"}) == {"ok": True}
    assert calls[0][0] == [
        "clankm",
        "--profile",
        "p1",
        "inbox",
        "send",
        "@server",
        "--payload",
        '{"game_id":"demo","type":"join_game"}',
        "--json",
    ]
    assert calls[1][0] == [
        "clankm",
        "--profile",
        "p1",
        "inbox",
        "reply",
        "thread-1",
        "--payload",
        '{"type":"ready_to_start"}',
        "--json",
    ]


def test_watch_messages_parses_jsonl_records():
    calls = []

    class FakeProcess:
        stdout = StringIO('{"id":"m1"}\n{"id":"m2","body":"{}"}\n')
        stderr = StringIO("")

        def wait(self):
            return 0

    def popen_runner(argv, **kwargs):
        calls.append(argv)
        return FakeProcess()

    client = ClankmatesClient(popen_runner=popen_runner)

    assert client.watch_messages("p", "t1") == [{"id": "m1"}, {"id": "m2", "body": "{}"}]
    assert calls == [["clankm", "--profile", "p", "inbox", "watch", "messages", "t1", "--once"]]


def test_watch_messages_reports_malformed_jsonl_line():
    class FakeProcess:
        stdout = StringIO('{"id":"m1"}\n{bad\n')
        stderr = StringIO("")

        def poll(self):
            return 0

        def terminate(self):
            pass

        def kill(self):
            pass

        def wait(self, timeout=None):
            return 0

    def popen_runner(argv, **kwargs):
        return FakeProcess()

    client = ClankmatesClient(popen_runner=popen_runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.watch_messages("p", "t1")

    assert exc_info.value.to_dict()["decode_error"].startswith("line 2:")


def test_non_zero_exit_returns_structured_error():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 17, stdout="out", stderr="err")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.send("p", "@server", {"type": "join_game"})

    assert exc_info.value.to_dict() == {
        "ok": False,
        "command": [
            "clankm",
            "--profile",
            "p",
            "inbox",
            "send",
            "@server",
            "--payload",
            '{"type":"join_game"}',
            "--json",
        ],
        "returncode": 17,
        "stdout": "out",
        "stderr": "err",
    }


def test_malformed_json_returns_structured_error():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout="{bad json", stderr="")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.send("p", "@server", {"type": "join_game"})

    assert exc_info.value.to_dict()["decode_error"].startswith("Expecting property name")


def test_missing_clankm_binary_returns_structured_error():
    def runner(argv, **kwargs):
        raise FileNotFoundError("clankm")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.send("p", "@server", {"type": "join_game"})

    payload = exc_info.value.to_dict()
    assert payload["command"][:5] == ["clankm", "--profile", "p", "inbox", "send"]
    assert payload["returncode"] is None
    assert payload["stderr"] == "clankm"


def test_timeout_returns_structured_error():
    def runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 5, output="partial out", stderr="partial err")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.reply("p", "thread-1", {"type": "ready_to_start"})

    payload = exc_info.value.to_dict()
    assert payload["returncode"] is None
    assert payload["timeout"] == 5
    assert payload["stdout"] == "partial out"
    assert payload["stderr"] == "partial err"


def test_join_persists_thread_and_command_artifact(monkeypatch, capsys, tmp_path):
    calls = []

    class FakeClient:
        def send(self, profile, recipient, body):
            calls.append((profile, recipient, body))
            return {"thread_id": "thread-1", "sent": True}

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(
        [
            "join",
            "--profile",
            "p",
            "--server",
            "@gamemaster/clanker_courts",
            "--game-id",
            "demo",
            "--artifact-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert calls == [("p", "@gamemaster/clanker_courts", {"type": "join_game", "game_id": "demo"})]
    assert payload["server_thread_id"] == "thread-1"
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["profile"] == "p"
    assert state["server_thread_id"] == "thread-1"
    command = json.loads((tmp_path / "submitted_commands.jsonl").read_text().splitlines()[0])
    assert command["command_type"] == "join_game"
    assert command["recipient"] == "@gamemaster/clanker_courts"


def test_stateful_commands_reply_on_saved_thread(monkeypatch, capsys, tmp_path):
    state = {
        "schema_version": 1,
        "profile": "p",
        "server": "@server",
        "game_id": "demo",
        "server_thread_id": "thread-1",
        "processed_message_ids": [],
    }
    (tmp_path / "state.json").write_text(json.dumps(state))
    calls = []

    class FakeClient:
        def reply(self, profile, thread_id, body):
            calls.append((profile, thread_id, body))
            return {"replied": True}

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(["orders", "--artifact-dir", str(tmp_path), "--phase-id", "p1"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert calls == [
        (
            "p",
            "thread-1",
            {"type": "order_package", "phase_id": "p1", "orders": [], "game_id": "demo"},
        )
    ]
    assert payload["server_thread_id"] == "thread-1"
    row = json.loads((tmp_path / "submitted_commands.jsonl").read_text().splitlines()[0])
    assert row["command_type"] == "order_package"


def test_watch_uses_saved_thread_and_archives_messages(monkeypatch, capsys, tmp_path):
    state = {
        "schema_version": 1,
        "profile": "p",
        "server": "@server",
        "game_id": "demo",
        "server_thread_id": "thread-1",
        "processed_message_ids": [],
    }
    (tmp_path / "state.json").write_text(json.dumps(state))
    calls = []

    class FakeClient:
        def iter_watch_messages(self, profile, thread_id, *, once):
            calls.append((profile, thread_id, once))
            yield {
                "id": "m1",
                "thread_id": "thread-1",
                "created_at": "2026-06-14T10:00:00Z",
                "attributes": {
                    "body": json.dumps(
                        {
                            "type": "setup_report",
                            "game_id": "demo",
                            "phase_id": "demo:turn-01:reinforcement",
                            "turn": 1,
                            "phase": "reinforcement",
                        }
                    )
                },
            }

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(["watch", "--artifact-dir", str(tmp_path), "--once"])

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert exit_code == 0
    assert calls == [("p", "thread-1", True)]
    assert rows[-1]["event"] == "watch_complete"
    assert rows[-1]["processed"] == 1
    archive = [
        json.loads(line)
        for line in (tmp_path / "raw_messages.jsonl").read_text().splitlines()
    ]
    assert archive[0]["payload_type"] == "setup_report"
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["phase_id"] == "demo:turn-01:reinforcement"


def test_missing_server_thread_fails_without_discovery(capsys, tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"profile": "p", "game_id": "demo"}))

    exit_code = main(["ready", "--artifact-dir", str(tmp_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["error"]["code"] == "missing_server_thread"
    assert payload["error"]["recovery"] == "run recover-thread with the known server thread id"


def test_recover_thread_writes_state_for_subsequent_commands(capsys, tmp_path):
    exit_code = main(
        [
            "recover-thread",
            "--artifact-dir",
            str(tmp_path),
            "--thread-id",
            "thread-recovered",
            "--profile",
            "p",
            "--server",
            "@server",
            "--game-id",
            "demo",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    state = json.loads((tmp_path / "state.json").read_text())
    assert exit_code == 0
    assert payload["server_thread_id"] == "thread-recovered"
    assert state["server_thread_id"] == "thread-recovered"


def test_recover_thread_repairs_partial_existing_state(capsys, tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"schema_version": 1}))

    exit_code = main(
        [
            "recover-thread",
            "--artifact-dir",
            str(tmp_path),
            "--thread-id",
            "thread-recovered",
            "--profile",
            "p",
            "--server",
            "@server",
            "--game-id",
            "demo",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    state = json.loads((tmp_path / "state.json").read_text())
    assert exit_code == 0
    assert payload["server_thread_id"] == "thread-recovered"
    assert state["profile"] == "p"
    assert state["server"] == "@server"
    assert state["game_id"] == "demo"
    assert state["processed_message_ids"] == []
