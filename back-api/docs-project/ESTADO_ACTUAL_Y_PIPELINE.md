# ARHIAX Dx — Estado Actual y Pipeline Completo

## 1. Qué dejó construido el autor

### Resumen ejecutivo

El autor entregó el **motor de gobernanza y control** del agente de diagnóstico organizacional. Es un artefacto de producción completo en su capa de decisión, pero sin ejecución real del pipeline diagnóstico ni interfaz de usuario. La metáfora correcta: construyó el sistema nervioso central y el sistema inmune, pero no los músculos ni la piel.

---

### Stack tecnológico actual

| Capa | Tecnología |
|---|---|
| Runtime | Python 3.11+ |
| API | FastAPI 0.115+ |
| Servidor | Uvicorn |
| Modelos de datos | Pydantic v2 |
| Criptografía | cryptography (Ed25519) |
| Build | setuptools + wheel |
| Tests | pytest + httpx |
| Contenedores | Docker + Docker Compose |
| Orquestación | Kubernetes (manifests de ejemplo) |

---

### Estructura del repositorio

```
arhiax-dx/
├── src/arhiax_dx/
│   ├── main.py                    # FastAPI app factory + 6 endpoints
│   ├── config.py                  # Settings via env vars
│   ├── models.py                  # Pydantic models (request/response/decision)
│   ├── specs.py                   # Loader de specs JSON con lru_cache
│   ├── installation.py            # CLI: arhiax-dx-validate
│   ├── installation_assets.py     # CLI: arhiax-dx-install-bootstrap
│   └── services/
│       ├── governance.py          # Motor de 18 reglas de gobernanza
│       ├── diagnostics.py         # Orquestador end-to-end
│       ├── evidence.py            # Ledger append-only con hash encadenado
│       ├── provenance.py          # Firma Ed25519 de certificados
│       └── tool_registry.py       # Carga y expone los 8 specs JSON
├── specs/                         # Contrato de gobernanza versionado (v2026.04)
│   ├── agent_identity.json        # Identidad, boundary, ventana operativa
│   ├── tool_catalog.json          # 24 herramientas declaradas
│   ├── data_scopes.json           # 7 scopes de datos con retención
│   ├── operation_catalog.json     # 5 operaciones permitidas
│   ├── autonomy_profile.json      # Niveles A0-A2 y requisitos de promoción
│   ├── policy_matrix.json         # 5 bundles DX-B01 a DX-B05
│   ├── model_strategy.json        # Routing Gemini/Anthropic por etapa
│   └── bbr_baseline.json          # 7 métricas de comportamiento base
├── policies/bundles/              # Políticas Rego (OPA-compatible)
│   ├── governance.rego
│   └── risk_controls.rego
├── tests/                         # 6 archivos de test
├── docs/                          # Documentación técnica y audit pack
├── infra/k8s/                     # Manifests Kubernetes de ejemplo
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

---

### Endpoints expuestos

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/healthz` | Liveness check |
| GET | `/readyz` | Readiness con metadata de runtime |
| GET | `/v1/compliance/posture` | Contrato de gobernanza completo para auditoría |
| GET | `/v1/compliance/install-readiness` | Checklist de bindings de instalación |
| GET | `/v1/compliance/install-blueprint` | Manifiesto de bindings para el cliente |
| POST | `/v1/diagnostics/evaluate` | Evaluación gobernada — endpoint principal |

---

### Las 18 reglas de gobernanza implementadas

**Preflight (13 reglas — se evalúan antes de construir el plan):**

| ID | Descripción | Resultado si falla |
|---|---|---|
| DX-G1-IDENTITY | client_id y legal_name presentes | DENY |
| DX-G2-BOUNDARY | boundary = "boundary-diagnostico-org" | DENY |
| DX-MANDATE-001 | size_org requerido | DENY |
| DX-TOOLS-001 | Herramientas declaradas en catálogo | DENY |
| DX-OPS-001 | Operaciones declaradas y habilitadas | DENY |
| DX-DATA-001 | Data scopes declarados | DENY |
| DX-AUTONOMY-001 | Nivel de autonomía válido (A0-A4) | DENY |
| DX-AUTONOMY-002 | Cambio de autonomía requiere métricas + aprobación | DENY |
| DX-TOOLS-002 | Herramientas caben bajo nivel de autonomía | DENY |
| DX-DATA-002 | Datos de respondentes anónimos | DENY |
| DX-RISK-001 | Sin patrones de inyección de prompts | DENY |
| DX-OPS-002 | Dentro de ventana operativa (Lun-Vie 7-22 Bogotá) | DENY |
| DX-G5-EVIDENCE | Evidencia siempre activa | PASS (siempre) |

