# ARHIAX Dx — Documentación Completa de la Plataforma

**Sinergia Consulting Group · v5.1 · Confidencial — Uso Estratégico**

---

## 1. Qué es ARHIAX Dx

ARHIAX Dx es una plataforma de diagnóstico organizacional gobernado. Permite a Sinergia Consulting automatizar el proceso completo de diagnóstico de una empresa cliente — desde la recepción del mandato hasta la entrega del reporte ejecutivo — usando una cadena de 18 agentes de inteligencia artificial especializados.

**No es un chatbot.** Es una línea de ensamblaje inteligente donde cada agente hace una tarea específica y pasa el resultado al siguiente, acumulando contexto hasta producir un diagnóstico de calidad consultora.

**El sistema garantiza:**
- Que ningún agente haga algo fuera de su alcance declarado
- Que los datos de los encuestados sean siempre anónimos
- Que el reporte final nunca se publique sin aprobación humana
- Que cada decisión quede registrada con firma digital

---

## 2. Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                     ARHIAX Dx Platform                          │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │   Frontend   │◄──►│  Pipeline API    │◄──►│    Worker    │  │
│  │  (Next.js)   │    │  (FastAPI :8000) │    │  (Python)    │  │
│  │  :3000       │    └──────────────────┘    └──────────────┘  │
│  └──────────────┘             │                      │          │
│                         ┌─────┴──────┐               │          │
│                         │ PostgreSQL  │               │          │
│                         │  (estado)  │               │          │
│                         └────────────┘               │          │
│                                                       ▼          │
│                         ┌──────────────────────────────────┐    │
│                         │  Governance Engine (FastAPI :8088)│    │
│                         │  Motor de 18 reglas de gobernanza │    │
│                         │  Ledger append-only (Ed25519)     │    │
│                         └──────────────────────────────────┘    │
│                                                                  │
│                         ┌──────────────────────────────────┐    │
│                         │  Gemini 2.5 Pro/Flash (Google)   │    │
│                         │  18 agentes especializados        │    │
│                         └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes

| Componente | Tecnología | Puerto | Función |
|---|---|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind | 3000 | Interfaz de usuario |
| Pipeline API | FastAPI + SQLAlchemy | 8000 | Orquestación, auth, persistencia |
| Worker | Python asyncio | — | Ejecuta el pipeline en background |
| Governance Engine | FastAPI + Pydantic | 8088 | Motor de reglas y gobernanza |
| Base de datos | PostgreSQL | 5432 | Estado de diagnósticos y usuarios |
| Redis | Redis | 6379 | Cola de tareas (opcional) |

---

## 3. Cómo funciona el pipeline

### El flujo completo de un diagnóstico

```
Consultor llena el formulario (3 pasos)
        ↓
Sistema evalúa 18 reglas de gobernanza
        ↓
Si pasa → Worker ejecuta los agentes en secuencia
        ↓
Cada agente llama a Gemini con un prompt especializado
        ↓
El output de cada agente alimenta al siguiente
        ↓
g14_qa_control evalúa la calidad (mínimo 85/100)
        ↓
Si publish_report = true → Reviewer debe aprobar
        ↓
Diagnóstico completado → reporte Word disponible
```

### Las 18 reglas de gobernanza

Antes de ejecutar cualquier diagnóstico, el sistema evalúa 18 reglas divididas en dos fases:

**Preflight (13 reglas — antes de ejecutar):**

| Regla | Qué verifica | Si falla |
|---|---|---|
| DX-G1-IDENTITY | Cliente identificado con ID y nombre legal | DENY |
| DX-G2-BOUNDARY | Boundary = "boundary-diagnostico-org" | DENY |
| DX-MANDATE-001 | Tamaño de organización presente | DENY |
| DX-TOOLS-001 | Herramientas declaradas en el catálogo | DENY |
| DX-OPS-001 | Operaciones declaradas y habilitadas | DENY |
| DX-DATA-001 | Data scopes declarados | DENY |
| DX-AUTONOMY-001 | Nivel de autonomía válido | DENY |
| DX-AUTONOMY-002 | Cambio de autonomía con métricas + aprobación | DENY |
| DX-TOOLS-002 | Herramientas dentro del nivel de autonomía | DENY |
| DX-DATA-002 | Datos de respondentes anónimos | DENY |
| DX-RISK-001 | Sin patrones de inyección de prompts | DENY |
| DX-OPS-002 | Dentro de ventana operativa (Lun-Vie 7-22 Bogotá) | DENY |
| DX-G5-EVIDENCE | Evidencia siempre activa | PASS siempre |

