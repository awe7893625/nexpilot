"""Local-first NexPilot server."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import secrets
import socket
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .terminal import PtyUnsupportedError, TerminalConfig, create_terminal_session

STATIC_DIR = Path(__file__).resolve().parent / "static"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    token: str
    shell: str
    cwd: Path
    idle_timeout: int = 900
    history_limit: int = 200_000


class ManagedTerminalSession:
    """Keeps one shell alive across browser reconnects."""

    def __init__(self, session_id: str, config: ServerConfig):
        self.session_id = session_id
        self.config = config
        self.terminal = create_terminal_session(
            TerminalConfig(shell=config.shell, cwd=config.cwd),
            send_output=self._handle_output,
        )
        self.started_at = time.time()
        self.last_seen_at = self.started_at
        self.history: deque[str] = deque()
        self.history_chars = 0
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self.pump_task: asyncio.Task | None = None
        self.idle_task: asyncio.Task | None = None
        self.closed = False

    def start(self) -> None:
        self.terminal.start()
        self.pump_task = asyncio.create_task(self._pump())

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        self.last_seen_at = time.time()
        if self.idle_task is not None:
            self.idle_task.cancel()
            self.idle_task = None
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.subscribers.discard(queue)
        self.last_seen_at = time.time()
        if not self.subscribers and not self.closed and self.idle_task is None:
            self.idle_task = asyncio.create_task(self._close_after_idle())

    async def _close_after_idle(self) -> None:
        try:
            await asyncio.sleep(max(10, self.config.idle_timeout))
            if not self.subscribers:
                await self.close("idle timeout")
        except asyncio.CancelledError:
            return

    async def _pump(self) -> None:
        try:
            await self.terminal.pump_output()
        except Exception as exc:
            await self._broadcast(
                {"type": "error", "error": f"terminal output failed: {exc}"}
            )
        finally:
            self.closed = True
            await self._broadcast({"type": "exit", "reason": "terminal exited"})

    async def _handle_output(self, data: str) -> None:
        if not data:
            return
        self.history.append(data)
        self.history_chars += len(data)
        while self.history_chars > self.config.history_limit and self.history:
            self.history_chars -= len(self.history.popleft())
        await self._broadcast({"type": "output", "data": data})

    async def _broadcast(self, message: dict[str, Any]) -> None:
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    pass

    def write(self, data: str) -> None:
        self.last_seen_at = time.time()
        self.terminal.write(data)

    def resize(self, cols: int, rows: int) -> None:
        self.last_seen_at = time.time()
        self.terminal.resize(cols, rows)

    async def close(self, reason: str = "closed") -> None:
        if self.closed:
            return
        self.closed = True
        if self.idle_task is not None:
            self.idle_task.cancel()
            self.idle_task = None
        if self.pump_task is not None:
            self.pump_task.cancel()
        await self.terminal.close()
        await self._broadcast({"type": "exit", "reason": reason})


def make_app(config: ServerConfig) -> FastAPI:
    app = FastAPI(title="NexPilot", version=__version__)
    app.state.config = config
    app.state.sessions = {}
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        # A04: anti-clickjacking headers
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
        return response

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/manifest.webmanifest")
    async def manifest() -> FileResponse:
        return FileResponse(STATIC_DIR / "manifest.webmanifest")

    @app.get("/api/status")
    async def status(request: Request) -> dict[str, Any]:
        require_token(request, config)
        return {
            "ok": True,
            "version": __version__,
            "platform": os.name,
            "cwd": str(config.cwd),
            "shell": config.shell,
            "host": config.host,
            "port": config.port,
            "terminal": {
                "session_reconnect": True,
                "idle_timeout": config.idle_timeout,
                "history_limit": config.history_limit,
                "windows_conpty": os.name == "nt",
            },
        }

    @app.websocket("/ws/terminal")
    async def terminal_ws(websocket: WebSocket):
        # A03: reject disallowed origins before any token check
        if not websocket_origin_allowed(websocket, config):
            await websocket.close(code=1008, reason="forbidden origin")
            return
        if not websocket_token_valid(websocket, config):
            await websocket.close(code=1008, reason="unauthorized")
            return

        await websocket.accept()

        try:
            session_id = _clean_session_id(websocket.query_params.get("session"))
            sessions: dict[str, ManagedTerminalSession] = app.state.sessions
            reconnected = session_id in sessions and not sessions[session_id].closed
            if reconnected:
                session = sessions[session_id]
            else:
                session = ManagedTerminalSession(session_id, config)
                session.start()
                sessions[session_id] = session
        except PtyUnsupportedError as exc:
            await websocket.send_json({"type": "error", "error": str(exc)})
            await websocket.close(code=1011, reason="unsupported platform")
            return
        except Exception as exc:
            await websocket.send_json({"type": "error", "error": str(exc)})
            await websocket.close(code=1011, reason="session start failed")
            return

        queue = session.subscribe()
        await websocket.send_json(
            {
                "type": "session",
                "session": session.session_id,
                "reconnected": reconnected,
                "idle_timeout": config.idle_timeout,
            }
        )
        if session.history:
            await websocket.send_json(
                {"type": "output", "data": "".join(session.history), "replay": True}
            )

        async def sender() -> None:
            while True:
                message = await queue.get()
                await websocket.send_json(message)
                if message.get("type") == "exit":
                    return

        sender_task = asyncio.create_task(sender())
        try:
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")
                if msg_type == "input":
                    # A09: cap a single input message to prevent paste-bomb DoS
                    data = str(message.get("data") or "")[:65536]
                    session.write(data)
                    await websocket.send_json({"type": "ack", "id": message.get("id")})
                elif msg_type == "resize":
                    # A06: safe-int conversion with defaults — non-numeric values won't crash
                    session.resize(
                        _safe_int(message.get("cols"), 100),
                        _safe_int(message.get("rows"), 32),
                    )
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "close_session":
                    await session.close("client closed session")
                    break
                else:
                    await websocket.send_json(
                        {"type": "error", "error": f"unsupported message: {msg_type}"}
                    )
        except WebSocketDisconnect:
            pass
        finally:
            sender_task.cancel()
            session.unsubscribe(queue)
            await _prune_closed_sessions(app.state.sessions)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {"ok": False, "error": exc.detail}, status_code=exc.status_code
        )

    return app


def require_token(request: Request, config: ServerConfig) -> None:
    provided = request.headers.get("x-nexpilot-token") or ""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    if not provided:
        provided = request.query_params.get("token", "")
    if not secrets.compare_digest(provided, config.token):
        raise HTTPException(status_code=401, detail="invalid or missing token")


def websocket_token_valid(websocket: WebSocket, config: ServerConfig) -> bool:
    provided = websocket.headers.get("x-nexpilot-token") or ""
    auth = websocket.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    if not provided:
        provided = websocket.query_params.get("token", "")
    return bool(provided and secrets.compare_digest(provided, config.token))


def _allowed_origins(config: ServerConfig) -> set[str]:
    """Return the set of origins that are permitted to open a WebSocket.

    A03: limit origins to localhost / 127.0.0.1 and, only when the server is
    bound to 0.0.0.0, also the actual LAN IP.  Unknown/null origins are blocked.
    """
    port = config.port
    allowed = {
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    }
    if config.host == "0.0.0.0":
        lan = _lan_ip()
        if lan != "127.0.0.1":
            allowed.add(f"http://{lan}:{port}")
    return allowed


def websocket_origin_allowed(websocket: WebSocket, config: ServerConfig) -> bool:
    """A03: reject WebSocket connections from unlisted origins."""
    origin = websocket.headers.get("origin") or ""
    if not origin:
        # No Origin header — only allow when bound to loopback
        return config.host not in {"0.0.0.0", "::"}
    return origin in _allowed_origins(config)


def _safe_int(value: Any, default: int) -> int:
    """A06: convert *value* to int safely; return *default* on any failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_session_id(raw: str | None) -> str:
    if raw and SESSION_ID_PATTERN.fullmatch(raw):
        return raw
    return secrets.token_urlsafe(12)


