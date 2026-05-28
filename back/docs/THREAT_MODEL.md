# Threat Model

## Top Risks

1. Prompt injection in mandate text
2. Unauthorized publication attempt
3. Tool catalog expansion outside governance
4. Non-anonymized respondent handling
5. Silent autonomy promotion
6. Evidence tampering
7. Secret injection failures at deployment time

## Threat to Control Mapping

| Threat | Packaged Control |
|---|---|
| prompt injection | `DX-RISK-001` |
| publication without approval | `DX-HIC-001` |
| undeclared tools | `DX-TOOLS-001` |
| raw respondent data | `DX-DATA-002` |
| autonomy drift | `DX-AUTONOMY-002` |
| evidence tampering | hash-chained ledger |
| excessive retention | `DX-DATA-003` |

## Residual Risk

The client environment still controls:

- secret handling quality
- webhook endpoint security
- KMS key governance
- network controls

Those are deployment and operational risks, not gaps in the packaged agent logic.