**Execution (5 reglas — se evalúan después del preflight):**

| ID | Descripción | Resultado si falla |
|---|---|---|
| DX-QA-001 | docx_generator requiere QA ≥ 85 | DENY |
| DX-HIC-001 | Publicación siempre escala a humano | ESCALATE_TO_HUMAN |
| DX-HIC-002 | delta_sigma > 2 escala a humano | ESCALATE_TO_HUMAN |
| DX-RISK-002 | irr_alpha < 0.70 escala a humano | ESCALATE_TO_HUMAN |
| DX-DATA-003 | Retención máxima 30 días | DENY |

---

### Las 24 herramientas del catálogo (solo declaradas, no implementadas)

| Herramienta | Fase | Severidad | Pipeline default |
|---|---|---|---|
| g01_receptor | intake | MEDIUM | ✓ |
| g02_configurador | intake | MEDIUM | ✓ |
| g03_cienciometro | research | MEDIUM | ✓ |
| g04_cartografo | mapping | MEDIUM | ✓ |
| g05_brechas | mapping | MEDIUM | ✓ |
| g06_bpmn_architect | design | HIGH | ✓ |
| g07_cuellos | quantification | HIGH | ✓ |
| g08_optimizador | design | HIGH | ✓ |
| g09a_preguntas | survey_design | MEDIUM | ✓ |
| g09b_ramificacion | survey_design | MEDIUM | ✓ |
| g09c_validacion | survey_design | MEDIUM | ✓ |
| g10a_scoring | analysis | HIGH | ✓ |
| g10b_psicometria | analysis | HIGH | ✓ |
| g11a_bayesiano | analysis | HIGH | ✓ |
| g11b_nlp | analysis | MEDIUM | ✗ |
| g12_hallazgos | synthesis | HIGH | ✓ |
| g13_redactor | reporting | HIGH | ✓ |
| g14_qa_control | qa | CRITICAL | ✓ |
| docx_generator | rendering | CRITICAL | ✗ |
| academic_search | research | MEDIUM | ✗ |
| web_search | research | MEDIUM | ✗ |
| irr_calculator | analysis | HIGH | ✓ |
| bpmn_generator | design | HIGH | ✗ |
| scoring_engine | analysis | HIGH | ✗ |

---

### Flujo de una solicitud (estado actual)

```
POST /v1/diagnostics/evaluate
  │
  ├─ GovernanceEngine.evaluate_preflight()   ← 13 reglas
  │    └─ Si DENY → ledger + certificado + respuesta de negación
  │
  ├─ DiagnosticService._build_execution_plan()
  │    └─ PlannedTools + active_model_routes + human_gates
  │
  ├─ GovernanceEngine.evaluate_execution()   ← 5 reglas
  │
  ├─ EvidenceLedger.append()                 ← hash encadenado
  │
  ├─ ProvenanceSigner.issue_certificate()    ← Ed25519
  │
  └─ DiagnosticResponse
       ├─ decision: ALLOW / DENY / ESCALATE_TO_HUMAN / ALLOW_WITH_HIC_NOTIFICATION
       ├─ execution_plan (planned_tools, active_models, human_gates)
       ├─ certificate (firmado)
       ├─ rule_results (18 reglas con outcome)
       └─ human_review_required: bool
```

---

### Routing de modelos (declarado, no ejecutado)

| Etapa | Herramientas | Primario | Fallback | Max tokens | Temperatura |
|---|---|---|---|---|---|
| survey_design | g09a, g09b, g09c | Gemini | Anthropic | 16,000 | 0.3 |
| analysis | g10a, g10b, g11a, g11b, irr_calculator, scoring_engine | Gemini | Anthropic | 24,000 | 0.2 |
| design | g06, g07, g08, bpmn_generator | Gemini | Anthropic | 28,000 | 0.2 |
| reporting | g12, g13, g14, docx_generator | Gemini | Anthropic | 32,000 | 0.1 |
| research | g03, academic_search, web_search | Gemini | Anthropic | 22,000 | 0.2 |

---

### Bindings requeridos en instalación

