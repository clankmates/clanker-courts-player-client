from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from clanker_courts_autoplayer.context import (
    append_decision_journal,
    append_ledger_note,
    build_phase_context,
    safe_fallback_orders,
)

from .clankmates import ClankmatesClient, ClankmatesError
from .runtime_registry import RegistryError, RunRegistry
from .state_store import StateStore

ClientFactory = Callable[[], ClankmatesClient]


class RuntimeErrorPayload(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_payload(self) -> dict[str, Any]:
        return {"ok": False, "error": {"code": self.code, "message": self.message}}


class RunManager:
    def __init__(
        self,
        runs_root: str | Path,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.registry = RunRegistry(runs_root)
        self.client_factory = client_factory or ClankmatesClient
        self._runtimes: dict[str, PlayerRuntime] = {}
        self._lock = threading.RLock()

    def admin_create_run(self, admin_token: str, **kwargs: Any) -> dict[str, Any]:
        self.registry.verify_admin(admin_token)
        credentials = self.registry.create_run(**kwargs)
        run = self.registry.get_run(credentials.run_id)
        runtime = self._runtime(credentials.run_id, run)
        runtime.start()
        return {
            "ok": True,
            "run_id": credentials.run_id,
            "run_token": credentials.run_token,
            "artifact_dir": str(credentials.artifact_dir),
        }

    def admin_list_runs(self, admin_token: str) -> dict[str, Any]:
        self.registry.verify_admin(admin_token)
        return {"ok": True, "runs": self.registry.list_runs()}

    def admin_stop_run(self, run_id: str, admin_token: str) -> dict[str, Any]:
        self.registry.verify_admin(admin_token)
        with self._lock:
            runtime = self._runtimes.get(run_id)
            if runtime is not None:
                runtime.stop()
        return {"ok": True, "run": self.registry.stop_run(run_id)}

    def admin_rotate_run_token(self, run_id: str, admin_token: str) -> dict[str, Any]:
        self.registry.verify_admin(admin_token)
        return {"ok": True, "run_id": run_id, "run_token": self.registry.rotate_run_token(run_id)}

    def runtime_status(self, run_id: str, run_token: str) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).status()

    def decision_context(self, run_id: str, run_token: str) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).decision_context()

    def submit_decision(
        self,
        run_id: str,
        run_token: str,
        *,
        decision_request_id: str,
        phase_id: str,
        orders: list[Any],
        rationale: str,
        risks: list[Any] | None = None,
        promises_made: list[Any] | None = None,
        promises_received: list[Any] | None = None,
    ) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).submit_decision(
            decision_request_id=decision_request_id,
            phase_id=phase_id,
            orders=orders,
            rationale=rationale,
            risks=risks or [],
            promises_made=promises_made or [],
            promises_received=promises_received or [],
        )

    def send_message(
        self, run_id: str, run_token: str, *, destination: str, body: str
    ) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).send_message(
            destination=destination,
            body=body,
        )

    def record_ledger_note(
        self,
        run_id: str,
        run_token: str,
        *,
        player: str,
        kind: str,
        note: str,
        phase_id: str | None = None,
    ) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).record_ledger_note(
            player=player,
            kind=kind,
            note=note,
            phase_id=phase_id,
        )

    def runtime_events(
        self, run_id: str, run_token: str, *, since_seq: int = 0, limit: int = 50
    ) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).events(since_seq=since_seq, limit=limit)

    def runtime_refresh_current(
        self, run_id: str, run_token: str, *, force: bool = False
    ) -> dict[str, Any]:
        return self._authorized_runtime(run_id, run_token).refresh_current(force=force)

    def runtime_stop(self, run_id: str, run_token: str) -> dict[str, Any]:
        runtime = self._authorized_runtime(run_id, run_token)
        runtime.stop()
        self.registry.stop_run(run_id)
        return {"ok": True, "run_id": run_id, "status": "stopped"}

    def _authorized_runtime(self, run_id: str, run_token: str) -> PlayerRuntime:
        run = self.registry.get_run(run_id, run_token)
        return self._runtime(run_id, run)

    def _runtime(self, run_id: str, run: dict[str, Any]) -> PlayerRuntime:
        with self._lock:
            runtime = self._runtimes.get(run_id)
            if runtime is None:
                runtime = PlayerRuntime(run_id, run, client_factory=self.client_factory)
                self._runtimes[run_id] = runtime
            return runtime


