# Audit Matrix

## Audit Questions This Repo Answers

| Question | Evidence |
|---|---|
| What is the agent allowed to do? | `specs/tool_catalog.json`, `specs/operation_catalog.json` |
| What data can it touch? | `specs/data_scopes.json` |
| What autonomy is allowed? | `specs/autonomy_profile.json` |
| What happens when a rule is violated? | `src/arhiax_dx/services/governance.py` |
| How are decisions recorded? | `src/arhiax_dx/services/evidence.py` |
| How are decisions signed? | `src/arhiax_dx/services/provenance.py` |
| What remains for client install? | `src/arhiax_dx/installation_assets.py` |

## Audit Readiness Position

This repo is:

- ready for logic audit
- ready for governance review
- ready for client-hosted install

This repo is not:

- a full client environment
- a provider contract
- a replacement for legal review
