# Security Policy

NexPilot Public Trial is a private beta package. Do not run it on machines you
do not own or administer.

## Supported Use

- Same-computer testing on `127.0.0.1`
- Same-LAN testing with `nexpilot --lan`
- Private-network testing through Tailscale, WireGuard, or equivalent

Direct public internet exposure is not supported.

## Reporting Issues

For private beta testers, report security issues directly to the repo owner.
Do not file public issues containing tokens, terminal output, IP addresses, or
screenshots with private information.

## Token Handling

The printed URL includes a bearer token. Anyone with that URL can control the
shell while the agent is running. Treat it like a password.

Stop the process to revoke the token immediately.
