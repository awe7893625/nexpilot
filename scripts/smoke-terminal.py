#!/usr/bin/env python3
"""Smoke test a running NexPilot terminal WebSocket."""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys


async def run(url: str, timeout: float) -> int:
    try:
        import websockets
    except Exception as exc:
        print(f"missing websockets package: {exc}", file=sys.stderr)
        return 2

    marker = f"NEXPILOT_WS_OK_{secrets.token_hex(4)}"
    output = ""
    async with websockets.connect(url, ping_interval=None) as ws:
        await ws.send(json.dumps({"type": "input", "data": f"printf '{marker}\\n'\\n"}))
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
                    await ws.send(json.dumps({"type": "input", "data": "exit\n"}))
                    print(f"NexPilot terminal smoke: PASS ({marker})")
                    return 0
        print("NexPilot terminal smoke: FAIL")
        print(output[-1000:])
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8765/ws/terminal?token=test-token")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    return asyncio.run(run(args.url, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
