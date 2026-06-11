# NexPilot

NexPilot is a phone-first terminal cockpit. Run a small agent on your computer,
open the printed URL on your phone, and control a local shell from the mobile
browser. It is local-first, open source, and free to use.

## Screenshots

| Desktop | Mobile |
|---|---|
| <img src="docs/images/desktop.png" alt="NexPilot desktop cockpit" width="100%"> | <img src="docs/images/mobile.png" alt="NexPilot mobile cockpit" width="260"> |

The same cockpit adapts from a wide desktop terminal to a phone-sized viewport, with
reconnect, output replay, heartbeat, and copy/paste/clear controls built in.

## Why It's Safe

NexPilot is intentionally local-first:

- No proprietary backend, cloud account, or sign-up is required.
- No token, database, device ID, or relay server is bundled.
- The agent runs entirely on your own computer.
- Remote use should go through a private network such as Tailscale, not the open
  public internet.

## Features

- Phone-first responsive cockpit UI (desktop and mobile).
- Terminal reconnect with recent-output replay and heartbeat.
- Input/output batching and large-paste chunking for smooth typing.
- Copy / paste / clear controls.
- Token-gated terminal access.
- macOS and Linux via POSIX PTY; Windows via ConPTY (optional `pywinpty`).

## Quick Start

```bash
git clone https://github.com/awe7893625/nexpilot.git
cd nexpilot
bash scripts/install.sh
bash scripts/run-lan.sh
```

Manual install:

```bash
git clone https://github.com/awe7893625/nexpilot.git
cd nexpilot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
nexpilot --lan
```

Open the printed URL on your phone. Keep the token private — anyone with that URL
can control the shell while the agent is running.

Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
.\.venv\Scripts\nexpilot.exe --lan
```

## Safer First Run

For first-time use on the same computer:

```bash
nexpilot
```

This binds to `127.0.0.1` only. For phone use on the same Wi-Fi, run
`nexpilot --lan`.

## Security Basics

- The access token is generated at startup unless `--token` is provided.
- The token is required for terminal WebSocket access and API calls.
- The terminal runs as your current OS user. Do not run as `root`.
- Do not expose this directly to the public internet.
- Prefer Tailscale, WireGuard, or another private network for remote use.
- Stop the process to revoke access immediately.

Read [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) for the full security model.

## Docs

- [Install guide](docs/INSTALL.md)
- [Quick start](docs/QUICKSTART.md)
- [Windows](docs/WINDOWS.md)
- [Uninstall](docs/UNINSTALL.md)
- [Security model](docs/SECURITY_MODEL.md)

## Development Checks

```bash
python3 -m compileall src tests
python3 scripts/secret-scan.py .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest
```

With a local server running on `127.0.0.1:8765` and token `test-token`:

```bash
python3 scripts/smoke-terminal.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'
```

## License

MIT — see [LICENSE](LICENSE). Free to use, modify, and share.
