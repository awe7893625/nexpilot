#!/usr/bin/env python3
"""Smoke test NexPilot terminal reconnect preserving the shell process."""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def with_session(url: str, session_id: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["session"] = session_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


async def wait_for_marker(ws, marker: str, timeout: float) -> bool:
    output = ""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        remaining = max(0.1, deadline - asyncio.get_running_loop().time())
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        message = json.loads(raw)
        if message.get("type") == "output":
            output += str(message.get("data") or "")
            if marker in output:
                return True
    print(output[-1000:])
    return False


async def run(url: str, timeout: float) -> int:
    try:
        import websockets
    except Exception as exc:
        print(f"missing websockets package: {exc}", file=sys.stderr)
        return 2

    marker = f"NEXPILOT_RECONNECT_OK_{secrets.token_hex(4)}"
    session_id = f"smoke-{secrets.token_hex(6)}"
    session_url = with_session(url, session_id)

    async with websockets.connect(session_url, ping_interval=None) as ws:
        command = f"NEXPILOT_RECONNECT_MARKER='{marker}'; export NEXPILOT_RECONNECT_MARKER; printf \"$NEXPILOT_RECONNECT_MARKER\\n\"\n"
        await ws.send(json.dumps({"type": "input", "data": command}))
        if not await wait_for_marker(ws, marker, timeout):
            print("NexPilot reconnect smoke: FAIL before reconnect")
            return 1

    await asyncio.sleep(0.2)

    async with websockets.connect(session_url, ping_interval=None) as ws:
        await ws.send(json.dumps({"type": "input", "data": 'printf "$NEXPILOT_RECONNECT_MARKER\\n"\n'}))
        if await wait_for_marker(ws, marker, timeout):
            await ws.send(json.dumps({"type": "input", "data": "exit\n"}))
            print(f"NexPilot reconnect smoke: PASS ({marker})")
            return 0

    print("NexPilot reconnect smoke: FAIL after reconnect")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8765/ws/terminal?token=test-token")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    return asyncio.run(run(args.url, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