**Execution (5 reglas — durante la ejecución):**

| Regla | Qué verifica | Si falla |
|---|---|---|
| DX-QA-001 | QA ≥ 85 para generar Word | DENY |
| DX-HIC-001 | Publicación siempre requiere humano | ESCALATE |
| DX-HIC-002 | Brecha de percepción delta_sigma > 2 | ESCALATE |
| DX-RISK-002 | IRR alpha < 0.70 | ESCALATE |
| DX-DATA-003 | Retención máxima 30 días | DENY |

### Los 18 agentes del pipeline

Cada agente tiene un modelo Gemini asignado según su función:

| Agente | Nombre | Modelo | Función |
|---|---|---|---|
| G01 | Receptor | gemini-2.5-flash | Parsea el mandato, inicializa la sesión |
| G02 | Configurador | gemini-2.5-flash | Configura dominio, benchmarks, KPIs |
| G03 | Cienciómetro | gemini-2.5-flash | Mapea literatura académica relevante |
| G04 | Cartógrafo | gemini-2.5-flash | Mapea praxis empresarial y casos del sector |
| G05 | Brechas | gemini-2.5-flash | Detecta brechas AS-IS vs benchmark |
| G06 | BPMN Architect | gemini-2.5-flash | Diseña proceso AS-IS (15-20 actividades) |
| G07 | Cuellos | gemini-2.5-flash | Cuantifica cuellos de botella con costo |
| G08 | Optimizador | gemini-2.5-flash | Diseña TO-BE con ROI y payback |
| G09a | Preguntas | gemini-2.5-flash | Diseña encuesta Multi-Rater (40-60 preguntas, técnica CIT) |
| G09b | Ramificación | gemini-2.5-flash | Lógica adaptativa por rol |
| G09c | Validación | gemini-2.5-flash | Calcula IRR (Krippendorff Alpha, mín 0.70) |
| G10a | Scoring | gemini-2.5-flash | Matrices de scoring 6 capas |
| G10b | Psicometría | gemini-2.5-flash | Alpha de Cronbach, fiabilidad |
| G11a | Bayesiano | **gemini-2.5-pro** (temp 0.1) | Actualiza 12 hipótesis con evidencia (posterior ≥ 0.90) |
| G11b | NLP | gemini-2.5-flash | Análisis cualitativo de respuestas abiertas |
| G12 | Hallazgos | gemini-2.5-flash | Sintetiza FindingsMatrix priorizada |
| G13 | Redactor | **gemini-2.5-pro** (temp 0.7) | Redacta informe ejecutivo C-suite con roadmap 90/180/365 |
| G14 | QA Control | **gemini-2.5-pro** (temp 0.2) | QA automatizado — mínimo 85/100 para aprobar |

**Nota sobre autonomía:**
- G01–G10b requieren **A1** (nivel inicial)
- G11a, G12, G13, G14 requieren **A2** (se ejecutan después del gate A1)

---

## 4. Los tres perfiles de usuario

### Admin — El director de la práctica

**Quién es:** `director-sinergia-001` en el sistema. El responsable final ante la junta.

**Qué puede hacer:**
- Todo lo que puede hacer un Consultor y un Revisor
- Crear, editar y eliminar usuarios del equipo
- Ver métricas BBR (comportamiento del sistema)
- Aprobar la promoción de autonomía A1 → A2
- Recibir escalados críticos (inyección de prompts, datos no anónimos)
- Ver el panel de administración completo

**Cuándo actúa:**
- Cuando hay un incidente de seguridad (CRITICAL)
- Cuando el sistema solicita subir a autonomía A2
- Para onboardear nuevos consultores al equipo

---

### Reviewer — El consultor senior

**Quién es:** `consultor-senior-001` en el sistema. El que firma antes de que salga al cliente.

**Qué puede hacer:**
- Ver todos los diagnósticos
- Aprobar o rechazar diagnósticos escalados
- Ver el borrador del reporte antes de aprobarlo
- Su decisión queda registrada en el certificado de gobernanza

