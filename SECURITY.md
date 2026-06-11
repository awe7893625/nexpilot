# Security Policy

NexPilot is a local agent that exposes terminal access behind an access token.
Only run it on machines you own or administer.

## Supported Use

- Same-computer use on `127.0.0.1`
- Same-LAN use with `nexpilot --lan`
- Private-network use through Tailscale, WireGuard, or equivalent

Direct public internet exposure is not supported. Do not port-forward this agent
or place it behind an unaudited public tunnel.

## Reporting Issues

Report security issues by opening a GitHub issue, or privately to the repo owner
for sensitive reports. Do not include tokens, terminal output, IP addresses, or
screenshots with private information in a public issue.

## Token Handling

The printed URL includes a bearer token. Anyone with that URL can control the
shell while the agent is running. Treat it like a password.

Stop the process to revoke the token immediately.
