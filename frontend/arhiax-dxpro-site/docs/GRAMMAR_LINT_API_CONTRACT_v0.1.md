# Contrato API — Gramática Canónica ARHIAX (Lint)

**Versión:** 0.1  
**Estado:** Borrador para implementación futura  
**Última actualización:** 2026-06-23

---

## Endpoint

```
POST /v1/agents/grammar/lint
```

## Request

```json
{
  "text": "string — texto a revisar",
  "audience": "client | internal | technical | executive",
  "engagement_id": "string — opcional, para trazabilidad",
  "exceptions": [
    {
      "rule_id": "string",
      "detected_text": "string",
      "reason": "string — justificación de la excepción",
      "reviewer": "string",
      "created_at": "string — ISO 8601"
    }
  ]
}
```

### Campos

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `text` | string | sí | Texto a evaluar contra la gramática canónica |
| `audience` | enum | sí | Audiencia objetivo del texto |
| `engagement_id` | string | no | ID del engagement para trazabilidad |
| `exceptions` | array | no | Lista de excepciones pre-aprobadas |

## Response (200 OK)

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
      "rule_id": "GC-02-TERM-001",
      "block": "Bloque 8 — Terminología invariante",
      "severity": "major",
      "message": "ARHIAX debe escribirse en mayúsculas",
      "detected_text": "Arhiax",
      "suggestion": "ARHIAX",
      "rationale": "ARHIAX es sigla del corpus y se escribe siempre en versales.",
      "index": 0,
      "excepted": false
    }
  ],
  "publish_decision": {
    "allowed": true,
    "confirm_required": true,
    "reason": "Hallazgos mayores detectados. Requiere confirmación."
  },
  "engagement_id": "eng-xxx",
  "linted_at": "2026-06-23T14:00:00.000Z",
  "lint_version": "1.0"
}
```

### Response — campos

| Campo | Tipo | Descripción |
|---|---|---|
| `score` | number | 0–100 |
| `critical` | number | Conteo de hallazgos críticos |
| `major` | number | Conteo de hallazgos mayores |
| `minor` | number | Conteo de hallazgos menores |
| `advisory` | number | Conteo de advertencias |
| `total` | number | Total de hallazgos |
| `findings` | array | Lista detallada de hallazgos |
| `publish_decision` | object | Decisión sobre publicación |
| `linted_at` | string | Timestamp ISO 8601 |
| `lint_version` | string | Versión del motor de lint |

### PublishDecision

| Campo | Tipo | Descripción |
|---|---|---|
| `allowed` | boolean | ¿Se permite publicar? |
| `confirm_required` | boolean | ¿Requiere confirmación humana adicional? |
| `reason` | string | Explicación legible |

## Severidades

| Código | Significado | Bloquea publicación |
|---|---|---|
| `critical` | Error de encoding o texto roto | Sí |
| `major` | Terminología incorrecta, calcos, Oxford | Sí (si > 3) |
| `minor` | Falsa fluidez, RAE | No |
| `advisory` | Registro interno para cliente | No |

## Códigos de estado HTTP

| Código | Significado |
|---|---|
| 200 | Lint ejecutado correctamente |
| 400 | Texto vacío o audience inválido |
| 422 | Excepción con razón vacía |
| 500 | Error interno del motor de lint |

## Ejemplo: caso limpio

Request:
```json
{
  "text": "El diagnostico empresarial se realizó con ARHIAX Dx Pro.",
  "audience": "client"
}
```

Response:
```json
{
  "score": 92,
  "critical": 0,
  "major": 0,
  "minor": 1,
  "advisory": 0,
  "total": 1,
  "findings": [
    {
      "rule_id": "GC-06-RAE-001",
      "severity": "minor",
      "message": "Mes con mayúscula inicial",
      "detected_text": "diagnostico",
      "suggestion": "Los meses se escriben con minúscula inicial en español.",
      "rationale": "La RAE establece minúscula inicial para meses y días de la semana.",
      "excepted": false
    }
  ],
  "publish_decision": {
    "allowed": true
  }
}
```

## Ejemplo: caso bloqueado

> **Nota:** El texto de ejemplo contiene caracteres mojibake intencionales (Ã, Â, ¿) para demostrar la detección de encoding roto.

Request:
```json
{
  "text": "La aprobaciÃ³n todavÃ­a no estÃ¡ lista.",
  "audience": "client"
}
```

Response:
```json
{
  "score": 75,
  "critical": 1,
  "total": 1,
  "findings": [
    {
      "rule_id": "GC-01-ENCODING-001",
      "severity": "critical",
      "detected_text": "Ã³",
      "suggestion": "Revise encoding UTF-8, tildes, ñ y signos de apertura.",
      "rationale": "El texto contiene caracteres incompatibles con una entrega canónica ARHIAX.",
      "excepted": false
    }
  ],
  "publish_decision": {
    "allowed": false,
    "reason": "Hallazgos críticos pendientes. Corrija antes de publicar."
  }
}
```

## Modelo de excepción

```json
{
  "finding_id": "uuid",
  "rule_id": "GC-02-TERM-001",
  "detected_text": "Arhiax",
  "reason": "El nombre del producto aparece en contexto histórico",
  "reviewer": "consultor@sinergia.com",
  "created_at": "2026-06-23T14:00:00.000Z"
}
```

### Reglas de validación de excepciones

1. `reason` no puede estar vacío.
2. `rule_id` debe existir en el catálogo de reglas.
3. `reviewer` debe identificarse (nombre o email).
4. Una excepción solo exime el hallazgo específico (rule_id + detected_text).
5. Las excepciones se registran en el audit pack del expediente.

## Relación con HIL (Human-in-the-Loop)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Lint API   │────>│  Publish     │────>│  Backend    │
│  /grammar/  │     │  Decision    │     │  Approval   │
│  lint       │     │  (frontend)  │     │  /approval  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                    │
       │  findings          │  allowed?          │  persist
       │  score             │  confirm?          │  + audit
       ▼                    ▼                    ▼
   GrammarReport      HIL Panel             CaseRecord
```

- El frontend ejecuta lint antes de permitir Publicar.
- Si hay críticos, Publicar se deshabilita.
- Si hay mayores, Publicar requiere confirmación.
- Las excepciones se envían al backend con la acción de publicación.
