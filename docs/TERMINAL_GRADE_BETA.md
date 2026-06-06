# Terminal-Grade Private Beta

This release moves the terminal from a simple WebSocket demo toward a
Termius-like beta baseline.

## Included In 0.2.0

- Interactive xterm.js terminal.
- POSIX PTY on macOS/Linux.
- Windows ConPTY backend through optional `pywinpty`.
- Session reconnect with a detached shell window.
- Recent terminal output replay after reconnect.
- Server heartbeat and browser stale-connection detection.
- Bounded server output queues so a slow phone cannot grow memory without
  limits.
- Browser-side output batching with animation-frame writes.
- Browser-side input micro-batching.
- Large paste chunking.
- Copy, paste, and clear controls.
- Mobile viewport handling for on-screen keyboards.

## Still Not Full Termius

NexPilot is not yet a complete Termius replacement.

Still pending:

- Saved host profile management beyond this local agent.
- Host-key trust UX for browser SSH profiles.
- Native signed macOS/Windows installers.
- Managed auto-start service.
- Public cloud relay with end-to-end encryption and audit logging.
- Long physical-phone soak across sleep/wake, network switches, and large
  scrollback.

## Acceptance Target

For private beta, the terminal is acceptable when:

- Local terminal smoke passes.
- Reconnect keeps the same shell alive within the configured idle window.
- Large paste is chunked and reaches the shell.
- Mobile viewport can type, paste, copy, and reconnect without page reload.
- Windows beta starts a ConPTY-backed shell after `pywinpty` install.
