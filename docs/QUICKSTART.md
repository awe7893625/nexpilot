# Quick Start

## 1. Install

```bash
git clone https://github.com/awe7893625/nexpilot.git
cd nexpilot
bash scripts/install.sh
```

Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
```

## 2. Run

For same-computer use:

```bash
bash scripts/run-local.sh
```

For phone use on the same Wi-Fi or Tailscale:

```bash
bash scripts/run-lan.sh
```

## 3. Open On Phone

Use the printed phone URL. Keep it private because it contains the access token.

## 4. Stop

Press `Ctrl-C` in the terminal running NexPilot. This immediately revokes access.

## 5. Safety Rules

- Do not run as `root` or administrator.
- Do not expose the port to the public internet.
- Prefer Tailscale for remote use.
- Close the process when finished.
