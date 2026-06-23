import json
from pathlib import Path

from clanker_courts_player.mcp_server import TOOL_NAMES
from clanker_courts_player.runtime_manager import RunManager

FIXTURES = Path(__file__).parent / "fixtures"


class FakeClient:
    calls: list[tuple] = []

    def send(self, profile, recipient, body):
        self.calls.append(("send", profile, recipient, body))
        return {"thread_id": f"thread-{profile}"}

    def reply(self, profile, thread_id, body):
        self.calls.append(("reply", profile, thread_id, body))
        return {"ok": True, "thread_id": thread_id}


def manager(tmp_path):
    return RunManager(tmp_path, client_factory=FakeClient)


def test_manager_creates_isolated_runs_and_requires_run_token(tmp_path):
    runtime = manager(tmp_path)
    admin_token = runtime.registry.ensure_admin_token()

    first = runtime.admin_create_run(
        admin_token,
        profile="cc_blue",
        server="@server",
        game_id="game-1",
    )
    second = runtime.admin_create_run(
        admin_token,
        profile="cc_orange",
        server="@server",
        game_id="game-1",
    )

    assert first["run_id"] != second["run_id"]
    assert runtime.runtime_status(first["run_id"], first["run_token"])["profile"] == "cc_blue"
    payload = runtime.runtime_status(second["run_id"], second["run_token"])
    assert payload["profile"] == "cc_orange"

    try:
        runtime.runtime_status(second["run_id"], first["run_token"])
    except Exception as exc:
        assert exc.code == "unauthorized"
    else:
        raise AssertionError("run token should not cross runs")


def test_decision_context_reads_local_cache_without_clankmates_call(tmp_path):
    FakeClient.calls = []
    runtime = manager(tmp_path)
    admin_token = runtime.registry.ensure_admin_token()
    created = runtime.admin_create_run(
        admin_token,
        profile="cc_blue",
        server="@server",
        game_id="game-1",
    )
    artifact_dir = Path(created["artifact_dir"])
    state = json.loads((artifact_dir / "state.json").read_text())
    current = json.loads((FIXTURES / "get_current_phase_open.json").read_text())
    state.update(
        {
            "status": "active",
            "player_id": "Blue",
            "players": ["Blue", "Orange"],
            "capital_location_id": "B",
            "latest_current_phase_response": current,
            "allowed_command": current["allowed_command"],
            "visible_state": current["visible_state"],
            "current_phase": current["current_phase"],
            "phase_id": current["current_phase"]["phase_id"],
            "turn": current["current_phase"]["turn"],
            "phase": current["current_phase"]["phase"],
        }
    )
    (artifact_dir / "state.json").write_text(json.dumps(state))
    calls_after_join = list(FakeClient.calls)

    context = runtime.decision_context(created["run_id"], created["run_token"])

    assert context["decision_request_id"] == "game-1-cc-blue:demo:turn-02:movement"
    assert context["recommended_next"]["kind"] == "current"
    assert FakeClient.calls == calls_after_join


def test_submit_decision_rejects_stale_request_before_reply(tmp_path):
    FakeClient.calls = []
    runtime = manager(tmp_path)
    admin_token = runtime.registry.ensure_admin_token()
    created = runtime.admin_create_run(
        admin_token,
        profile="cc_blue",
        server="@server",
        game_id="game-1",
    )
    artifact_dir = Path(created["artifact_dir"])
    state = json.loads((artifact_dir / "state.json").read_text())
    state["phase_id"] = "phase-current"
    (artifact_dir / "state.json").write_text(json.dumps(state))
    calls_after_join = list(FakeClient.calls)

    try:
        runtime.submit_decision(
            created["run_id"],
            created["run_token"],
            decision_request_id="old",
            phase_id="phase-current",
            orders=[],
            rationale="fallback",
        )
    except Exception as exc:
        assert exc.code == "stale_decision_request"
    else:
        raise AssertionError("stale request should be rejected")

    assert FakeClient.calls == calls_after_join


def test_mcp_tool_surface_includes_admin_and_runtime_tools():
    for name in [
        "admin_create_run",
        "admin_list_runs",
        "runtime_status",
        "decision_context",
        "submit_decision",
        "runtime_refresh_current",
    ]:
        assert name in TOOL_NAMES
