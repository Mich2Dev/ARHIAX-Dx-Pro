# DX to DX Pro Matrix

## Purpose

This matrix records how DX Pro covers the ARHIAX DX product surface while remaining independent.

| Capability | ARHIAX DX Reference | DX Pro Standalone Direction |
|---|---|---|
| Runtime API | FastAPI diagnostic surface | FastAPI diagnostic + PMEL surface |
| Compliance posture | Packaged governance contract | Packaged DX Pro contract with PMEL/ATK |
| Tool catalog | DX diagnostic tools | DX diagnostic tools plus Pro PMEL tools |
| Data scopes | Organizational diagnostic scopes | Organizational, PMEL, BPMN, DMN and evidence scopes |
| Autonomy | Starts A1, promotion to A2 | Starts A1, caps at A2, denies A3/A4 in PMEL |
| Evidence | Append-only ledger | HMAC chained ledger with file lock |
| Certificates | Ed25519 in DX reference | HMAC-SHA256 now, Ed25519/KMS planned |
| Policy model | Python governance and Rego bundles | Python governance plus PMEL Rego/OPA path |
| Human approval | Publication and critical gates | Publication, IRR, delta sigma and PMEL escalation |
| Install readiness | Client deployment checklist | Standalone DX Pro binding blueprint |

## Independence Rule

DX Pro may reuse ideas from DX, but must not import, subclass or require `arhiax_dx`.

The package boundary is `dxpro_runtime`.