| Binding | Requerido | Propietario |
|---|---|---|
| ed25519_signing | Sí | Seguridad del cliente |
| gemini_primary | Sí | Plataforma del cliente |
| anthropic_fallback | Sí | Plataforma del cliente |
| hic_webhook | Sí | Operaciones del cliente |
| observability_stack | Sí | Plataforma del cliente |
| whatsapp_critical | No | Operaciones del cliente |
| docx_renderer | No | Plataforma del cliente |
| bpmn_renderer | No | Plataforma del cliente |

---

### Variables de entorno

```env
ARHIAX_DX_PROJECT_NAME=ARHIAX Dx Agent
ARHIAX_DX_AGENT_VERSION=5.1.0
ARHIAX_DX_ENV=development
ARHIAX_DX_MODE=mock
ARHIAX_DX_HOST=0.0.0.0
ARHIAX_DX_PORT=8088
ARHIAX_DX_LEDGER_PATH=var/evidence-ledger.jsonl
ARHIAX_DX_INSTALL_MANIFEST_PATH=var/install/client-install-manifest.json
ARHIAX_DX_PUBLIC_KEY_ID=dx-local-ed25519
ARHIAX_DX_ED25519_PRIVATE_KEY=           # base64 de clave Ed25519
ARHIAX_DX_GOVERNANCE_SPEC_VERSION=2026.04
ARHIAX_DX_POLICY_BUNDLE_VERSION=2026.04
ARHIAX_DX_TOOL_CATALOG_VERSION=2026.04
ARHIAX_DX_SPECS_PATH=specs/
ARHIAX_DX_OPERATING_TIMEZONE=America/Bogota
ARHIAX_DX_OPERATING_WINDOW_START=7
ARHIAX_DX_OPERATING_WINDOW_END=22
GEMINI_API_KEY=                           # inyectado en instalación
ANTHROPIC_API_KEY=                        # inyectado en instalación
HIC_WEBHOOK_URL=                          # inyectado en instalación
WHATSAPP_BUSINESS_WEBHOOK=               # opcional
ARHIAX_DX_POLICY_BUNDLES=DX-B01,DX-B02,DX-B03,DX-B04,DX-B05
```

---

### Cobertura de tests

| Archivo | Qué cubre |
|---|---|
| test_api.py | healthz, compliance_posture, evaluate ALLOW, escalación por publicación |
| test_governance.py | 7 casos: undeclared tool, prompt injection, raw data, retención, publicación, QA bajo, autonomía A2 |
| test_installation.py | readiness report, bindings configurados |
| test_installation_assets.py | generación de manifiesto, bindings opcionales |
| test_specs.py | carga de specs, model routes para reporting |
| conftest.py | fixtures: client, settings, request_payload |

---

### Lo que el autor dejó explícitamente fuera

Según la documentación y el código:

1. **Ejecución real de las 24 herramientas** — son referencias en el catálogo, no implementaciones
2. **Llamadas reales a Gemini/Anthropic** — el routing está declarado pero no ejecutado
3. **Interfaz de usuario** — cero HTML, cero frontend
4. **Flujo de aprobación humana** — el webhook existe como placeholder, sin UI de revisión
5. **Generación real de DOCX** — docx_generator está en el catálogo pero no implementado
6. **Renderizado BPMN** — bpmn_generator declarado, no implementado
7. **Base de datos** — solo ledger JSONL en disco, sin persistencia estructurada
8. **Infraestructura del cliente** — secrets, KMS, observabilidad, red

---

## 2. Pipeline completo — Lo que hay que construir

