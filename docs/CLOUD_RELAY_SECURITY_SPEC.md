# Cloud Relay Security Spec

Public cloud relay is intentionally not enabled in this private beta package.

Reason: a public relay for remote shell is a high-risk feature. Shipping it
without the controls below would turn a leaked URL, token, or relay bug into
internet-reachable shell access.

## Required Before Enabling

- End-to-end encryption where the relay cannot read terminal payloads.
- Device-bound identity for the computer agent.
- User-bound identity for the phone/browser.
- Short-lived session grants.
- Revocation from the owner side.
- Audit logs that record metadata only, not terminal payload.
- Public relay SSRF protection and private metadata IP blocklist.
- Rate limits and abuse detection.
- Explicit owner approval per device.
- Security review and rollback procedure.

## Approved Private Beta Network Paths

Use one of these instead:

- Same Wi-Fi/LAN with `nexpilot --lan`.
- Tester-owned Tailscale tailnet.
- Tester-owned WireGuard or equivalent private network.

Do not use Rain's internal tailnet. Do not router-port-forward the local agent.
Do not expose `:8765` directly to the public internet.

## Implementation Status

The private beta package is prepared so a relay can be added later behind a
separate feature flag and security review. It does not ship a public relay
endpoint today.
