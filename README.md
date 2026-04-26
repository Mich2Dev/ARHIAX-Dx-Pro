# ARHIAX DX Pro Runtime

Runtime standalone para ARHIAX DX Pro. Toma la cobertura funcional de ARHIAX DX como referencia, pero no importa ni necesita el paquete `arhiax_dx`: DX Pro trae su propio catalogo, gobernanza, evidencia, diagnostico y capa PMEL/ATK.

## Objetivo

Cubrir el flujo productivo mejorado:

1. Recibir una solicitud de diagnostico organizacional.
2. Validar identidad, frontera, mandato, herramientas, operaciones, datos, autonomia, QA y HIC.
3. Ejecutar cadena PMEL previa con outcomes ATK.
4. Construir plan de ejecucion y evidencia por decision.
5. Emitir certificado de provenance HMAC-SHA256.
6. Mantener endpoints PMEL directos para captura y validacion de procesos.

## Estado

Producto standalone en fase vertical. OPA es el camino principal de decision: primero `DXPRO_OPA_URL`, luego binario `opa` local, y solo despues fallback nativo auditado. El fallback cubre los 22 paquetes declarados en el bundle PMEL para evitar saltos silenciosos de cobertura.

## Endpoints

- `GET /healthz`
- `GET /readyz`
- `GET /v1/compliance/posture`
- `GET /v1/compliance/install-readiness`
- `GET /v1/compliance/install-blueprint`
- `POST /v1/diagnostics/evaluate`
- `POST /v1/pmel/evaluate`
- `POST /v1/pmel/run-step`
- `POST /v1/pmel/capture`
- `POST /v1/dxpro/pmel/evaluate`
- `POST /v1/dxpro/pmel/run-step`
- `POST /v1/dxpro/pmel/capture`
- `POST /v1/agents/to-be/generate`
- `POST /v1/agents/bpmn-lint`
- `POST /v1/agents/visual-interpret`
- `POST /v1/agents/dmn/evaluate`
- `POST /v1/agents/crypto/decommission`
- `GET /v1/evidence`
- `GET /v1/evidence?trace_id={trace_id}`
- `GET /v1/pmel/runs/{trace_id}`
- `GET /v1/evidence/verify`
- `POST /v1/certificates/verify`
- `GET /v1/audit-pack/{trace_id}`

## Local Server

Run the FastAPI server:

```powershell
$env:PYTHONPATH='src'
python -m dxpro_runtime.server
```

Default URL:

```text
http://127.0.0.1:8310
```

OpenAPI is available at:

```text
http://127.0.0.1:8310/docs
```

## Diagnostic Evaluate

`POST /v1/diagnostics/evaluate` ejecuta el diagnostico gobernado completo de DX Pro:

- contrato de cliente y frontera `boundary-diagnostico-org-pro`
- catalogo cerrado de herramientas DX + herramientas Pro PMEL
- reglas de datos, autonomia, QA, IRR, delta sigma, retencion y publicacion
- PMEL pre-ejecucion con `autonomy`, `consent_gates`, `aibom` y `cycle_limits`
- evidencia `diagnostic_evaluation`
- certificado HMAC-SHA256

El response incluye `decision`, `execution_plan`, `pmel_step`, `certificate`, `rule_results`, `trace_id` y `evidence_id`.

## Certificates and Audit Pack

`POST /v1/certificates/verify` validates the HMAC-SHA256 certificate signature and checks whether the referenced diagnostic evidence HMAC exists in the ledger trace.

Payload:

```json
{
  "certificate": {}
}
```

`GET /v1/audit-pack/{trace_id}` returns a complete audit package:

- ledger verification result
- PMEL evidence ids
- diagnostic evidence ids
- certificate evidence ids
- certificate verification results
- ordered evidence entries for the trace

When certificate issuance is enabled, a diagnostic evaluation writes 7 evidence entries:

1. Four PMEL `policy_decision` entries.
2. One `pmel_step_aggregate` entry.
3. One `diagnostic_evaluation` entry.
4. One `provenance_certificate` entry.

## Run Step

`POST /v1/pmel/run-step` ejecuta una cadena de politicas PMEL y agrega el resultado por prioridad ATK:

1. `SUSPEND`
2. `DENY`
3. `ESCALATE`
4. `MODIFY`
5. `AUDIT`
6. `PERMIT`

Por defecto evalua:

- `arhia.pmel.base.autonomy`
- `arhia.pmel.governance.consent_gates`
- `arhia.pmel.base.aibom`
- `arhia.pmel.governance.cycle_limits`

Cada decision genera evidencia individual y el resultado agregado genera una evidencia adicional.

## Fixtures

Casos reproducibles:

- `fixtures/run_step_permit.json`
- `fixtures/run_step_missing_consent.json`
- `fixtures/run_step_autonomy_a3.json`
- `fixtures/run_step_cycle_suspend.json`
- `fixtures/capture_permit.json`

Ejecutar fixture de `run-step`:

```powershell
python scripts/run_fixture.py fixtures/run_step_permit.json
```

## Capture Agent Stub

`POST /v1/pmel/capture` ejecuta gobernanza previa a ingesta y, si el agregado ATK permite continuar, devuelve un artefacto `pmel_capture_draft` con actividades preliminares derivadas del texto de entrevista.

Si la gobernanza devuelve `DENY`, `ESCALATE` o `SUSPEND`, el artefacto queda en `null`.

## Pro Agents

DX Pro incluye agentes Pro standalone, todos gobernados por `run_step` antes de generar artefactos:

- `PmelToBeGenerator`: genera blueprint TO-BE desde actividades AS-IS.
- `PmelBpmnLintAgent`: produce reporte de lint BPMN.
- `PmelVisualInterpreter`: mapea observaciones visuales a senales de proceso.
- `DmnEngine`: evalua tablas de decision deterministicas.
- `CryptoParticipant`: prepara plan de decommissioning/crypto-shred en modo `plan_only`.

Cada agente registra evidencia PMEL individual, evidencia agregada y un evento `agent_artifact` cuando la decision permite crear el artefacto.

## OPA

DX Pro treats OPA as the primary policy path.

Policy engine mode selection:

1. `opa-http` when `DXPRO_OPA_URL` points to a running OPA server.
2. `opa-cli` when the `opa` binary is available locally.
3. `native-fallback` only for development/degraded mode.

The native fallback now covers every package declared by `policy-bundle-pmel-v1.0.0/manifest.json`, so full-bundle tests do not silently skip policies when OPA is unavailable.

Run the full bundle through the runtime:

```json
{
  "subject": "pmel-full-bundle",
  "scope": "full_bundle",
  "input": {}
}
```

Validate bundle with OPA local or Docker:

```powershell
python scripts/validate_opa.py
```

El script usa `opa` si esta instalado. Si no, intenta Docker con `openpolicyagent/opa:0.68.0-rootless`.

## Smoke Test

```powershell
python scripts/smoke_test.py
```

## Tests

```powershell
$env:PYTHONPATH='src'; python -m pytest tests -q
```

## CI

The GitHub Actions workflow in `.github/workflows/ci.yml` runs:

- package install
- unit and API tests
- smoke test
- OPA bundle validation