**Cuándo actúa — los 4 tipos de escalado:**

| Tipo | Cuándo ocurre | SLA |
|---|---|---|
| Publicación de reporte | Siempre que se quiera publicar al cliente | 4h |
| IRR bajo | Cuando alpha < 0.70 (encuesta poco confiable) | 1h |
| Brecha crítica | Cuando delta_sigma > 2 (directivos vs operativos muy desalineados) | 4h |
| Promoción A2 | Cuando el sistema solicita más autonomía | 24h |

**Lo que NO puede hacer:**
- Crear usuarios
- Ver métricas BBR
- Cambiar configuración del sistema

---

### Operator — El consultor junior / analista

**Quién es:** El que trabaja día a día con los clientes de Sinergia.

**Qué puede hacer:**
- Crear nuevos diagnósticos (formulario de 3 pasos)
- Ver el progreso del pipeline en tiempo real
- Ver los resultados: hallazgos, recomendaciones, roadmap
- Descargar el reporte Word
- Ver el historial de diagnósticos por cliente

**Lo que NO puede hacer:**
- Aprobar o rechazar diagnósticos
- Crear usuarios
- Ver administración

---

## 5. El formulario de nuevo diagnóstico (3 pasos)

### Paso 1 — Datos del cliente

Recoge toda la información necesaria para que los agentes tengan contexto:

**Identidad de la empresa:**
- Nombre comercial y razón social
- NIT
- Sector económico (lista de 13 sectores)
- País y ciudad (listas desplegables — Colombia tiene 26 ciudades)
- Número de empleados
- Años de operación

**Contacto principal:**
- Nombre, cargo, email, teléfono

**El problema:**
- Área a diagnosticar (lista de 11 áreas)
- Síntoma principal (texto libre — mínimo 20 caracteres)
- Hace cuánto viene el problema
- Qué han intentado antes (opcional)
- Qué esperan obtener

**Alcance:**
- Cuántas personas participarán en la encuesta
- Fecha límite para el reporte (opcional)
- Nivel de confidencialidad

### Paso 2 — Tipo de diagnóstico

El consultor elige la profundidad. El sistema activa los módulos automáticamente:

| Opción | Módulos | Duración | Incluye |
|---|---|---|---|
| **Básico** | 6 | 3–5 días | Mapeo, brechas, hallazgos, narrativa |
| **Estándar** | 17 | 7–10 días | Todo lo básico + encuesta, scoring, Bayesiano, BPMN, QA |
| **Completo** | 24 | 12–15 días | Todo lo estándar + TO-BE, ROI, NLP, Word descargable |

También se configura:
- ¿Publicar reporte al cliente? (activa flujo de aprobación)
- ¿Emitir certificado de gobernanza? (firmado con Ed25519)

### Paso 3 — Revisión y envío

Resumen completo antes de iniciar. Al confirmar, el sistema:
1. Evalúa las 18 reglas de gobernanza
2. Si pasa → crea el diagnóstico en PostgreSQL y lo encola
3. El Worker lo toma y ejecuta los agentes en secuencia

---

## 6. La pantalla de resultados

Cuando el diagnóstico completa, el consultor ve:

- **Score QA** — calificación del informe (0-100, mínimo 85 para aprobar)
- **Resumen ejecutivo** — párrafo C-suite generado por G13
- **Hallazgos confirmados** — priorizados por impacto y confianza bayesiana
- **Cuellos de botella** — con costo estimado en USD/mes
- **Recomendaciones estratégicas** — numeradas por prioridad
- **Roadmap** — acciones en 90, 180 y 365 días
- **Próximos pasos inmediatos**
- **Certificado de gobernanza** — colapsable, con hash y firma Ed25519
- **Botón Descargar Word** — genera el `.docx` con todo el contenido

---

## 7. El ledger de evidencia

Cada decisión del sistema queda registrada en un archivo append-only (`evidence-ledger.jsonl`) con:
- Timestamp
- Hash de la entrada anterior (cadena de hashes)
- Decisión (ALLOW / DENY / ESCALATE_TO_HUMAN)
- Reglas evaluadas
- Herramientas planificadas
- Razones de la decisión
- Hash de la entrada actual (firmado)

Esto garantiza que el historial no puede ser alterado retroactivamente. Visible en la pantalla **Evidencia** del sidebar.

