from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .runtime_manager import RunManager, to_error_payload

TOOL_NAMES = [
    "admin_create_run",
    "admin_list_runs",
    "admin_stop_run",
    "admin_rotate_run_token",
    "runtime_status",
    "decision_context",
    "submit_decision",
    "send_message",
    "record_ledger_note",
    "runtime_events",
    "runtime_refresh_current",
    "runtime_stop",
]


def serve(host: str, port: int, runs_root: Path) -> None:
    manager = RunManager(runs_root)
    admin_token = manager.registry.ensure_admin_token()
    print(
        json.dumps(
            {
                "ok": True,
                "event": "server_started",
                "host": host,
                "port": port,
                "runs_root": str(runs_root),
                "admin_token_file": str(manager.registry.admin_token_path),
            },
            sort_keys=True,
        )
    )
    del admin_token

    class Handler(_Handler):
        run_manager = manager

    ThreadingHTTPServer((host, port), Handler).serve_forever()


class _Handler(BaseHTTPRequestHandler):
    run_manager: RunManager

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self._send_json({"ok": True, "service": "clanker-courts-mcp-server"})

    def do_POST(self) -> None:
        if self.path != "/mcp":
            self.send_error(404)
            return
        try:
            payload = self._read_json()
            response = self._handle_rpc(payload)
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            response = _rpc_error(None, -32603, str(exc))
        self._send_json(response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_rpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") if isinstance(payload.get("params"), dict) else {}

        if method == "initialize":
            return _rpc_result(
                request_id,
                {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "clanker-courts-mcp-server", "version": "0.1.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            )
        if method == "tools/list":
            return _rpc_result(
                request_id,
                {
                    "tools": [
                        {"name": name, "description": _tool_description(name)}
                        for name in TOOL_NAMES
                    ]
                },
            )
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            if not isinstance(name, str) or name not in TOOL_NAMES:
                return _rpc_error(request_id, -32602, "unknown tool")
            result = self._call_tool(name, arguments)
            return _rpc_result(
                request_id,
                {"content": [{"type": "text", "text": json.dumps(result)}]},
            )
        return _rpc_error(request_id, -32601, "method not found")

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            method = getattr(self.run_manager, name)
            return method(**arguments)
        except Exception as exc:
            return to_error_payload(exc)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode())
        if not isinstance(payload, dict):
            raise ValueError("request must be a JSON object")
        return payload

    def _send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _tool_description(name: str) -> str:
    return name.replace("_", " ")


def _rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clanker-courts-mcp-server")
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    serve_parser = subparsers.add_parser("serve", help="serve the shared local MCP endpoint")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--runs-root", default=".runs/mcp")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "serve":
        parser.print_help()
        return 0
    serve(args.host, args.port, Path(args.runs_root))
    return 0
