import subprocess
from io import StringIO

import pytest
from clanker_courts_player.clankmates import ClankmatesClient, ClankmatesError


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