---

## 8. Métricas BBR (Behavioral Baseline Reference)

El briefing define 7 métricas de comportamiento esperado. El panel de Admin muestra:

| Métrica | Valor esperado | Alerta si |
|---|---|---|
| Ratio escalado | ≤ 0.10 | > 0.10 |
| Ratio denegado | ≤ 0.05 | > 0.05 |
| QA score promedio | ≥ 87/100 | < 87 |
| IRR alpha | ≥ 0.75 | < 0.70 |
| Latencia p95 | ≤ 45,000ms | > 45,000ms |
| Tool calls/hora | ≤ 240 | > 240 |
| Tokens promedio | ≤ 60,000 | > 60,000 |

---

## 9. Cómo arrancar el sistema localmente

### Prerequisitos
- Python 3.11+
- Node.js 20+
- PostgreSQL corriendo (o Docker)
- Gemini API key

### Paso a paso

**1. Governance Engine (motor de gobernanza original)**
```bash
cd back
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
uvicorn arhiax_dx.main:app --host 0.0.0.0 --port 8088 --app-dir src
```

**2. Pipeline API**
```bash
cd back-api
python -m venv .venv
.venv\Scripts\activate
pip install -e .
# Configurar variables de entorno:
$env:DATABASE_URL="postgresql+asyncpg://usuario:password@localhost:5432/arhiax_dx"
$env:GEMINI_API_KEY="tu-key-aqui"
$env:SECRET_KEY="clave-secreta"
$env:GOVERNANCE_API_URL="http://localhost:8088"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --app-dir src --reload
```

**3. Worker (proceso independiente)**
```bash
cd back-api
# Con las mismas variables de entorno
python -m api.worker
```

**4. Frontend**
```bash
cd front
npm install
npm run dev
```