### Visión general

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARHIAX Dx Platform                        │
│                                                                   │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   Frontend   │◄──►│   Backend API    │◄──►│  Worker Pool  │  │
│  │  (Next.js)   │    │   (FastAPI)      │    │  (Celery)     │  │
│  └──────────────┘    └──────────────────┘    └───────────────┘  │
│         │                    │                       │           │
│         │              ┌─────┴──────┐         ┌─────┴──────┐   │
│         │              │ PostgreSQL  │         │   Redis    │   │
│         │              │ (estado)   │         │  (queue)   │   │
│         │              └────────────┘         └────────────┘   │
│         │                                                        │
│         └──── WebSocket ──── progreso en tiempo real            │
└─────────────────────────────────────────────────────────────────┘
```

---

### Stack del pipeline completo

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | Next.js 14 + TypeScript | App Router, SSR, ecosistema maduro |
| UI Components | shadcn/ui + Tailwind CSS | Componentes accesibles, sin lock-in |
| Formularios | React Hook Form + Zod | Validación tipada, mismos schemas que el backend |
| Estado servidor | TanStack Query | Cache, revalidación, optimistic updates |
| Tiempo real | WebSocket (FastAPI nativo) | Progreso del pipeline sin polling |
| Backend | FastAPI (existente, extendido) | Mantiene el motor de gobernanza intacto |
| Tareas async | Celery + Redis | Pipeline puede tardar 5-15 min por etapa |
| Base de datos | PostgreSQL + SQLAlchemy | Persistencia de diagnósticos, aprobaciones, usuarios |
| Migraciones | Alembic | Control de versiones del schema |
| Ejecución LLM | google-generativeai + anthropic | Gemini primario, Anthropic fallback |
| Generación DOCX | python-docx | Reporte ejecutivo en Word |
| Generación BPMN | bpmn-python o XML directo | Diagramas de proceso |
| Auth | JWT + bcrypt | Sesiones de usuario, roles |

---

### Pantallas del frontend

#### 1. Dashboard principal
- Lista de diagnósticos activos, en revisión y completados
- Métricas BBR en tiempo real (QA score, IRR alpha, ratio escalado)
- Accesos rápidos: nuevo diagnóstico, revisiones pendientes

#### 2. Nuevo diagnóstico — Formulario de mandato
```
Paso 1: Datos del cliente
  - Nombre de la organización
  - Nombre legal
  - Dominio (ej: logística, manufactura, servicios)
  - Subproceso a diagnosticar
  - Tamaño de la organización (número de empleados)
  - Objetivo del diagnóstico
  - Confidencialidad

Paso 2: Configuración del pipeline
  - Selección de herramientas (checkbox con descripción de cada una)
  - Operaciones requeridas (pre-seleccionadas según herramientas)
  - Data scopes (pre-seleccionados según herramientas)
  - Nivel de autonomía (A1 por defecto)
  - Perfil de procesamiento:
    - ¿Generar certificado? (sí por defecto)
    - ¿Publicar reporte? (requiere aprobación humana)
    - Días de retención (máx 30)

Paso 3: Revisión y envío
  - Resumen del mandato
  - Herramientas seleccionadas con sus fases
  - Advertencias de gobernanza (si aplica)
  - Botón: Evaluar y ejecutar
```

#### 3. Evaluación de gobernanza (tiempo real)
- Resultado preflight regla por regla (18 indicadores verde/rojo)
- Decisión final: ALLOW / DENY / ESCALATE
- Si DENY: razones específicas con ID de regla
- Si ESCALATE: notificación al revisor + estado "en espera"
- Plan de ejecución: herramientas planificadas con fase y modelo asignado

#### 4. Ejecución del pipeline (tiempo real vía WebSocket)
```
[intake]        g01_receptor ████████████ ✓
                g02_configurador ████████ ✓
