# ARHIAX DX Pro Governance Specification

## Governance Objective

DX Pro must execute organizational diagnostics under an explicit governance contract. The runtime should deny, escalate, modify, audit, suspend or permit work before uncontrolled automation can affect client outputs.

## Decision Outcomes

DX Pro uses the ARHIAX ATK outcome set:

| Outcome | Meaning |
|---|---|
| `PERMIT` | Continue execution |
| `AUDIT` | Continue and record audit signal |
| `MODIFY` | Continue only after controlled transformation |
| `ESCALATE` | Require human review |
| `DENY` | Block request |
| `SUSPEND` | Stop the component or cycle |

Restrictive priority is:

1. `SUSPEND`
2. `DENY`
3. `ESCALATE`
4. `MODIFY`
5. `AUDIT`
6. `PERMIT`

## Diagnostic Rules

| Rule | Purpose | Blocking Outcome |
|---|---|---|
| `DXPRO-G1-IDENTITY` | Client identity and legal entity must be present | `DENY` |
| `DXPRO-G2-BOUNDARY` | Request must match `boundary-diagnostico-org-pro` | `DENY` |
| `DXPRO-MANDATE-001` | Mandate must include organization size | `DENY` |
| `DXPRO-TOOLS-001` | Tools must be declared in the DX Pro catalog | `DENY` |
| `DXPRO-OPS-001` | Operations must be declared and enabled | `DENY` |
| `DXPRO-DATA-001` | Data scopes must be declared | `DENY` |
| `DXPRO-AUTONOMY-001` | Autonomy must be valid and not exceed A2 | `DENY` |
| `DXPRO-DATA-002` | Raw respondent storage is not allowed | `DENY` |
| `DXPRO-RISK-001` | Prompt injection patterns are blocked | `DENY` |
| `DXPRO-OPS-002` | Execution must stay inside operating window | `DENY` |
| `DXPRO-QA-001` | DOCX generation requires QA >= 85 | `DENY` |
| `DXPRO-HIC-001` | Publication always requires human review | `ESCALATE` |
| `DXPRO-HIC-002` | Critical delta sigma requires review | `ESCALATE` |
| `DXPRO-RISK-002` | IRR below 0.70 requires review | `ESCALATE` |
| `DXPRO-DATA-003` | Retention may not exceed 30 days | `DENY` |

## PMEL Pre-Execution Chain

Default PMEL chain:

1. `arhia.pmel.base.autonomy`
2. `arhia.pmel.governance.consent_gates`
3. `arhia.pmel.base.aibom`
4. `arhia.pmel.governance.cycle_limits`

Each package emits evidence before aggregation. The aggregate result is then merged with the diagnostic rule result.

## Pro Agent Controls

DX Pro Pro agents must execute through PMEL pre-execution controls before generating any artifact. The current agent set is:

- `PmelToBeGenerator`
- `PmelBpmnLintAgent`
- `PmelVisualInterpreter`
- `DmnEngine`
- `CryptoParticipant`
- `RgcAgent`
- `RgcDeepResearchContrasterAgent`
- `AdaptiveQuestionBankAgent`
- `MultiRoleScoringAgent`
- `PsychometricsAgent`
- `IrrReliabilityAgent`
- `BayesianSynthesisAgent`
- `ExecutiveQaAgent`
- `DiagnosticIntelligenceAgent`
- `DiagnosticFusionCycleAgent`

The artifact is blocked when PMEL returns `DENY`, `ESCALATE` or `SUSPEND`. Permitted executions record an `agent_artifact` evidence event after the individual policy decisions and aggregate evidence.

The fused diagnostic agents keep DX Pro as the execution boundary. They add organizational diagnostic depth from ARHIAX DX while preserving PMEL/ATK controls, AIBOM declaration, cycle limits, consent gates and evidence logging.

`DiagnosticFusionCycleAgent` is the governed orchestrator for the fusion layer. It does not bypass child controls: every child agent still runs its own PMEL pre-execution chain and writes its own artifact evidence under the parent trace.

## Autonomy

DX Pro starts at `A1` and caps normal runtime autonomy at `A2`.

Requests for `A3` or `A4` are denied by PMEL autonomy policy.

Promotion readiness requires:

- 30 clean BBR days
- QA average for last five executions >= 87
- IRR alpha >= 0.75
- human approval

## Human Intervention

The following conditions escalate:

- report publication
- `delta_sigma > 2`
- `irr_alpha < 0.70`
- PMEL package outcome `ESCALATE`

Human intervention channel binding is completed during client installation.

## Evidence Requirements

Every response must include:

- `trace_id`
- final decision
- PMEL step decision
- evidence id
- rule results
- execution plan

Certificate issuance is enabled by default unless `processing_profile.issue_certificate` is `false`.

Certificates can be verified through `POST /v1/certificates/verify`. Verification has two layers:

- signature validity over the certificate body
- evidence binding against the diagnostic evidence HMAC stored in the ledger trace

`trusted=true` requires both layers to pass.

`GET /v1/audit-pack/{trace_id}` returns the evidence entries, certificate entries and verification results for a trace.

## Current Implementation Status

Implemented:

- standalone catalog
- diagnostic rules
- PMEL chain
- ATK aggregation
- HMAC evidence ledger
- HMAC provenance certificate
- FastAPI runtime surface
- audit pack by `trace_id`
- certificate verification with evidence binding
- OPA-first policy mode selection
- native fallback coverage for all 22 PMEL bundle packages
- full-bundle runtime execution through `scope="full_bundle"`
- governed Pro agents with artifact evidence

Planned hardening:

- confirm CI run is green after GitHub publish
- Ed25519 or KMS-backed signatures
- downloadable audit pack artifact formats