**5. Crear primer usuario admin**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sinergia.co","name":"Admin","password":"admin123","role":"admin"}'
```

**6. Abrir la app**
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Governance: http://localhost:8088/docs

---

## 10. Estructura del repositorio

```
arhiax-dx/
├── back/                          # Motor de gobernanza (original — no modificar)
│   ├── src/arhiax_dx/
│   │   ├── main.py                # FastAPI + 6 endpoints de gobernanza
│   │   ├── services/
│   │   │   ├── governance.py      # 18 reglas de gobernanza
│   │   │   ├── evidence.py        # Ledger append-only
│   │   │   └── provenance.py      # Certificados Ed25519
│   │   └── ...
│   └── specs/                     # Contrato de gobernanza (JSON versionados)
│       ├── agent_identity.json
│       ├── tool_catalog.json      # 24 herramientas declaradas
│       ├── autonomy_profile.json  # Niveles A0-A2
│       ├── model_strategy.json    # Routing Gemini por agente
│       └── ...
│
├── back-api/                      # Pipeline API (nuevo)
│   └── src/api/
│       ├── main.py                # FastAPI app
│       ├── models.py              # ORM: Diagnostic, PipelineStage, HumanReview, User
│       ├── worker.py              # Worker independiente (polling PostgreSQL)
│       ├── pipeline_runner.py     # Lógica de ejecución del pipeline
│       ├── routers/
│       │   ├── auth.py            # Login, registro
│       │   ├── diagnostics.py     # CRUD diagnósticos + descarga Word
│       │   ├── reviews.py         # Cola de revisiones humanas
│       │   ├── users.py           # Gestión de usuarios (admin)
│       │   ├── ledger.py          # Lectura del ledger
│       │   └── ws.py              # WebSocket de progreso
│       └── pipeline/
│           ├── executor.py        # Llama a Gemini por herramienta
│           ├── prompts.py         # Prompts especializados por agente
│           ├── governance_client.py # Llama al governance engine
│           └── docx_builder.py    # Genera el Word con python-docx
│
├── front/                         # Frontend Next.js (nuevo)
│   └── src/
│       ├── app/
│       │   ├── login/             # Pantalla de login
│       │   └── dashboard/
│       │       ├── page.tsx       # Dashboard principal
│       │       ├── diagnostics/   # Nuevo diagnóstico + detalle
│       │       ├── clients/       # Historial por cliente
│       │       ├── reviews/       # Cola de revisiones
│       │       ├── ledger/        # Evidencia
│       │       ├── compliance/    # Postura de cumplimiento
│       │       └── admin/         # Gestión de usuarios + BBR
│       ├── components/
│       │   ├── diagnostics/       # Wizard, detalle, progreso, resultados
│       │   ├── reviews/           # Cola de aprobaciones
│       │   ├── clients/           # Historial por cliente
│       │   ├── admin/             # Panel de administración
│       │   └── layout/            # Sidebar, Header
│       └── lib/
│           ├── api.ts             # Cliente axios
│           ├── auth.ts            # Token JWT en localStorage
│           ├── pipeline-presets.ts # Básico/Estándar/Completo
│           └── geo.ts             # Países y ciudades
│
├── PLATAFORMA.md                  # Este documento
├── ESTADO_ACTUAL_Y_PIPELINE.md    # Análisis técnico inicial
└── README.md                      # Guía de arranque rápido
```

---

## 11. APIs disponibles

### Pipeline API (http://localhost:8000)

| Método | Ruta | Descripción | Rol requerido |
|---|---|---|---|
| POST | /auth/login | Iniciar sesión | — |
| POST | /auth/register | Crear cuenta | — |
| GET | /auth/me | Usuario actual | Cualquiera |
| GET | /v2/diagnostics | Listar diagnósticos | Cualquiera |
| POST | /v2/diagnostics/submit | Crear diagnóstico | Operator+ |
| GET | /v2/diagnostics/stats | Estadísticas | Cualquiera |
| GET | /v2/diagnostics/clients | Clientes únicos | Cualquiera |
| GET | /v2/diagnostics/{id} | Detalle completo | Cualquiera |
| GET | /v2/diagnostics/{id}/download-report | Descargar Word | Cualquiera |
| WS | /v2/diagnostics/{id}/stream | Progreso en tiempo real | — |
| GET | /v2/reviews/pending | Cola de revisiones | Cualquiera |
| GET | /v2/reviews/pending/count | Conteo pendientes | Cualquiera |
| POST | /v2/reviews/{id}/approve | Aprobar | Reviewer+ |
| POST | /v2/reviews/{id}/reject | Rechazar | Reviewer+ |
| GET | /v2/ledger | Entradas del ledger | Cualquiera |
| GET | /v2/users | Listar usuarios | Admin |
| POST | /v2/users | Crear usuario | Admin |
| PATCH | /v2/users/{id} | Editar usuario | Admin |
| DELETE | /v2/users/{id} | Eliminar usuario | Admin |

### Governance Engine (http://localhost:8088)

| Método | Ruta | Descripción |
|---|---|---|
| GET | /healthz | Liveness check |
| GET | /readyz | Readiness |
| GET | /v1/compliance/posture | Contrato de gobernanza completo |
| GET | /v1/compliance/install-readiness | Estado de instalación |
| POST | /v1/diagnostics/evaluate | Evaluación gobernada |

---

## 12. Variables de entorno

### back-api/.env

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/arhiax_dx
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=clave-secreta-cambiar-en-produccion
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
GOVERNANCE_API_URL=http://localhost:8088
GEMINI_API_KEY=tu-gemini-api-key
ANTHROPIC_API_KEY=                    # opcional (fallback)
SPECS_PATH=../back/specs
LEDGER_PATH=../back/var/evidence-ledger.jsonl
```

### front/.env.local

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_GOVERNANCE_URL=http://localhost:8088
```

---

## 13. Lo que falta por construir

En orden de impacto para el negocio:

| Feature | Descripción | Complejidad |
|---|---|---|
| Encuesta real | Formulario para empleados, link de acceso, recolección de respuestas | Alta |
| Notificaciones | Badge en tiempo real cuando termina un diagnóstico | Baja |
| PDF export | Exportar el reporte a PDF además de Word | Media |
| Panel del cliente | Vista externa para que el cliente de Sinergia vea su diagnóstico | Media |
| BBR completo | Medir latencia p95, tokens promedio, tool calls/hora | Media |
| Versionado de reportes | Si se rechaza y se rehace, trazabilidad de versiones | Media |
| Docker Compose completo | Un solo comando levanta todo | Baja |

---

*Documento generado el 26 de abril de 2026 · ARHIAX Dx v5.1 · Sinergia Consulting Group*