[research]      g03_cienciometro ████░░░░ ⟳ ejecutando...
[mapping]       g04_cartografo ░░░░░░░░ pendiente
[mapping]       g05_brechas ░░░░░░░░ pendiente
...
```
- Log de cada herramienta con tokens usados y modelo invocado
- Tiempo transcurrido por etapa
- Indicador de modelo activo (Gemini / Anthropic fallback)

#### 5. Cola de revisión humana
- Lista de diagnósticos que requieren aprobación
- Filtros: publicación pendiente, IRR bajo, gap crítico, promoción A2
- Vista del borrador del reporte
- Botones: Aprobar / Rechazar / Solicitar revisión
- Campo de comentario obligatorio al rechazar
- Firma del revisor (nombre + timestamp)

#### 6. Resultados del diagnóstico
- Reporte ejecutivo renderizado en pantalla
- Descarga DOCX (si QA ≥ 85 y aprobado)
- Diagrama BPMN del proceso AS-IS y TO-BE
- Certificado firmado (JSON + preview)
- Entrada del ledger de evidencia
- Historial de reglas evaluadas

#### 7. Panel de gobernanza / auditoría
- Ledger de evidencia completo (paginado)
- Filtros por cliente, decisión, fecha
- Verificación de integridad del hash encadenado
- Postura de compliance (`/v1/compliance/posture` visualizado)
- Estado de bindings de instalación

---

### Nuevos endpoints del backend

#### Autenticación
```
POST /auth/login
POST /auth/logout
GET  /auth/me
```

#### Diagnósticos (estado persistido)
```
POST   /v1/diagnostics/submit          # Crea diagnóstico y lanza tarea Celery
GET    /v1/diagnostics                 # Lista con paginación y filtros
GET    /v1/diagnostics/{id}            # Detalle completo
GET    /v1/diagnostics/{id}/status     # Estado actual de la tarea
WS     /v1/diagnostics/{id}/stream     # WebSocket de progreso en tiempo real
GET    /v1/diagnostics/{id}/report     # Reporte generado
GET    /v1/diagnostics/{id}/certificate # Certificado firmado
GET    /v1/diagnostics/{id}/bpmn       # Diagrama BPMN
```

#### Revisiones humanas
```
GET    /v1/reviews/pending             # Cola de aprobaciones pendientes
GET    /v1/reviews/{id}                # Detalle de revisión
POST   /v1/reviews/{id}/approve        # Aprobar con comentario
POST   /v1/reviews/{id}/reject         # Rechazar con razón
```

#### Ledger y auditoría
```
GET    /v1/ledger                      # Entradas paginadas
GET    /v1/ledger/verify               # Verificación de integridad
```

---

### Implementación de las 24 herramientas

Cada herramienta se implementa como una función async que:
1. Recibe el contexto del diagnóstico
2. Construye el prompt según la etapa
3. Llama a Gemini (o Anthropic como fallback)
4. Parsea y valida la respuesta
5. Retorna el resultado estructurado

**Ejemplo de flujo por etapa:**

```
intake:
  g01_receptor   → captura mandato, inicializa sesión gobernada
  g02_configurador → construye configuración de dominio y benchmarks

research:
  g03_cienciometro → mapea literatura académica relevante
  academic_search  → consulta bases de datos académicas
  web_search       → enriquece contexto sectorial

mapping:
  g04_cartografo → mapas de proceso y capacidad organizacional
  g05_brechas    → hipótesis de brechas y gaps baseline

design:
  g06_bpmn_architect → arquitectura AS-IS en BPMN
  g07_cuellos        → cuantificación de cuellos de botella
  g08_optimizador    → opciones TO-BE y escenarios ROI
  bpmn_generator     → renderiza assets BPMN

survey_design:
  g09a_preguntas   → banco de preguntas por rol
  g09b_ramificacion → lógica de ramificación adaptativa
  g09c_validacion  → validaciones de integridad

analysis:
  g10a_scoring     → matrices de scoring por rol
  g10b_psicometria → confiabilidad y alpha de Cronbach
  g11a_bayesiano   → análisis Bayesiano de hipótesis
  g11b_nlp         → síntesis NLP de texto abierto
  irr_calculator   → confiabilidad inter-evaluador
  scoring_engine   → normalización y agregación

synthesis:
  g12_hallazgos → hallazgos consolidados y problem statements

reporting:
  g13_redactor    → narrativa ejecutiva para revisión humana
  g14_qa_control  → QA y gobernanza antes de renderizado
  docx_generator  → Word final tras aprobación QA
```

---

### Modelo de datos PostgreSQL

```sql
-- Diagnósticos
diagnostics (
  id UUID PRIMARY KEY,
  request_id UUID UNIQUE,
  client_id VARCHAR,
  legal_name VARCHAR,
  organization_name VARCHAR,
  domain VARCHAR,
  subprocess VARCHAR,
  objective TEXT,
  size_org VARCHAR,
  status VARCHAR,          -- pending | running | awaiting_review | completed | denied | failed
  decision VARCHAR,        -- ALLOW | DENY | ESCALATE_TO_HUMAN | ALLOW_WITH_HIC_NOTIFICATION
  autonomy_level VARCHAR,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
)

-- Resultados por etapa del pipeline
pipeline_stages (
  id UUID PRIMARY KEY,
  diagnostic_id UUID REFERENCES diagnostics,
  tool_name VARCHAR,
  phase VARCHAR,
  status VARCHAR,          -- pending | running | completed | failed
  model_used VARCHAR,
  tokens_used INTEGER,
  latency_ms INTEGER,
  output JSONB,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
)

