# Gramática Canónica ARHIAX — Backend v0.3

**Versión:** 0.3  
**Fecha:** 2026-06-23  
**Estado:** Implementado

---

## 1. Arquitectura

```
dxpro_runtime/grammar/
├── __init__.py    # Exportaciones públicas
├── models.py      # Pydantic models (GrammarRule, GrammarFinding, GrammarReport, etc.)
├── rules.py       # Catálogo de 24 reglas canónicas
├── lint.py        # Motor lint puro (lint_text, can_publish, compile_report_text)
└── service.py     # Orquestación + persistencia (GrammarService)
```

El módulo `grammar/` es autocontenido. `api.py` solo expone endpoints y delega en `GrammarService`.

---

## 2. Endpoints

### `POST /v1/agents/grammar/lint`
### `POST /v1/dxpro/agents/grammar/lint`

**Request:**
```json
{
  "text": "Texto a revisar",
  "audience": "client | internal | technical | executive",
  "source": "manual | executive_report",
  "case_id": "opcional — si se provee, persiste el reporte"
}
```

**Response 200:**
```json
{
  "score": 85,
  "critical": 0,
  "major": 2,
  "minor": 1,
  "advisory": 0,
  "total": 3,
  "findings": [
    {
      "finding_id": "uuid",
      "rule_id": "GC-02-TERM-001",
      "block": "7.2 Terminología invariante",
      "severity": "major",
      "message": "ARHIAX debe escribirse en mayúsculas sostenidas",
      "detected_text": "Arhiax",
      "suggestion": "ARHIAX",
      "rationale": "ARHIAX es sigla del corpus...",
      "index": 0,
      "excepted": false
    }
  ],
  "text_hash_sha256": "abc123...",
  "timestamp": "2026-06-23T...",
  "audience": "client",
  "source": "manual",
  "publish_decision": {
    "allowed": true,
    "confirm_required": true,
    "reason": "Hallazgos mayores detectados. Requiere confirmación o justificación."
  }
}
```

**HTTP 400:** texto vacío o audiencia inválida.

### `GET /v1/cases/{case_id}/grammar`

Retorna el último `GrammarReport` persistido para un caso.

**Response 200:**
```json
{
  "case_id": "case-123",
  "grammar_report": { ... } | null,
  "exceptions": []
}
```

### `POST /v1/cases/{case_id}/publish`

Publica un caso validando gramática canónica.

**Request:**
```json
{
  "case_id": "case-123",
  "action": "publish",
  "grammar_confirmed": false,
  "reviewer": { "name": "Consultor", "role": "engagement_manager" }
}
```

**Comportamiento:**
- Críticos abiertos → `approved: false`, `grammar_blocked: true`
- Mayores abiertos + no confirmado → `approved: false`, `grammar_confirm_required: true`
- Mayores abiertos + confirmado → `approved: true`
- Sin hallazgos → `approved: true`

---

## 3. Modelos (Pydantic)

Ver `models.py` para definiciones completas.

| Modelo | Campos clave |
|---|---|
| `GrammarRule` | id, block, title, severity, pattern, suggestion, rationale, audience |
| `GrammarFinding` | finding_id, rule_id, block, severity, message, detected_text, suggestion, rationale, index, excepted |
| `GrammarException` | finding_id, rule_id, detected_text, reason, reviewer, created_at |
| `PublishDecision` | allowed, confirm_required, reason |
| `GrammarReport` | score, critical, major, minor, advisory, total, findings, text_hash_sha256, timestamp, audience, source, publish_decision |
| `GrammarReportSummary` | case_id, grammar_report, exceptions |

---

## 4. Reglas incluidas (24 reglas)

| ID | Categoría | Severidad | Audiencia |
|---|---|---|---|
| GC-01-ENCODING-001 | Mojibake | critical | todas |
| GC-02-TERM-001 | ARHIAX minúscula | major | client, executive |
| GC-02-TERM-002 | ARHIAX DxPro sin espacio | major | client, executive |
| GC-02-TERM-003 | DxPro sin espacio | major | client, executive |
| GC-02-TERM-004 | DXPRO en texto | major | client, executive |
| GC-02-TERM-005 | governex minúscula | major | client, executive |
| GC-03-OXFORD-001 | Coma de Oxford | minor | client |
| GC-04-CALCO-001~006 | Calcos inglés | major | client |
| GC-05-FLUID-001~005 | Falsa fluidez | advisory | client |
| GC-06-RAE-001 | Mes mayúscula | minor | client |
| GC-06-RAE-002 | Día mayúscula | minor | client |
| GC-07-REG-001 | custodio | minor | client |
| GC-07-REG-002 | desvelamiento | minor | client |
| GC-07-REG-003 | umbral | minor | client |