async def _prune_closed_sessions(sessions: dict[str, ManagedTerminalSession]) -> None:
    for session_id, session in list(sessions.items()):
        if session.closed and not session.subscribers:
            sessions.pop(session_id, None)


def _default_shell() -> str:
    if os.name == "nt":
        return os.environ.get("COMSPEC", "powershell.exe")
    return os.environ.get(
        "SHELL", "/bin/zsh" if Path("/bin/zsh").exists() else "/bin/sh"
    )


def _lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def build_config(args: argparse.Namespace) -> ServerConfig:
    host = args.host or os.environ.get("NEXPILOT_HOST") or "127.0.0.1"
    if args.lan:
        host = "0.0.0.0"
    port = int(args.port or os.environ.get("NEXPILOT_PORT") or 8765)
    token = args.token or os.environ.get("NEXPILOT_TOKEN") or secrets.token_urlsafe(24)
    shell = args.shell or os.environ.get("NEXPILOT_SHELL") or _default_shell()
    cwd = Path(args.cwd or os.environ.get("NEXPILOT_CWD") or Path.home()).expanduser()
    idle_timeout = int(
        args.idle_timeout or os.environ.get("NEXPILOT_IDLE_TIMEOUT") or 900
    )
    history_limit = int(
        args.history_limit or os.environ.get("NEXPILOT_HISTORY_LIMIT") or 200_000
    )
    return ServerConfig(
        host=host,
        port=port,
        token=token,
        shell=shell,
        cwd=cwd,
        idle_timeout=idle_timeout,
        history_limit=history_limit,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the NexPilot local trial agent.")
    parser.add_argument("--host", help="Bind host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, help="Bind port. Default: 8765")
    parser.add_argument(
        "--lan", action="store_true", help="Bind 0.0.0.0 for same-LAN phone access."
    )
    parser.add_argument("--token", help="Access token. Default: generated at startup.")
    parser.add_argument("--shell", help="Shell command. Default: current user shell.")
    parser.add_argument(
        "--cwd", help="Initial working directory. Default: home directory."
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        help="Seconds to keep detached shells alive. Default: 900.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        help="Per-session replay history characters. Default: 200000.",
    )
    return parser.parse_args(argv)


def print_startup(config: ServerConfig) -> None:
    display_host = "127.0.0.1" if config.host in {"0.0.0.0", "::"} else config.host
    local_url = f"http://{display_host}:{config.port}/?token={config.token}"
    print("")
    print("NexPilot agent")
    print(f"  Version: {__version__}")
    print(f"  Bind:    {config.host}:{config.port}")
    print(f"  Shell:   {config.shell}")
    print(f"  CWD:     {config.cwd}")
    print(f"  Detach:  {config.idle_timeout}s reconnect window")
    print("")
    print(f"Open: {local_url}")
    if config.host == "0.0.0.0":
        print(
            f"Phone on same Wi-Fi: http://{_lan_ip()}:{config.port}/?token={config.token}"
        )
        print("")
        # A10: warn the user that --lan exposes the shell on all interfaces over plain HTTP
        print("WARNING: --lan mode exposes this shell on ALL network interfaces.")
        print("         The token travels in plaintext over HTTP.")
        print("         Use Tailscale or a trusted private network only.")
    print("")
    print("Keep this URL private. Stop this process to revoke access.")
    print("")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = build_config(args)
    app = make_app(config)
    print_startup(config)
    # A02: disable access logs so ?token=SECRET is never written to disk.
    # log_level="warning" keeps error/warning output for diagnostics.
    uvicorn.run(
        app, host=config.host, port=config.port, log_level="warning", access_log=False
    )


if __name__ == "__main__":
    main()
