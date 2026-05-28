# Test Coverage Governance

Current automated tests cover:

- spec loading
- compliance posture endpoint
- install blueprint endpoint
- denial of undeclared tools
- denial of raw respondent storage
- denial of excessive retention
- denial of prompt injection
- escalation of publication requests
- escalation of low IRR
- denial of DOCX generation with low QA
- evidence ledger append behavior

Gaps intentionally left for client environment testing:

- actual webhook delivery
- actual Gemini and Anthropic provider calls
- client KMS/HSM key loading