---

## 5. Scoring

```
score = max(0, min(100, round(100 - (critical * 25 + major * 8 + minor * 3 + advisory * 1))))
```

---

## 6. PublishDecision

| Estado | Resultado |
|---|---|
| Sin revisión | `allowed=True, confirm_required=True` |
| Críticos abiertos | `allowed=False` |
| Críticos exceptuados | `allowed=True, confirm_required=True` |
| Mayores abiertos | `allowed=True, confirm_required=True` |
| Mayores exceptuados | `allowed=True` |
| Solo menores/advisory | `allowed=True` |
| Sin hallazgos | `allowed=True` |

---

## 7. Integración HIL

### Endpoint dedicado: `POST /v1/cases/{case_id}/publish`

Verifica `grammar_report.publish_decision` antes de aprobar:
- Críticos abiertos → bloquea publicación
- Mayores abiertos → exige `grammar_confirmed=true` en el payload
- Sin issues → aprueba automáticamente

### Endpoint existente blindado: `POST /v1/agents/cases/approval`

Cuando `action="publish"`, se intercepta la petición y se ejecuta el mismo grammar check antes de delegar al agente:
- Si hay críticos → `grammar_blocked: true`, `grammar_bypass_detected: true`
- Si hay mayores sin confirmación en payload → `grammar_confirm_required: true`
- Si pasa → se delega al agente normalmente

`action="approve"` o `action="reject"` pasan directamente al agente sin intervención.

---

## 8. Integración con report export

`ReportExportService.export()` ejecuta `lint_text()` sobre el markdown del report pack ANTES de exportar:
- Si hay críticos abiertos y el target no es `draft`, lanza `RuntimeError`
- Si el target incluye `draft`, exporta con status `draft_requires_canonical_review`
- Adjunta `grammar_report` al `report_pack`

---

## 9. Persistencia

Los reportes gramaticales se persisten dentro del JSON del caso:
```json
{
  "grammar": {
    "report": { ... },
    "exceptions": [],
    "updated_at": "2026-06-23T..."
  }
}
```

- Si `case_id` se provee en lint, se persiste automáticamente
- Si no hay `case_id`, se devuelve sin persistir
- Casos sin grammar retornan `null`

---

## 10. Tests

35 tests en `tests/test_grammar.py`:

| Suite | Tests | Descripción |
|---|---|---|
| `TestLintText` | 11 | Motor lint: detección, audiencia, scoring, hash |
| `TestCanPublish` | 6 | Decisiones de publicación con/sin excepciones |
| `TestCompileReportText` | 3 | Generación de texto copiable |
| `TestGrammarAPI` | 6 | Endpoints HTTP: lint, alias, persistencia, validación |
| `TestPublishGrammar` | 3 | Integración HIL: bloqueo, confirmación, aprobación |
| `TestBypassPrevention` | 3 | Bypass HIL: crítico, mayor, approve pasa a través |
| `TestExportGrammar` | 3 | Export: bloqueo final, draft permite, adjunta reporte |

---

## 11. Límites conocidos (v0.3)

- No hay reescritura automática con LLM
- No hay autocorrección masiva
- No hay interfaz visual nueva
- No hay motor NLP avanzado
- Las excepciones se persisten pero no tienen endpoint dedicado CRUD
- La exportación PDF/DOCX no incluye visualmente el audit pack gramatical
- El patrón de mojibake `GC-01-ENCODING-001` detecta `Ã` y `±` pero no cubre `?` como carácter de reemplazo mojibake (depende del códec del emisor)

---

## 12. Diferencia frontend lint vs backend lint

| Aspecto | Frontend (v0.2) | Backend (v0.3) |
|---|---|---|
| Motor | TypeScript en React | Python puro en runtime |
| Reglas | Mismas 24 reglas | Mismas 24 reglas (replicadas) |
| Persistencia | Estado local (React state) | CaseStore (JSON en disco) |
| API | Ninguna (solo UI) | REST endpoints + alias /v1/dxpro |
| HIL | Modal de confirmación | Endpoint /publish con validación |
| Exportación | N/A | Integrado en ReportExportService |

---

## 13. Próximos pasos (v0.4)

- Audit pack editorial en PDF/DOCX con sello gramatical
- Comparación texto original vs. texto corregido
- Almacenamiento histórico de revisiones por caso
- Endpoint CRUD para excepciones
- Panel de trazabilidad canónica en frontend
- Redactor asistido (sin autocorrector ciego)
