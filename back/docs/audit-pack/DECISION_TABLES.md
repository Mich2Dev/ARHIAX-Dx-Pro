# Decision Tables

| Condition | Outcome |
|---|---|
| client identity missing | `DENY` |
| authorization boundary mismatch | `DENY` |
| undeclared tool requested | `DENY` |
| undeclared operation requested | `DENY` |
| raw respondent storage requested | `DENY` |
| prompt injection detected | `DENY` |
| retention > 30 days | `DENY` |
| docx requested and QA < 85 | `DENY` |
| publish report requested | `ESCALATE_TO_HUMAN` |
| `delta_sigma > 2` | `ESCALATE_TO_HUMAN` |
| `irr_alpha < 0.70` | `ESCALATE_TO_HUMAN` |
| all controls pass | `ALLOW` |
