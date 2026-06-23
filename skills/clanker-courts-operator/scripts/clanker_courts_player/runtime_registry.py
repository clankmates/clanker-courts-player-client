from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .runtime_auth import new_token, read_secret_file, token_hash, verify_token, write_secret_file


@dataclass(frozen=True)
class RunCredentials:
    run_id: str
    run_token: str
    artifact_dir: Path


class RegistryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_payload(self) -> dict[str, Any]:
        return {"ok": False, "error": {"code": self.code, "message": self.message}}


class RunRegistry:
    def __init__(self, runs_root: str | Path) -> None:
        self.runs_root = Path(runs_root)
        self.registry_path = self.runs_root / "registry.json"
        self.admin_token_path = self.runs_root / "admin.token"

    def ensure_admin_token(self) -> str:
        if self.admin_token_path.exists():
            return read_secret_file(self.admin_token_path)
        token = new_token()
        write_secret_file(self.admin_token_path, token)
        return token

    def verify_admin(self, admin_token: str) -> None:
        expected = self.ensure_admin_token()
        if not verify_token(admin_token, token_hash(expected, salt="admin-token-check")):
            raise RegistryError("unauthorized", "invalid admin token")

    def create_run(
        self,
        *,
        profile: str,
        server: str,
        game_id: str,
        artifact_dir: str | Path | None = None,
        label: str | None = None,
        decision_provider: str = "harness",
        fallback_margin_seconds: int = 15,
        auto_join: bool = True,
        auto_ready: bool = True,
    ) -> RunCredentials:
        self.ensure_admin_token()
        payload = self._load()
        run_id = _run_id(game_id, profile, payload["runs"])
        path = Path(artifact_dir) if artifact_dir is not None else self._default_artifact_dir(
            game_id=game_id, profile=profile, run_id=run_id
        )
        resolved_path = str(path.resolve())

        for existing in payload["runs"].values():
            if existing.get("artifact_dir") == resolved_path and existing.get("status") == "active":
                raise RegistryError(
                    "duplicate_artifact_dir",
                    "an active run already uses artifact_dir",
                )
            if (
                existing.get("profile") == profile
                and existing.get("server") == server
                and existing.get("game_id") == game_id
                and existing.get("status") == "active"
            ):
                raise RegistryError("duplicate_player_run", "an active run already exists")

        run_token = new_token()
        payload["runs"][run_id] = {
            "run_id": run_id,
            "label": label,
            "profile": profile,
            "server": server,
            "game_id": game_id,
            "artifact_dir": resolved_path,
            "token_hash": token_hash(run_token),
            "decision_provider": decision_provider,
            "fallback_margin_seconds": fallback_margin_seconds,
            "auto_join": auto_join,
            "auto_ready": auto_ready,
            "status": "active",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        self._save(payload)
        return RunCredentials(run_id=run_id, run_token=run_token, artifact_dir=Path(resolved_path))

    def get_run(self, run_id: str, run_token: str | None = None) -> dict[str, Any]:
        payload = self._load()
        run = payload["runs"].get(run_id)
        if not isinstance(run, dict):
            raise RegistryError("unknown_run", "run_id was not found")
        if run_token is not None and not verify_token(run_token, str(run.get("token_hash", ""))):
            raise RegistryError("unauthorized", "invalid run token")
        return dict(run)

    def list_runs(self) -> list[dict[str, Any]]:
        payload = self._load()
        return [_public_run(run) for run in payload["runs"].values() if isinstance(run, dict)]

    def stop_run(self, run_id: str) -> dict[str, Any]:
        payload = self._load()
        run = payload["runs"].get(run_id)
        if not isinstance(run, dict):
            raise RegistryError("unknown_run", "run_id was not found")
        run["status"] = "stopped"
        run["updated_at"] = _utc_now()
        self._save(payload)
        return _public_run(run)

    def rotate_run_token(self, run_id: str) -> str:
        payload = self._load()
        run = payload["runs"].get(run_id)
        if not isinstance(run, dict):
            raise RegistryError("unknown_run", "run_id was not found")
        token = new_token()
        run["token_hash"] = token_hash(token)
        run["updated_at"] = _utc_now()
        self._save(payload)
        return token

    def _default_artifact_dir(self, *, game_id: str, profile: str, run_id: str) -> Path:
        return self.runs_root / "artifacts" / _safe(game_id) / _safe(profile) / run_id

    def _load(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"schema_version": 1, "runs": {}}
        with self.registry_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or not isinstance(payload.get("runs"), dict):
            raise RegistryError("invalid_registry", "registry.json is malformed")
        return payload

    def _save(self, payload: dict[str, Any]) -> None:
        self.runs_root.mkdir(parents=True, exist_ok=True)
        tmp_path = self.registry_path.with_name(".registry.json.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, self.registry_path)


def _public_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in run.items()
        if key not in {"token_hash"} and not key.endswith("_token")
    }


def _run_id(game_id: str, profile: str, runs: dict[str, Any]) -> str:
    prefix = f"{_safe(game_id)}-{_safe(profile)}"
    candidate = prefix
    counter = 2
    while candidate in runs:
        candidate = f"{prefix}-{counter}"
        counter += 1
    return candidate


def _safe(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in safe.split("-") if part) or "run"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
