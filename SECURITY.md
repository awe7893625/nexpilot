# Security Policy

NexPilot Public Trial is a private beta package. Do not run it on machines you
do not own or administer.

## Supported Use

- Same-computer testing on `127.0.0.1`
- Same-LAN testing with `nexpilot --lan`
- Private-network testing through Tailscale, WireGuard, or equivalent

Direct public internet exposure is not supported.

Public cloud relay is not enabled in this private beta. Do not router
port-forward this agent or place it behind an unaudited public tunnel.

## Redistribution

Tester access is non-transferable. Do not copy, mirror, upload, sublicense,
sell, publish, or redistribute this repository or a tester package. Source
access cannot technically prevent copying by a recipient, so beta distribution
must stay private, invite-only, and per tester.

## Reporting Issues

For private beta testers, report security issues directly to the repo owner.
Do not file public issues containing tokens, terminal output, IP addresses, or
screenshots with private information.

## Token Handling

The printed URL includes a bearer token. Anyone with that URL can control the
shell while the agent is running. Treat it like a password.

Stop the process to revoke the token immediately.
