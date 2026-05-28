# Installation Guide

## Goal

Install ARHIAX Dx Agent into a client-controlled environment without changing the packaged governance core.

## Steps

1. Clone the repo into the client environment.
2. Create a virtual environment and install dependencies.
3. Copy `.env.example` into an environment-specific secret management flow.
4. Run:

```bash
arhiax-dx-install-bootstrap
```

5. Complete the generated install manifest.
6. Inject:
   - Gemini key
   - Anthropic key
   - HIC webhook
   - Ed25519 signing key
7. Validate:

```bash
arhiax-dx-validate
```

8. Start the service:

```bash
uvicorn arhiax_dx.main:app --host 0.0.0.0 --port 8088 --app-dir src
```

## Required Bindings

| Binding | Required | Owner |
|---|---|---|
| `ed25519_signing` | Yes | Client security |
| `gemini_primary` | Yes | Client platform |
| `anthropic_fallback` | Yes | Client platform |
| `hic_webhook` | Yes | Client operations |
| `observability_stack` | Yes | Client platform |

## Optional Bindings

| Binding | Purpose |
|---|---|
| `whatsapp_critical` | Critical escalation |
| `docx_renderer` | Word export |
| `bpmn_renderer` | BPMN asset rendering |

## Validation Rule

The deployment should not be considered ready until:

- install manifest bindings are configured
- keys are injected
- readiness report returns `install_ready = true`

## Non-Negotiable Controls

- Do not disable publication escalation
- Do not widen the authorization boundary
- Do not add undeclared tools by env var
- Do not allow raw respondent retention