class PlayerRuntime:
    def __init__(
        self,
        run_id: str,
        run: dict[str, Any],
        *,
        client_factory: ClientFactory,
    ) -> None:
        self.run_id = run_id
        self.run = run
        self.artifact_dir = Path(str(run["artifact_dir"]))
        self.store = StateStore(self.artifact_dir / "state.json")
        self.events_path = self.artifact_dir / "runtime_events.jsonl"
        self.lock_path = self.artifact_dir / ".runtime.lock"
        self.client_factory = client_factory
        self._lock = threading.RLock()

    def start(self) -> None:
        with self._lock:
            self._acquire_lock()
            self._append_event(
                "runtime_started",
                {"decision_provider": self.run["decision_provider"]},
            )
            if self.run.get("auto_join", True) and not self.store.state_path.exists():
                self._join()

    def stop(self) -> None:
        with self._lock:
            self._append_event("runtime_stopped", {})
            if self.lock_path.exists():
                self.lock_path.unlink()

    def status(self) -> dict[str, Any]:
        state = self._load_state_or_empty()
        return {
            "ok": True,
            "run_id": self.run_id,
            "artifact_dir": str(self.artifact_dir),
            "status": state.get("status") or self.run.get("status"),
            "game_id": self.run.get("game_id"),
            "profile": self.run.get("profile"),
            "server": self.run.get("server"),
            "player_id": state.get("player_id"),
            "turn": state.get("turn"),
            "phase": state.get("phase"),
            "phase_id": state.get("phase_id"),
            "decision_request_id": _decision_request_id(self.run_id, state.get("phase_id")),
            "processed_messages": len(state.get("processed_message_ids", [])),
        }

    def decision_context(self) -> dict[str, Any]:
        if not self.store.state_path.exists():
            raise RuntimeErrorPayload("missing_state", "run has no state.json yet")
        context = build_phase_context(self.artifact_dir)
        state = self.store.load()
        context["run_id"] = self.run_id
        context["decision_request_id"] = _decision_request_id(self.run_id, state.get("phase_id"))
        return context

    def submit_decision(
        self,
        *,
        decision_request_id: str,
        phase_id: str,
        orders: list[Any],
        rationale: str,
        risks: list[Any],
        promises_made: list[Any],
        promises_received: list[Any],
    ) -> dict[str, Any]:
        with self._lock:
            state = self.store.load()
            expected_request_id = _decision_request_id(self.run_id, state.get("phase_id"))
            if decision_request_id != expected_request_id:
                raise RuntimeErrorPayload(
                    "stale_decision_request",
                    "decision_request_id is not current",
                )
            if state.get("phase_id") != phase_id:
                raise RuntimeErrorPayload("stale_phase", "phase_id is not current")
            append_decision_journal(
                self.artifact_dir,
                phase_id=phase_id,
                rationale=rationale,
                orders=orders,
                risks=risks,
                promises_made=promises_made,
                promises_received=promises_received,
            )
            body = {
                "type": "order_package",
                "game_id": state["game_id"],
                "phase_id": phase_id,
                "orders": orders,
            }
            result = self._reply(state, "order_package", body)
            self._append_event(
                "decision_submitted",
                {"phase_id": phase_id, "decision_request_id": decision_request_id},
            )
            return {
                "ok": True,
                "run_id": self.run_id,
                "phase_id": phase_id,
                "server_ack_status": "pending",
                "result": result,
            }

    def send_message(self, *, destination: str, body: str) -> dict[str, Any]:
        with self._lock:
            state = self.store.load()
            payload = {
                "type": "message",
                "game_id": state["game_id"],
                "destination": destination,
                "body": body,
            }
            result = self._reply(state, "message", payload)
            self._append_event("message_sent", {"destination": destination})
            return {"ok": True, "run_id": self.run_id, "result": result}

    def record_ledger_note(
        self, *, player: str, kind: str, note: str, phase_id: str | None
    ) -> dict[str, Any]:
        record = append_ledger_note(
            self.artifact_dir,
            player=player,
            kind=kind,
            note=note,
            phase_id=phase_id,
        )
        self._append_event("ledger_note_recorded", {"player": player, "kind": kind})
        return {"ok": True, "run_id": self.run_id, "record": record}

    def events(self, *, since_seq: int = 0, limit: int = 50) -> dict[str, Any]:
        rows = _read_jsonl(self.events_path)
        selected = [
            row for row in rows if isinstance(row.get("seq"), int) and row["seq"] > since_seq
        ]
        return {"ok": True, "run_id": self.run_id, "events": selected[:limit]}

    def refresh_current(self, *, force: bool = False) -> dict[str, Any]:
        with self._lock:
            state = self.store.load()
            if not force and self._recent_event("current_requested"):
                return {"ok": False, "error": {"code": "rate_limited"}}
            body = {
                "type": "get_current_phase",
                "game_id": state["game_id"],
                "request_id": f"runtime-current-{_compact_timestamp()}",
            }
            result = self._reply(state, "get_current_phase", body)
            self._append_event("current_requested", {"force": force})
            return {"ok": True, "run_id": self.run_id, "result": result}

    def maybe_submit_fallback(self) -> dict[str, Any]:
        with self._lock:
            fallback = safe_fallback_orders(self.artifact_dir)
            if fallback.get("safe_to_submit") is not True:
                return {"ok": False, "error": {"code": "fallback_not_safe"}}
            state = self.store.load()
            body = {
                "type": "order_package",
                "game_id": state["game_id"],
                "phase_id": fallback["phase_id"],
                "orders": fallback["orders"],
            }
            result = self._reply(state, "order_package", body)
            self._append_event("fallback_submitted", {"phase_id": fallback["phase_id"]})
            return {"ok": True, "run_id": self.run_id, "result": result}

    def _join(self) -> None:
        body = {"type": "join_game", "game_id": self.run["game_id"]}
        result = self._client_call(
            lambda client: client.send(self.run["profile"], self.run["server"], body)
        )
        thread_id = _thread_id_from_send_result(result)
        if thread_id is None:
            raise RuntimeErrorPayload("missing_thread_id", "join result did not include thread_id")
        self.store.append_submitted_command(
            {
                "command_type": "join_game",
                "game_id": self.run["game_id"],
                "recipient": self.run["server"],
                "body": body,
                "result": result,
                "ok": True,
            }
        )
        self.store.initialize_session(
            profile=self.run["profile"],
            server=self.run["server"],
            game_id=self.run["game_id"],
            server_thread_id=thread_id,
            join_result=result,
        )
        self._append_event("joined", {"server_thread_id": thread_id})

    def _reply(
        self, state: dict[str, Any], command_type: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        result = self._client_call(
            lambda client: client.reply(state["profile"], state["server_thread_id"], body)
        )
        self.store.append_submitted_command(
            {
                "command_type": command_type,
                "game_id": body.get("game_id"),
                "thread_id": state.get("server_thread_id"),
                "body": body,
                "result": result,
                "ok": True,
            }
        )
        return result

    def _client_call(self, action: Callable[[ClankmatesClient], dict[str, Any]]) -> dict[str, Any]:
        try:
            return action(self.client_factory())
        except ClankmatesError as exc:
            self._append_event("clankm_failed", exc.to_dict())
            raise RuntimeErrorPayload("clankm_failed", exc.stderr or str(exc)) from exc

    def _acquire_lock(self) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            raise RuntimeErrorPayload(
                "run_locked",
                "artifact_dir already has an active runtime lock",
            )
        self.lock_path.write_text(str(os.getpid()), encoding="utf-8")

    def _append_event(self, event: str, payload: dict[str, Any]) -> None:
        rows = _read_jsonl(self.events_path)
        seq = int(rows[-1]["seq"]) + 1 if rows and isinstance(rows[-1].get("seq"), int) else 1
        record = {
            "seq": seq,
            "local_timestamp": _utc_now(),
            "run_id": self.run_id,
            "event": event,
            "payload": _redact(payload),
        }
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    def _recent_event(self, event: str) -> bool:
        rows = _read_jsonl(self.events_path)
        return any(row.get("event") == event for row in rows[-3:])

    def _load_state_or_empty(self) -> dict[str, Any]:
        try:
            return self.store.load()
        except FileNotFoundError:
            return {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                decoded = json.loads(line)
                if isinstance(decoded, dict):
                    rows.append(decoded)
    return rows


def _decision_request_id(run_id: str, phase_id: Any) -> str | None:
    return f"{run_id}:{phase_id}" if isinstance(phase_id, str) else None


def _thread_id_from_send_result(result: dict[str, Any]) -> str | None:
    for key in ("id", "thread_id", "threadId"):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    data = result.get("data")
    if isinstance(data, dict):
        for key in ("id", "thread_id", "threadId"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if "token" in lowered or "secret" in lowered or "key" in lowered:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted


def _compact_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def to_error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, RuntimeErrorPayload | RegistryError):
        return exc.to_payload()
    return {"ok": False, "error": {"code": "runtime_error", "message": str(exc)}}
