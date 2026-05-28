# Post-Install Handoff

## What the Client Owns After Install

- infrastructure
- secrets
- observability
- human escalation channels
- KMS or HSM for signing
- report rendering services if enabled

## What ARHIAX Dx Still Owns as a Packaged Artifact

- governance contract in `specs/`
- policy bundle semantics
- execution decision model
- evidence structure
- certificate format

## Handoff Checklist

- install manifest completed
- webhook ownership assigned
- escalation roster named
- model provider quotas validated
- evidence path persisted
- secret rotation process documented

## Escalation Ownership

| Event | Default Owner |
|---|---|
| publication approval | Director or delegated approver |
| low IRR follow-up | diagnostic lead |
| critical perception gap | consulting lead |
| prompt injection incident | client security and operator |

## Support Boundary

If the client changes:

- tool catalog
- policy matrix
- autonomy profile

they are changing governed behavior and should treat that as a controlled change request, not a normal install tweak.
