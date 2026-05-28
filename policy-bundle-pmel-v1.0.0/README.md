# pmel-runtime v1.0.0 — ARHIA Policy Bundle

**Classification:** SECRETO EMPRESARIAL — Sinergia Consulting Group S.A.S.
**Gap closed:** G-01 from SDX-01 v1.0 §8.1
**Acompañamiento documental:** TR-2026-037 — Policy Bundle PMEL v1.0 Documentation

## Purpose

This OPA/Rego policy bundle makes PMEL policy-as-code. Every governance decision that
previously lived inside the Python/TypeScript agent runtime is now evaluated by the
ARHIA Policy Engine via `opa eval` or the OPA runtime SDK.

## Scope covered

- BPMN-Lint rules R1–R12 (catálogo v1.0)
- TO-BE Generator 4 prohibitions (P1–P4)
- Agent cycle limits (Capture 5, TO-BE 3)
- Consent gates (T1/T2/T3 per Paso 6)
- Sensitive data handling (Cláusula 5.1 Paso 6)
- Retention enforcement (§3.8, §4.6 Paso 6)
- Decommissioning triggers (D1/D2/D3/D4 per TR-036)
- Crypto-shred preconditions (TR-036 §3.7)
- Autonomy enforcement (A2 fixed)
- HIC checkpoints
- AIBOM validation

## Directory layout

```
policy-bundle-pmel-v1.0.0/
├── manifest.json              # Bundle metadata
├── base/                      # Cross-cutting ARHIA enforcement
├── bpmn_lint/                 # R1-R12 rules
├── pmel_governance/           # TO-BE, cycles, consent, sensitive, retention
├── decommissioning/           # Triggers and crypto-shred preconditions
├── data/                      # Externalized thresholds and lexicons
└── tests/                     # ~60 test cases
```

## Deployment

```bash
# Verify bundle integrity
opa check policy-bundle-pmel-v1.0.0/ --strict

# Run tests
opa test policy-bundle-pmel-v1.0.0/ -v

# Start OPA in server mode with the bundle loaded
opa run --server --set=decision_logs.console=true policy-bundle-pmel-v1.0.0/
```

## Decision endpoints

All decisions follow ARHIA ATK 6-outcome model:
`PERMIT` / `DENY` / `ESCALATE` / `MODIFY` / `AUDIT` / `SUSPEND`

Example queries (after `opa run`):

```bash
# BPMN lint R1
curl -X POST http://localhost:8181/v1/data/arhia/pmel/bpmn_lint/r01_gateways/decision \
  -d @examples/r01_input.json

# Consent gate
curl -X POST http://localhost:8181/v1/data/arhia/pmel/governance/consent_gates/decision \
  -d @examples/consent_gate_input.json
```

## Gap flags

Configurable in `data/thresholds.json`:

- `g06_closed`: toggles R12 threshold behavior (currently false — mitigated by human review)
- `g07_closed`: toggles R6 DMN engine enforcement (currently false — delegates to Consultor)
- `g08_closed`: toggles D1 partial revocation crypto-shred (currently false — tombstone path)

Changes to these flags do not require re-release; they are evaluated at query time.

## Signing and versioning

Bundle is signed with Sinergia's RS256 signing key (`key_id` in `manifest.json`).
Verify with:

```bash
opa sign policy-bundle-pmel-v1.0.0/ --signing-key private_key.pem \
         --bundle --claims-file claims.json
```

## Change log

| Version | Date       | Changes                                         |
|---------|------------|-------------------------------------------------|
| 1.0.0   | 2026-04-17 | Initial release. Closes SDX-01 gap G-01.        |
