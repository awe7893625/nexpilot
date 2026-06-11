# Install Guide

## Requirements

- macOS, Linux, or Windows
- Python 3.9+
- A phone on the same Wi-Fi, or a private network path such as Tailscale

## Install From Source

```bash
git clone https://github.com/awe7893625/nexpilot.git
cd nexpilot
bash scripts/install.sh
```

## Manual Install From Source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Windows

PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
.\.venv\Scripts\nexpilot.exe --lan
```

Windows terminal support uses ConPTY through optional `pywinpty`.

## Run For Same-Computer Testing

```bash
nexpilot
```

Open the printed localhost URL in the computer browser.

## Run For Phone On Same Wi-Fi

```bash
nexpilot --lan
```

Open the printed phone URL on the phone browser.

## Run Over Tailscale

1. Install Tailscale on the computer and phone.
2. Sign both devices into the same tailnet.
3. Run:

```bash
nexpilot --lan
```

4. Open `http://TAILSCALE_IP:8765/?token=...` on the phone.

Do not publish this port directly to the public internet.
