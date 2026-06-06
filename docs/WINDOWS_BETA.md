# Windows Private Beta

Windows support is now a private beta path. It uses ConPTY through `pywinpty`.

## Install

Run PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
```

Then run:

```powershell
.\.venv\Scripts\nexpilot.exe
```

For phone testing on the same Wi-Fi:

```powershell
.\.venv\Scripts\nexpilot.exe --lan
```

## Scope

Included:

- PowerShell or `cmd.exe` through Windows ConPTY.
- Same token gate as macOS/Linux.
- Same reconnect window and terminal history replay.
- Same Wi-Fi/LAN or tester-owned Tailscale access.

Not included yet:

- Signed MSI installer.
- Windows service install.
- Auto-start on login.
- Public cloud relay.

## Safety

Do not port-forward this agent. Do not expose it directly to the public
internet. A token URL is shell access to that Windows account while the process
is running.
