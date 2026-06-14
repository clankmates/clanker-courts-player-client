from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterator
from typing import Any

Runner = Callable[..., subprocess.CompletedProcess[str]]
PopenRunner = Callable[..., subprocess.Popen[str]]


class ClankmatesError(RuntimeError):
    def __init__(
        self,
        *,
        command: list[str],
        returncode: int | None,
        stdout: str,
        stderr: str,
        decode_error: str | None = None,
        timeout: float | None = None,
    ) -> None:
        super().__init__(decode_error or stderr or f"clankm exited {returncode}")
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.decode_error = decode_error
        self.timeout = timeout

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": False,
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
        if self.decode_error is not None:
            payload["decode_error"] = self.decode_error
        if self.timeout is not None:
            payload["timeout"] = self.timeout
        return payload


class ClankmatesClient:
    def __init__(
        self,
        *,
        clankm_path: str = "clankm",
        runner: Runner | None = None,
        popen_runner: PopenRunner | None = None,
        timeout: float = 30,
    ) -> None:
        self.clankm_path = clankm_path
        self.runner = runner or subprocess.run
        self.popen_runner = popen_runner or subprocess.Popen
        self.timeout = timeout

    def whoami(self, profile: str) -> dict[str, Any]:
        return self._run_json(["--profile", profile, "auth", "whoami", "--json"])

    def list_threads(
        self,
        profile: str,
        status: str = "all",
        *,
        mailbox: str | None = None,
        participant: str | None = None,
        participant_scope: str | None = None,
        query: str | None = None,
        since: str | None = None,
        since_cache: bool = False,
        before: str | None = None,
        save_cache: bool = False,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        argv = ["--profile", profile, "inbox", "list", "--status", status]
        if mailbox is not None:
            argv.extend(["--mailbox", mailbox])
        if participant is not None:
            argv.extend(["--participant", participant])
        if participant_scope is not None:
            argv.extend(["--participant-scope", participant_scope])
        if query is not None:
            argv.extend(["--query", query])
        if since is not None:
            argv.extend(["--since", since])
        if since_cache:
            argv.append("--since-cache")
        if before is not None:
            argv.extend(["--before", before])
        if save_cache:
            argv.append("--save-cache")
        if limit is not None:
            argv.extend(["--limit", str(limit)])
        if cursor is not None:
            argv.extend(["--cursor", cursor])
        argv.append("--json")
        return self._run_json(argv)

    def show_thread(
        self, profile: str, thread_id: str, *, limit: int = 10, cursor: str | None = None
    ) -> dict[str, Any]:
        argv = ["--profile", profile, "inbox", "show", thread_id, "--limit", str(limit)]
        if cursor is not None:
            argv.extend(["--cursor", cursor])
        argv.append("--json")
        return self._run_json(argv)

    def message_changes(
        self,
        profile: str,
        thread_id: str,
        *,
        since: str | None = None,
        since_cache: bool = False,
        save_cache: bool = False,
        query: str | None = None,
        has_attachment: bool = False,
    ) -> dict[str, Any]:
        argv = ["--profile", profile, "inbox", "messages", "changes", thread_id]
        if since is not None:
            argv.extend(["--since", since])
        if since_cache:
            argv.append("--since-cache")
        if save_cache:
            argv.append("--save-cache")
        if query is not None:
            argv.extend(["--query", query])
        if has_attachment:
            argv.append("--has-attachment")
        argv.append("--json")
        return self._run_json(argv)

    def watch_messages(
        self,
        profile: str,
        thread_id: str,
        *,
        once: bool = True,
        since: str | None = None,
        since_cache: bool = False,
        query: str | None = None,
        before: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return list(
            self.iter_watch_messages(
                profile,
                thread_id,
                once=once,
                since=since,
                since_cache=since_cache,
                query=query,
                before=before,
                limit=limit,
            )
        )

    def iter_watch_messages(
        self,
        profile: str,
        thread_id: str,
        *,
        once: bool = False,
        since: str | None = None,
        since_cache: bool = False,
        query: str | None = None,
        before: str | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        command = [
            self.clankm_path,
            *self._watch_messages_args(
                profile,
                thread_id,
                once=once,
                since=since,
                since_cache=since_cache,
                query=query,
                before=before,
                limit=limit,
            ),
        ]
        try:
            process = self.popen_runner(
                command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ClankmatesError(
                command=command,
                returncode=None,
                stdout="",
                stderr=str(exc),
            ) from exc
        stdout = process.stdout
        if stdout is None:
            raise ClankmatesError(
                command=command,
                returncode=None,
                stdout="",
                stderr="watch process did not expose stdout",
            )
        captured_stdout: list[str] = []
        for line_number, line in enumerate(stdout, start=1):
            captured_stdout.append(line)
            if line.strip() == "":
                continue
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ClankmatesError(
                    command=command,
                    returncode=None,
                    stdout="".join(captured_stdout),
                    stderr=_stop_and_read_stderr(process),
                    decode_error=f"line {line_number}: {exc}",
                ) from exc
            if not isinstance(decoded, dict):
                raise ClankmatesError(
                    command=command,
                    returncode=None,
                    stdout="".join(captured_stdout),
                    stderr=_stop_and_read_stderr(process),
                    decode_error=f"line {line_number}: expected JSON object",
                )
            yield decoded
        returncode = process.wait()
        if returncode != 0:
            raise ClankmatesError(
                command=command,
                returncode=returncode,
                stdout="".join(captured_stdout),
                stderr=_read_pipe(process.stderr),
            )

    def archive_thread(self, profile: str, thread_id: str) -> dict[str, Any]:
        return self._run_json(["--profile", profile, "inbox", "archive", thread_id, "--json"])

    def send(self, profile: str, recipient: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._run_json(
            [
                "--profile",
                profile,
                "inbox",
                "send",
                recipient,
                "--payload",
                _json_body(body),
                "--json",
            ]
        )

    def reply(self, profile: str, thread_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._run_json(
            [
                "--profile",
                profile,
                "inbox",
                "reply",
                thread_id,
                "--payload",
                _json_body(body),
                "--json",
            ]
        )

    def _run_json(self, args: list[str]) -> dict[str, Any]:
        command = [self.clankm_path, *args]
        completed = self._run(command)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if completed.returncode != 0:
            raise ClankmatesError(
                command=command,
                returncode=completed.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        try:
            decoded = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ClankmatesError(
                command=command,
                returncode=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                decode_error=str(exc),
            ) from exc
        if not isinstance(decoded, dict):
            raise ClankmatesError(
                command=command,
                returncode=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                decode_error="expected JSON object",
            )
        return decoded

    def _run_jsonl(self, args: list[str]) -> list[dict[str, Any]]:
        command = [self.clankm_path, *args]
        completed = self._run(command)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if completed.returncode != 0:
            raise ClankmatesError(
                command=command,
                returncode=completed.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(stdout.splitlines(), start=1):
            if line.strip() == "":
                continue
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ClankmatesError(
                    command=command,
                    returncode=completed.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    decode_error=f"line {line_number}: {exc}",
                ) from exc
            if not isinstance(decoded, dict):
                raise ClankmatesError(
                    command=command,
                    returncode=completed.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    decode_error=f"line {line_number}: expected JSON object",
                )
            records.append(decoded)
        return records

    def _watch_messages_args(
        self,
        profile: str,
        thread_id: str,
        *,
        once: bool,
        since: str | None,
        since_cache: bool,
        query: str | None,
        before: str | None,
        limit: int | None,
    ) -> list[str]:
        argv = ["--profile", profile, "inbox", "watch", "messages", thread_id]
        if once:
            argv.append("--once")
        if since is not None:
            argv.extend(["--since", since])
        if since_cache:
            argv.append("--since-cache")
        if query is not None:
            argv.extend(["--query", query])
        if before is not None:
            argv.extend(["--before", before])
        if limit is not None:
            argv.extend(["--limit", str(limit)])
        return argv

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(
                command,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ClankmatesError(
                command=command,
                returncode=None,
                stdout="",
                stderr=str(exc),
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ClankmatesError(
                command=command,
                returncode=None,
                stdout=_coerce_text(exc.output),
                stderr=_coerce_text(exc.stderr),
                timeout=exc.timeout,
            ) from exc


def _json_body(body: dict[str, Any]) -> str:
    return json.dumps(body, separators=(",", ":"), sort_keys=True)


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _read_pipe(pipe: Any) -> str:
    if pipe is None:
        return ""
    value = pipe.read()
    return _coerce_text(value)


def _stop_and_read_stderr(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return _read_pipe(process.stderr)
