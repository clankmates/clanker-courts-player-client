import json
import subprocess
from pathlib import Path

import pytest
from clanker_courts_player.clankmates import ClankmatesClient, ClankmatesError
from clanker_courts_player.cli import main


def test_reply_uses_exact_clankm_argv_and_json_body():
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout='{"ok":true}', stderr="")

    client = ClankmatesClient(runner=runner)
    body = {"type": "order_package", "orders": []}

    assert client.reply("p1", "thread-1", body) == {"ok": True}
    assert calls[0][0] == [
        "clankm",
        "--profile",
        "p1",
        "inbox",
        "reply",
        "thread-1",
        "--payload",
        json.dumps(body, separators=(",", ":"), sort_keys=True),
        "--json",
    ]


def test_adapter_methods_parse_json_and_build_expected_commands():
    calls = []
    responses = iter(
        [
            '{"handle":"bluebot"}',
            '{"threads":[]}',
            '{"messages":[]}',
            '{"messages":[{"id":"m2"}]}',
            '{"archived":true}',
            '{"sent":true}',
        ]
    )

    def runner(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=next(responses), stderr="")

    client = ClankmatesClient(runner=runner)

    assert client.whoami("p") == {"handle": "bluebot"}
    assert client.list_threads("p") == {"threads": []}
    assert client.show_thread("p", "t1", limit=3) == {"messages": []}
    assert client.message_changes(
        "p", "t1", since="2026-06-14T10:00:00Z", since_cache="server", save_cache="server"
    ) == {"messages": [{"id": "m2"}]}
    assert client.archive_thread("p", "t1") == {"archived": True}
    assert client.send("p", "@server", {"type": "join_game"}) == {"sent": True}
    assert calls == [
        ["clankm", "--profile", "p", "auth", "whoami", "--json"],
        ["clankm", "--profile", "p", "inbox", "list", "--status", "all", "--json"],
        ["clankm", "--profile", "p", "inbox", "show", "t1", "--limit", "3", "--json"],
        [
            "clankm",
            "--profile",
            "p",
            "inbox",
            "messages",
            "changes",
            "t1",
            "--since",
            "2026-06-14T10:00:00Z",
            "--since-cache",
            "server",
            "--save-cache",
            "server",
            "--json",
        ],
        ["clankm", "--profile", "p", "inbox", "archive", "t1", "--json"],
        [
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
    ]


def test_watch_messages_parses_jsonl_records():
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"id":"m1"}\n{"id":"m2","body":"{}"}\n',
            stderr="",
        )

    client = ClankmatesClient(runner=runner)

    assert client.watch_messages("p", "t1") == [{"id": "m1"}, {"id": "m2", "body": "{}"}]
    assert calls == [["clankm", "--profile", "p", "inbox", "watch", "messages", "t1"]]


def test_watch_messages_reports_malformed_jsonl_line():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout='{"id":"m1"}\n{bad\n', stderr="")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.watch_messages("p", "t1")

    assert exc_info.value.to_dict()["decode_error"].startswith("line 2:")


def test_legacy_polling_command_still_available_for_manual_debug():
    calls = []
    responses = iter(
        [
            '{"messages":[]}',
            '{"archived":true}',
            '{"sent":true}',
        ]
    )

    def runner(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=next(responses), stderr="")

    client = ClankmatesClient(runner=runner)

    assert client.show_thread("p", "t1", limit=3) == {"messages": []}
    assert client.archive_thread("p", "t1") == {"archived": True}
    assert client.send("p", "@server", {"type": "join_game"}) == {"sent": True}
    assert calls == [
        ["clankm", "--profile", "p", "inbox", "show", "t1", "--limit", "3", "--json"],
        ["clankm", "--profile", "p", "inbox", "archive", "t1", "--json"],
        [
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
    ]


def test_non_zero_exit_returns_structured_error():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 17, stdout="out", stderr="err")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.whoami("p")

    assert exc_info.value.to_dict() == {
        "ok": False,
        "command": ["clankm", "--profile", "p", "auth", "whoami", "--json"],
        "returncode": 17,
        "stdout": "out",
        "stderr": "err",
    }


def test_malformed_json_returns_structured_error():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout="{bad json", stderr="")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.list_threads("p")

    assert exc_info.value.to_dict()["decode_error"].startswith("Expecting property name")


def test_missing_clankm_binary_returns_structured_error():
    def runner(argv, **kwargs):
        raise FileNotFoundError("clankm")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.whoami("p")

    payload = exc_info.value.to_dict()
    assert payload["command"] == ["clankm", "--profile", "p", "auth", "whoami", "--json"]
    assert payload["returncode"] is None
    assert payload["stderr"] == "clankm"


def test_timeout_returns_structured_error():
    def runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 5, output="partial out", stderr="partial err")

    client = ClankmatesClient(runner=runner)

    with pytest.raises(ClankmatesError) as exc_info:
        client.whoami("p")

    payload = exc_info.value.to_dict()
    assert payload["returncode"] is None
    assert payload["timeout"] == 5
    assert payload["stdout"] == "partial out"
    assert payload["stderr"] == "partial err"


