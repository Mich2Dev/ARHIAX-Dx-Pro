# ARHIAX Dx Pro — Rama `dev`

> **⚠️ PRIORIDAD DE LECTURA:** antes de tocar código, lee  
> **[docs/PRIORIDAD_LECTURA_ESTADO_OPERATIVO_DX_PRO.md](docs/PRIORIDAD_LECTURA_ESTADO_OPERATIVO_DX_PRO.md)**  
> (estado julio 2026 — caso Ivania, compuertas `credit`, pipeline G01–G14, motor P01–P07).

Plataforma de diagnósticos organizacionales gobernados — **Sinergia Consulting Group S.A.S.**

Esta rama concentra el flujo **Dx Pro** completo: wizard → pipeline G01–G14 → encuesta multi-rater → diagnóstico → aprobación HIL → entregables PDF/Markdown.

## Repositorios

| Remoto | URL | Uso |
|--------|-----|-----|
| **Mich2Dev** (principal) | https://github.com/Mich2Dev/ARHIAX-Dx-Pro | Rama de trabajo `dev` |
| **Marcelo7225** | https://github.com/Marcelo7225/ARHIAX-Dx-Pro | Espejo / integración con Marcelo |

```bash
git clone https://github.com/Mich2Dev/ARHIAX-Dx-Pro.git
cd ARHIAX-Dx-Pro
git checkout dev
```

---

## Producción (Cloud Run)

| Campo | Valor |
|-------|-------|
| **URL pública** | https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/ |
| **Proyecto GCP** | `arhiax-project` |
| **Región** | `southamerica-east1` |
| **Servicio** | `arhiax-dx-pro` |
| **Cloud SQL** | `arhiax-project:southamerica-east1:arhiax-db` |

### Arquitectura en producción

Un solo contenedor monolítico (Supervisord) ejecuta:

- **Frontend** Next.js → puerto `3000` (expuesto por Cloud Run)
- **back-api** FastAPI → `localhost:8000`
- **worker** pipeline asíncrono
- **governance** → `localhost:8088`
- **dxpro runtime** → `localhost:8310`
- **Redis** → `localhost:6379`

El navegador llama a la API vía proxy interno: `/api/backend/*` → `http://localhost:8000/*`.

### Desplegar a Cloud Run

**Requisitos:** [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) autenticado con acceso al proyecto `arhiax-project`.

**Opción rápida (Windows):**

```bat
deploy-cloudrun.bat
```

**Opción manual (PowerShell / bash):**

```bash
gcloud run deploy arhiax-dx-pro \
  --source . \
  --project arhiax-project \
  --region southamerica-east1 \
  --memory 4Gi \
  --cpu 2 \
  --port 3000 \
  --allow-unauthenticated \
  --timeout=3600 \
  --add-cloudsql-instances arhiax-project:southamerica-east1:arhiax-db \
  --update-env-vars "APP_URL=https://arhiax-dx-pro-187668243215.southamerica-east1.run.app"
```

El build usa el `Dockerfile` de la raíz. Cloud Build empaqueta todo el monorepo y despliega una nueva revisión.

**Variables de entorno en Cloud Run** (configurar en consola GCP o con `--update-env-vars` / Secret Manager):

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Postgres vía socket Cloud SQL (`postgresql+asyncpg://...`) — ya configurada en el servicio |
| `APP_URL` | URL pública para enlaces de encuesta |
| `GEMINI_API_KEY` | **Obligatoria** — sin llave el pipeline no ejecuta (fail-closed, sin mock) |
| `ANTHROPIC_API_KEY` | LLM alternativo si aplica |

> **Cold start:** tras un deploy nuevo el contenedor tarda ~30–45 s en levantar todos los servicios. Si el login falla al primer intento, espera y recarga.

**Verificar salud:**

```bash
curl https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/api/backend/healthz
# → {"status":"ok","service":"arhiax-dx-pipeline-api"}
```

---

## Desarrollo local

### Requisitos

- Docker Desktop
- Python 3.11+ (para scripts E2E)
- Node.js 18+ (solo si desarrollas el frontend fuera de Docker)

### Arranque

```bat
start.bat
```

O manualmente:

```bash
docker compose up -d --build
```

Si no existe `.env`, copia desde `.env.example` y agrega `GEMINI_API_KEY` si tienes una.

### URLs locales

| URL | Servicio |
|-----|----------|
| http://localhost:3001 | Frontend (consola Dx Pro) |
| http://localhost:8000 | API pipeline (`back-api`) |
| http://localhost:8088 | Governance |
| http://localhost:8310 | Dx Pro runtime |
| localhost:5435 | PostgreSQL (host) |

### Credenciales (seed)

| Campo | Valor |
|-------|-------|
| **Email** | `admin@arhiax.com` |
| **Password** | `arhiax-admin-2026` |

Se crean con `python -m api.seed` al levantar el contenedor `migrate`. Personalizables vía `SEED_ADMIN_EMAIL` y `SEED_ADMIN_PASSWORD`.

### Consola Pro

Tras login, el flujo principal está en:

```
http://localhost:3001/dashboard-pro
```

---

## Flujo E2E automatizado

Scripts en `back-api/scripts/` que replican el recorrido completo de un usuario en la UI.

### Caso completo (crear → encuesta → diagnóstico → aprobar → PDF)

```bash
cd back-api
python scripts/user_flow_completo.py
```

Pasos que ejecuta:

