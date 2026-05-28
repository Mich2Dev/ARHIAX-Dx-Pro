# Control Traceability Matrix

| Requirement | Control | Code | Spec | Test |
|---|---|---|---|---|
| Client identity required | `DX-G1-IDENTITY` | `services/governance.py` | `agent_identity.json` | `tests/test_governance.py` |
| Boundary required | `DX-G2-BOUNDARY` | `services/governance.py` | `agent_identity.json` | `tests/test_governance.py` |
| Undeclared tool denied | `DX-TOOLS-001` | `services/governance.py` | `tool_catalog.json` | `tests/test_governance.py` |
| Undeclared operation denied | `DX-OPS-001` | `services/governance.py` | `operation_catalog.json` | `tests/test_governance.py` |
| Raw respondent data denied | `DX-DATA-002` | `services/governance.py` | `data_scopes.json` | `tests/test_governance.py` |
| Prompt injection denied | `DX-RISK-001` | `services/governance.py` | `policy_matrix.json` | `tests/test_governance.py` |
| QA gate for DOCX | `DX-QA-001` | `services/governance.py` | `tool_catalog.json` | `tests/test_governance.py` |
| Publication escalates | `DX-HIC-001` | `services/governance.py` | `autonomy_profile.json` | `tests/test_governance.py` |
| Retention cap enforced | `DX-DATA-003` | `services/governance.py` | `data_scopes.json` | `tests/test_governance.py` |
| Evidence always emitted | `DX-G5-EVIDENCE` | `services/evidence.py` | `policy_matrix.json` | `tests/test_api.py` |
