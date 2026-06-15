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

    def watch_messages(
        self,
        profile: str,
        thread_id: str,
        *,
        once: bool = True,
    ) -> list[dict[str, Any]]:
        return list(self.iter_watch_messages(profile, thread_id, once=once))

    def iter_watch_messages(
        self,
        profile: str,
        thread_id: str,
        *,
        once: bool = False,
    ) -> Iterator[dict[str, Any]]:
        command = [
            self.clankm_path,
            "--profile",
            profile,
            "inbox",
            "watch",
            "messages",
            thread_id,
        ]
        if once:
            command.append("--once")
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
