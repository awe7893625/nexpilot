"""Local-first NexPilot public trial server."""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .terminal import PtyTerminalSession, PtyUnsupportedError, TerminalConfig

STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    token: str
    shell: str
    cwd: Path


def make_app(config: ServerConfig) -> FastAPI:
    app = FastAPI(title="NexPilot Public Trial", version=__version__)
    app.state.config = config
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
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
        }

    @app.websocket("/ws/terminal")
    async def terminal_ws(websocket: WebSocket):
        if not websocket_token_valid(websocket, config):
            await websocket.close(code=1008, reason="unauthorized")
            return

        await websocket.accept()

        async def send_output(data: str) -> None:
            await websocket.send_json({"type": "output", "data": data})

        try:
            session = PtyTerminalSession(
                TerminalConfig(shell=config.shell, cwd=config.cwd),
                send_output=send_output,
            )
            session.start()
        except PtyUnsupportedError as exc:
            await websocket.send_json({"type": "error", "error": str(exc)})
            await websocket.close(code=1011, reason="unsupported platform")
            return
        except Exception as exc:
            await websocket.send_json({"type": "error", "error": str(exc)})
            await websocket.close(code=1011, reason="session start failed")
            return

        output_task = asyncio.create_task(session.pump_output())
        try:
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")
                if msg_type == "input":
                    session.write(str(message.get("data") or ""))
                elif msg_type == "resize":
                    session.resize(int(message.get("cols") or 100), int(message.get("rows") or 32))
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await websocket.send_json({"type": "error", "error": f"unsupported message: {msg_type}"})
        except WebSocketDisconnect:
            pass
        finally:
            output_task.cancel()
            await session.close()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"ok": False, "error": exc.detail}, status_code=exc.status_code)

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


def _default_shell() -> str:
    if os.name == "nt":
        return os.environ.get("COMSPEC", "powershell.exe")
    return os.environ.get("SHELL", "/bin/zsh" if Path("/bin/zsh").exists() else "/bin/sh")


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
    return ServerConfig(host=host, port=port, token=token, shell=shell, cwd=cwd)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the NexPilot local trial agent.")
    parser.add_argument("--host", help="Bind host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, help="Bind port. Default: 8765")
    parser.add_argument("--lan", action="store_true", help="Bind 0.0.0.0 for same-LAN phone access.")
    parser.add_argument("--token", help="Access token. Default: generated at startup.")
    parser.add_argument("--shell", help="Shell command. Default: current user shell.")
    parser.add_argument("--cwd", help="Initial working directory. Default: home directory.")
    return parser.parse_args(argv)


def print_startup(config: ServerConfig) -> None:
    display_host = "127.0.0.1" if config.host in {"0.0.0.0", "::"} else config.host
    local_url = f"http://{display_host}:{config.port}/?token={config.token}"
    print("")
    print("NexPilot public trial agent")
    print(f"  Version: {__version__}")
    print(f"  Bind:    {config.host}:{config.port}")
    print(f"  Shell:   {config.shell}")
    print(f"  CWD:     {config.cwd}")
    print("")
    print(f"Open: {local_url}")
    if config.host == "0.0.0.0":
        print(f"Phone on same Wi-Fi: http://{_lan_ip()}:{config.port}/?token={config.token}")
    print("")
    print("Keep this URL private. Stop this process to revoke access.")
    print("")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = build_config(args)
    app = make_app(config)
    print_startup(config)
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()
