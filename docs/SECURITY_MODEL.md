# Security Model

NexPilot Public Trial is a local agent. The tester runs it on their own
computer and opens a browser UI from a phone.

## Trust Boundary

- Trusted: the tester's computer, the tester's phone, and the private network
  between them.
- Not trusted: public internet clients, unknown LAN users, shared Wi-Fi, and any
  person who can see the token URL.

## Authentication

The server generates a random access token at startup unless `--token` or
`NEXPILOT_TOKEN` is provided. API and WebSocket terminal access require the
token.

Anyone with the token can control the shell while the agent is running. Treat
the printed URL like a password.

## Authorization

This beta has one authorization level: full terminal access as the OS user who
started the process. Do not run as `root` or with administrator elevation.

## Network Exposure

Default mode binds to `127.0.0.1`. Phone mode uses `--lan`, which binds to
`0.0.0.0` so a phone on the same network can connect.

Do not expose `--lan` directly to the public internet. For remote use, put the
computer and phone on a private network such as Tailscale or WireGuard.

## Data Handling

The public package does not include Rain's private M4/Kai/NexDesk runtime,
internal databases, task artifacts, logs, device IDs, service tokens, or
production relay settings.

The beta server does not persist terminal transcripts. Your shell history and
any files you touch remain governed by your own computer and shell settings.

The server keeps a bounded in-memory replay buffer for terminal reconnect. The
buffer is not written to disk and is cleared when the process exits.

## Revocation

Stop the `nexpilot` process to revoke access immediately. Restarting without
`--token` generates a new token.

## Known Limits

- Terminal reconnect keeps a detached shell alive only for the configured idle
  window.
- Windows support is private beta through optional ConPTY dependencies.
- No multi-user roles.
- No public relay service.
- No end-to-end encrypted cloud relay.
- Source access cannot technically prevent a recipient from copying the code;
  private beta distribution relies on non-transferable terms, private invites,
  per-tester packages, and checksums.