1. Login en `/auth/login`
2. Crear caso vía wizard (`POST /pro/cases`)
3. Esperar pipeline G01–G08 + encuesta G09 (`survey_open`)
4. Responder encuesta por rol (Estratégico / Operativo / Táctico)
5. Lanzar diagnóstico (`POST /pro/cases/{id}/run`)
6. Esperar fusión G10–G14 (`review_pending`)
7. Aprobar en HIL
8. Generar y descargar PDF + Markdown

**Reanudar un caso existente:**

```bash
# PowerShell
$env:CASE_ID="uuid-del-caso"
python scripts/user_flow_completo.py
```

**Salida:**

```
exports/caso_completo/
├── case-<ref>_<cliente>.pdf
├── case-<ref>_<cliente>.md
└── ultimo_caso.json    ← UUID, URLs y rutas del último run
```

### Regenerar entregables de un caso ya aprobado

```bash
python scripts/download_deliverables.py <case-uuid>
```

### Otros scripts

| Script | Uso |
|--------|-----|
| `e2e_pro_flow.py` | Flujo E2E alternativo → `exports/e2e_demo/` |
| `regen_pdf.py` | Regenerar PDF de un caso en `exports/e2e_demo/` |

---

## Entregables PDF

El informe Pro se genera en `back-api/src/api/pipeline/`:

| Módulo | Responsabilidad |
|--------|-----------------|
| `pro_report_data.py` | Datos enriquecidos del informe |
| `pro_pdf_report.py` | Layout PDF (secciones, tablas, DDF por bloques) |
| `pro_pdf_charts.py` | Gráficas (madurez, triangulación, etc.) |
| `pro_markdown_builder.py` | Versión Markdown del mismo contenido |
| `pro_pdf_builder.py` | Orquestador de exportación |

Endpoints:

```
POST /pro/cases/{id}/generate-deliverables
GET  /pro/cases/{id}/download/pdf
GET  /pro/cases/{id}/download/markdown
```

---

## Estructura del repositorio

```
/
├── front/                  # Frontend Next.js (consola Dx Pro)
├── back-api/               # API pipeline Pro + Standard (FastAPI, Alembic, worker)
│   └── scripts/            # E2E, download_deliverables, regen_pdf
├── back/                   # Servicio de gobernanza + specs
├── ARHIAX-Dx-Pro/          # Runtime Dx Pro standalone
├── docs/                   # Documentación extendida
├── exports/                # PDFs generados localmente (no versionados)
├── docker-compose.yml      # Desarrollo local multi-contenedor
├── Dockerfile              # Imagen monolítica para Cloud Run
├── supervisord.conf        # Procesos del monolito en producción
├── start-cloudrun.sh       # Migraciones + arranque en Cloud Run
├── deploy-cloudrun.bat     # Deploy one-click a GCP
└── .dockerignore
```

---

## Comandos útiles

```bash
# Logs de todos los servicios
docker compose logs -f

# Solo API o worker
docker compose logs -f api worker

# Reiniciar un servicio
docker compose restart api

# Detener todo
docker compose down

# Migraciones manuales
docker compose exec api sh -c "cd /app && alembic upgrade head"

# Health check local
curl http://localhost:8000/healthz
```

---

## Variables de entorno (desarrollo)

Ver `.env.example` en la raíz y `back-api/.env.example`. Las más relevantes:

| Variable | Default local | Descripción |
|----------|---------------|-------------|
| `DATABASE_URL` | Postgres en Docker (`5435`) | Conexión async SQLAlchemy |
| `REDIS_URL` | `redis://redis:6379/0` | Cola del worker |
| `GEMINI_API_KEY` | **Obligatoria** | LLM para todas las etapas G01–G14 |
| `APP_URL` | `http://localhost:3001` | Base URL para links de encuesta |
| `SECRET_KEY` | dev secret | JWT auth |

---

## Rama `dev` — qué incluye

- PDF Pro denso (~15 páginas): contexto, cartografía, DDF, triangulación, roadmap, matriz
- Fix auditoría encuesta (roles ES/EN en `survey.py`)
- Panel de auditoría Pro en frontend (`SurveyAuditPanel` → `/pro/survey/{token}/audit`)
- Scripts E2E y descarga de entregables
- Config de deploy Cloud Run monolítico con Cloud SQL

### Sincronizar con Marcelo

```bash
git push marcelofork dev    # Mich2Dev
git push marcelo dev        # Marcelo7225 (si tienes acceso)
```

---

## Política regulatoria: fail-closed (sin mock)

El pipeline **nunca** genera contenido simulado. Si el LLM no está disponible o falla:

1. La etapa queda en `failed` y el caso pasa a `error`
2. **No** se activan fallbacks deterministas ni placeholders
3. **No** se puede aprobar (HIL) ni generar PDF con etapas fallidas
4. Queda evidencia `pipeline_failed` con `policy: fail_closed_no_mock`

**Requisito:** `GEMINI_API_KEY` configurada en `.env` (local) o Cloud Run (producción).

```bash
curl http://localhost:8000/healthz
# → {"status":"ok","llm_configured":true,"policy":"fail_closed_no_mock"}
```

---

## Documentación adicional

- [Estructura del proyecto](docs/ESTRUCTURA.md)
- [Checklist de producción](docs/PRODUCCION_CHECKLIST.md)
- [Redespliegue canónico Dx Pro](docs/DEPLOYMENT_DXPRO_REDEPLOY_CANONICAL_v1.0.md)
- [Arquitectura Dx Pro](ARHIAX-Dx-Pro/docs/ARCHITECTURE.md)
- [Checklist verificación DDF](docs/CHECKLIST_VERIFICACION_DDF.md)

---

## Soporte

**Sinergia Consulting Group S.A.S.** · Dx Platform v5.1 · Governed