def test_preflight_cli_prints_structured_json_when_clankmates_errors(monkeypatch, capsys):
    class FakeClient:
        def whoami(self, profile):
            raise ClankmatesError(
                command=["clankm", "--profile", profile, "auth", "whoami", "--json"],
                returncode=None,
                stdout="",
                stderr="clankm missing",
            )

    import clanker_courts_player.clankmates as clankmates_module

    monkeypatch.setattr(clankmates_module, "ClankmatesClient", FakeClient)

    exit_code = main(["preflight", "--profile", "p", "--base-url", "http://localhost:4000"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["stderr"] == "clankm missing"


def test_ready_cli_replies_on_server_thread(monkeypatch, capsys):
    calls = []

    class FakeClient:
        def reply(self, profile, thread_id, body):
            calls.append((profile, thread_id, body))
            return {"replied": True}

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(
        [
            "ready",
            "--profile",
            "p",
            "--thread-id",
            "thread-1",
            "--game-id",
            "demo",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert calls == [("p", "thread-1", {"type": "ready_to_start", "game_id": "demo"})]
    assert payload["thread_id"] == "thread-1"


def test_submit_orders_cli_replies_on_server_thread(monkeypatch, capsys):
    calls = []

    class FakeClient:
        def reply(self, profile, thread_id, body):
            calls.append((profile, thread_id, body))
            return {"replied": True}

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(
        [
            "submit-orders",
            "--profile",
            "p",
            "--thread-id",
            "thread-1",
            "--game-id",
            "demo",
            "--phase-id",
            "demo:turn-01:movement",
            "--orders-json",
            '[{"kind":"move","from":"B","to":"M","troops":3}]',
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert calls == [
        (
            "p",
            "thread-1",
            {
                "type": "order_package",
                "game_id": "demo",
                "phase_id": "demo:turn-01:movement",
                "orders": [{"kind": "move", "from": "B", "to": "M", "troops": 3}],
            },
        )
    ]
    assert payload["thread_id"] == "thread-1"


def test_freshen_cli_uses_message_changes_and_archives_incremental_messages(
    monkeypatch, capsys, tmp_path
):
    calls = []

    class FakeClient:
        def message_changes(self, profile, thread_id, *, since, since_cache, save_cache):
            calls.append((profile, thread_id, since, since_cache, save_cache))
            return {
                "messages": [
                    {
                        "id": "m1",
                        "thread_id": "thread-1",
                        "created_at": "2026-06-14T10:00:00Z",
                        "attributes": {"body": '{"type":"ready_check","game_id":"demo"}'},
                    }
                ]
            }

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())
    state_path = tmp_path / "state.json"

    exit_code = main(
        [
            "freshen",
            "--profile",
            "p",
            "--thread-id",
            "thread-1",
            "--state",
            str(state_path),
            "--since-cache",
            "game-demo-server",
            "--save-cache",
            "game-demo-server",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert calls == [("p", "thread-1", None, "game-demo-server", "game-demo-server")]
    assert payload["primitive"] == "inbox messages changes"
    assert payload["processed"] == 1
    archive = tmp_path / "raw_messages.jsonl"
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    assert rows[0]["message_id"] == "m1"
    assert rows[0]["payload_type"] == "ready_check"


def test_freshen_cli_reports_no_changes_without_archive(monkeypatch, capsys, tmp_path):
    class FakeClient:
        def message_changes(self, profile, thread_id, *, since, since_cache, save_cache):
            return {"messages": []}

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(
        [
            "freshen",
            "--profile",
            "p",
            "--thread-id",
            "thread-1",
            "--state",
            str(tmp_path / "state.json"),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["no_changes"] is True
    assert payload["processed"] == 0
    assert not (tmp_path / "raw_messages.jsonl").exists()


def test_freshen_cli_falls_back_to_bounded_show_for_stale_clankm(
    monkeypatch, capsys, tmp_path
):
    calls = []

    class FakeClient:
        def message_changes(self, profile, thread_id, *, since, since_cache, save_cache):
            calls.append("changes")
            raise ClankmatesError(
                command=["clankm", "inbox", "messages", "changes"],
                returncode=2,
                stdout="",
                stderr="unknown command: changes",
            )

        def show_thread(self, profile, thread_id, *, limit=10, cursor=None):
            calls.append(("show", limit, cursor))
            return {
                "messages": [
                    {
                        "id": "m2",
                        "thread_id": "thread-1",
                        "created_at": "2026-06-14T10:00:00Z",
                        "attributes": {"body": '{"type":"setup_report","game_id":"demo"}'},
                    }
                ]
            }

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(
        [
            "freshen",
            "--profile",
            "p",
            "--thread-id",
            "thread-1",
            "--state",
            str(tmp_path / "state.json"),
            "--limit",
            "7",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert calls == ["changes", ("show", 7, None)]
    assert payload["primitive"] == "inbox show fallback"
    assert payload["processed"] == 1


def test_watch_messages_cli_archives_jsonl_records(monkeypatch, capsys, tmp_path):
    class FakeClient:
        def watch_messages(self, profile, thread_id):
            return [
                {
                    "id": "m3",
                    "thread_id": "thread-1",
                    "created_at": "2026-06-14T10:00:00Z",
                    "attributes": {"body": '{"type":"movement_phase_report","game_id":"demo"}'},
                }
            ]

    import clanker_courts_player.cli as cli_module

    monkeypatch.setattr(cli_module, "_clankmates_client", lambda: FakeClient())

    exit_code = main(
        [
            "watch-messages",
            "--profile",
            "p",
            "--thread-id",
            "thread-1",
            "--state",
            str(tmp_path / "state.json"),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["primitive"] == "inbox watch messages"
    assert payload["processed"] == 1
    archive = Path(tmp_path / "raw_messages.jsonl")
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    assert rows[0]["payload_type"] == "movement_phase_report"
