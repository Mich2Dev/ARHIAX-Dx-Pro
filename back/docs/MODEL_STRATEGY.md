# Model Strategy

## Packaged Providers

- primary: Gemini
- fallback: Anthropic

## Fallback Policy

If Gemini returns:

- `429`
- `503`

the runtime may route to Anthropic.

If both providers fail:

- the execution is denied
- HIC severity is medium

## Stage Mapping

| Stage | Typical Tools | Primary | Fallback |
|---|---|---|---|
| survey design | `g09a_preguntas`, `g09b_ramificacion`, `g09c_validacion` | Gemini | Anthropic |
| analysis | `g10a_scoring`, `g10b_psicometria`, `g11a_bayesiano` | Gemini | Anthropic |
| design | `g06_bpmn_architect`, `g07_cuellos`, `g08_optimizador` | Gemini | Anthropic |
| reporting | `g12_hallazgos`, `g13_redactor`, `g14_qa_control` | Gemini | Anthropic |

## Why This Matters for Audit

The agent does not choose model routing ad hoc.

Routing is:

- declared
- versioned
- reviewable
- bounded by the tool stage
