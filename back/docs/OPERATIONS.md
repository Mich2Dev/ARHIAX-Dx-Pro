# Operations

## Operating Window

- timezone: `America/Bogota`
- days: Monday to Friday
- hours: `07:00` to `22:00`

## Runtime Signals

The packaged baseline expects monitoring over:

- tool calls per hour
- p95 latency
- escalation ratio
- deny ratio
- token usage
- QA score
- IRR alpha

## Safe Failure Modes

- undeclared tool -> deny
- undeclared operation -> deny
- raw respondent data request -> deny
- retention > 30 days -> deny
- publication request -> escalate
- low IRR -> escalate
- provider exhaustion on both routes -> deny

## Recommended Client Alerts

- HIC webhook delivery failure
- evidence ledger write failure
- deny spike
- escalation spike
- outside-window request attempts