-- Revisiones humanas
human_reviews (
  id UUID PRIMARY KEY,
  diagnostic_id UUID REFERENCES diagnostics,
  review_type VARCHAR,     -- publication | irr_followup | critical_gap | autonomy_promotion
  status VARCHAR,          -- pending | approved | rejected
  reviewer_id UUID,
  reviewer_name VARCHAR,
  comment TEXT,
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ
)

-- Reportes generados
reports (
  id UUID PRIMARY KEY,
  diagnostic_id UUID REFERENCES diagnostics,
  qa_score FLOAT,
  irr_alpha FLOAT,
  delta_sigma FLOAT,
  narrative TEXT,
  findings JSONB,
  bpmn_xml TEXT,
  docx_path VARCHAR,
  published BOOLEAN DEFAULT FALSE,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ
)

-- Usuarios
users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE,
  name VARCHAR,
  role VARCHAR,            -- operator | reviewer | admin
  hashed_password VARCHAR,
  created_at TIMESTAMPTZ
)
```

---

### Flujo completo del pipeline

```
Usuario llena formulario
  │
  ▼
POST /v1/diagnostics/submit
  │
  ├─ Validación Zod en frontend
  ├─ GovernanceEngine.evaluate_preflight() [18 reglas]
  │
  ├─ Si DENY → mostrar razones en UI, fin
  │
  ├─ Si ESCALATE → crear human_review, notificar revisor, UI muestra "en espera"
  │
  └─ Si ALLOW → guardar en PostgreSQL + lanzar tarea Celery
                │
                ▼
         Worker Celery ejecuta pipeline:
           Para cada herramienta en orden:
             1. Construir prompt con contexto acumulado
             2. Llamar Gemini (o Anthropic si falla)
             3. Parsear respuesta
             4. Guardar en pipeline_stages
             5. Emitir evento WebSocket al frontend
             6. Continuar con siguiente herramienta
                │
                ▼
         g14_qa_control evalúa calidad
           ├─ QA < 85 → DENY docx_generator, notificar
           └─ QA ≥ 85 → continuar
                │
                ▼
         g13_redactor genera narrativa ejecutiva
                │
                ▼
         Si publish_report = true:
           → Crear human_review de tipo "publication"
           → Notificar revisor vía webhook HIC
           → UI muestra "esperando aprobación de publicación"
           → Revisor aprueba/rechaza en panel de revisión
                │
                ▼
         Si aprobado:
           → docx_generator genera Word
           → Guardar en reports
           → ProvenanceSigner.issue_certificate()
           → EvidenceLedger.append()
           → Notificar al usuario: diagnóstico completado
```

---

### Orden de construcción recomendado

#### Fase 1 — Base de datos y auth (2-3 días)
- Modelos SQLAlchemy + Alembic
- Endpoints de autenticación JWT
- Migración inicial

#### Fase 2 — Ejecución del pipeline (4-5 días)
- Celery + Redis
- Implementación de las 24 herramientas (llamadas reales a Gemini/Anthropic)
- WebSocket de progreso
- Nuevos endpoints de diagnóstico

#### Fase 3 — Flujo de revisión humana (2 días)
- Endpoints de revisión
- Notificación vía webhook HIC
- Lógica de aprobación/rechazo

#### Fase 4 — Generación de documentos (2 días)
- docx_generator con python-docx
- bpmn_generator con XML
- Endpoint de descarga

#### Fase 5 — Frontend (5-7 días)
- Setup Next.js + shadcn/ui
- Formulario de mandato (multi-paso)
- Vista de evaluación de gobernanza
- Vista de progreso del pipeline (WebSocket)
- Panel de revisión humana
- Vista de resultados y descarga
- Panel de auditoría / ledger

#### Fase 6 — Integración y hardening (2 días)
- Tests de integración end-to-end
- Variables de entorno de producción
- Docker Compose actualizado con todos los servicios
- Kubernetes manifests actualizados

---

### Lo que NO se toca del código existente

El motor de gobernanza se mantiene intacto:

- `services/governance.py` — sin cambios
- `services/evidence.py` — sin cambios
- `services/provenance.py` — sin cambios
- `services/tool_registry.py` — sin cambios
- `specs/*.json` — sin cambios
- `models.py` — se extiende, no se modifica
- `config.py` — se extiende con nuevas vars

El principio del autor se respeta: la lógica de gobernanza es el núcleo estable. Todo lo nuevo se construye encima.

---

*Documento generado el 2026-04-24. Refleja el estado del repositorio en esa fecha.*
