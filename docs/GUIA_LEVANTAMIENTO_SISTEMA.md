# Guía de levantamiento — ARHIAX Dx Pro (rama `integracion`)

**Para:** Marcelo y cualquier IA que le asista  
**Rama de trabajo:** `integracion` (monorepo completo)  
**Última actualización:** 2026-06-30

---

## 1. Qué es este sistema

Este repositorio integra **todo lo que construiste en tu `main`** dentro de la **plataforma monorepo** que presentamos en Brasil:

| Capa | Carpeta | Qué hace |
|---|---|---|
| Frontend operador | `front/` | Next.js 14 — dashboards Standard + Pro, encuestas, descargas |
| API plataforma | `back-api/` | FastAPI — auth, casos Pro, pipeline, grammar gate, PDF/DOCX |
| Motor gobernanza | `back/` | OPA/Rego, ledger de evidencia, specs |
| Runtime Dx Pro | `ARHIAX-Dx-Pro/` | `dxpro_runtime` — fusión, agentes, PMEL, **gramática canónica** |
| Orquestación | `docker-compose.yml` | 8 servicios en un solo comando |

**Tu `main` standalone ya no es la fuente de verdad.** Esta rama `integracion` lo es.  
Lo que tenías en `src/dxpro_runtime/grammar/` vive ahora en dos lugares equivalentes:

- `ARHIAX-Dx-Pro/src/dxpro_runtime/grammar/` — runtime Docker (puerto 8310)
- `back-api/src/api/pipeline/canonical_grammar/` — API plataforma (puerto 8000)

---

## 2. Requisitos previos

1. **Docker Desktop** instalado y corriendo (ícono verde en la bandeja).
2. **Git** con esta rama checkout: `integracion` / `feat/integracion-monorepo`.
3. Opcional: clave `GEMINI_API_KEY` o `ANTHROPIC_API_KEY` en un `.env` en la raíz para LLM real.  
   Sin clave, el pipeline corre en modo degradado pero **sí genera PDF**.

---

## 3. Levantar todo (un solo comando)

Desde la raíz del repo:

```powershell
cd C:\Users\maiko\OneDrive\Escritorio\Sinergia\ARIHAX-Dx-Pro
docker compose up --build -d
```

Espera ~2–3 minutos la primera vez (build de imágenes).

### Verificar que todo está sano

```powershell
docker compose ps
```

Todos deben estar `healthy` o `running`:

| Servicio | Puerto | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| API (back-api) | 8000 | http://localhost:8000/healthz |
| Dx Pro runtime | 8310 | http://localhost:8310/healthz |
| Governance | 8088 | http://localhost:8088/healthz |
| PostgreSQL | 5435 | (interno) |
| Redis | 6380 | (interno) |

---

## 4. Flujo de uso (humano)

1. Abrir **http://localhost:3000**
2. Registrar usuario o usar uno de prueba.
3. Ir a **Dashboard Pro** → **Nuevo caso**.
4. Completar consentimiento, cliente, dominio, roles.
5. Compartir link de encuesta → al menos 3 roles responden.
6. **Ejecutar diagnóstico** (run).
7. Esperar estado `review_pending`.
8. **Aprobar** caso (con `grammar_confirmed=true` si hay warnings).
9. **Generar entregables** → descargar PDF / DOCX / Markdown.

---

## 5. Flujo automático (prueba E2E)

Con Docker arriba:

```powershell
python scripts\run_pro_e2e.py
```

Genera PDF en `demo_pdfs/e2e_<case_id>/diagnostico.pdf`.

---

## 6. Gramática canónica (lo tuyo, integrado)

### Endpoints en la API plataforma (8000)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/pro/grammar/lint` | Lint de texto (24 reglas) |
| `GET` | `/pro/cases/{id}/grammar` | Reporte del caso |
| `POST` | `/pro/cases/{id}/publish` | Publicar con gate |
| `POST` | `/pro/cases/{id}/generate-deliverables` | Bloqueado si grammar crítico |

### Endpoints en runtime Dx Pro (8310) — mismos que tu main

| Método | Ruta |
|---|---|
| `POST` | `/v1/agents/grammar/lint` |
| `POST` | `/v1/dxpro/agents/grammar/lint` |
| `GET` | `/v1/cases/{case_id}/grammar` |

Documentación detallada: `docs/GRAMMAR_CANONICAL_BACKEND_v0.3.md`

---

## 7. PDF del informe

El PDF ejecutivo se genera en `back-api/src/api/pipeline/pro_pdf_builder.py`:

- Diseño alineado al mockup `ARHIAX_DxPro_informe_cliente_mockup.pdf`
- Contenido real del caso (fusión, reporte, evidencia)
- Grammar gate antes de publicar entregables finales

Descarga: `GET /pro/cases/{id}/download/pdf` (requiere auth JWT).

---

## 8. Mapa de carpetas (no confundir)

```
ARIHAX-Dx-Pro/                    ← RAÍZ del monorepo (trabajar aquí)
├── front/                        ← Frontend Next.js (EDITAR)
├── back-api/                     ← API plataforma (EDITAR)
├── back/                         ← Gobernanza
├── ARIHAX-Dx-Pro/                ← Runtime Dx Pro embebido (EDITAR)
│   ├── src/dxpro_runtime/
│   └── policy-bundle-pmel-v1.0.0/
├── docker-compose.yml
├── docs/
│   ├── GRAMMAR_CANONICAL_BACKEND_v0.3.md
│   └── DEPLOYMENT_DXPRO_REDEPLOY_CANONICAL_v1.0.md
└── scripts/run_pro_e2e.py
```

**No editar** carpetas sueltas `src/` o `frontend/` en la raíz si aparecen — son restos de checkout viejos.  
La fuente activa es el monorepo de arriba.

---

## 9. Reglas de trabajo en equipo

1. **Rama `integracion`** = desarrollo activo (Mich2Dev + Marcelo).
2. **No hacer revert en `main` de Marcelo** sin hablar — el producto vive en `integracion`.
3. Features nuevas de Marcelo → rama `feature/...` → PR hacia `integracion`.
4. Demos de presentación → ramas `feature/demo-*` que no tocan producción.
5. Cambios destructivos (revert, force push) → consultar antes.

---

## 10. Comandos útiles

```powershell
# Ver logs de la API
docker compose logs -f api

# Ver logs del runtime Dx Pro
docker compose logs -f dxpro

# Rebuild solo API después de cambios Python
docker compose up -d --build api

# Parar todo
docker compose down

# Tests grammar (local, sin Docker)
cd back-api
python -m pytest tests/test_grammar_gate.py -q
```

---

## 11. Para tu IA (prompt sugerido)

> Estoy en el monorepo ARHIAX-Dx-Pro, rama integracion.  
> La plataforma se levanta con `docker compose up --build -d`.  
> Frontend en `front/`, API en `back-api/`, runtime en `ARHIAX-Dx-Pro/`.  
> La gramática canónica está en `back-api/src/api/pipeline/canonical_grammar/`.  
> No uses el standalone viejo de mi main — todo está integrado aquí.  
> Para probar: `python scripts/run_pro_e2e.py`.

---

## 12. Soporte

Si algo no levanta:

1. ¿Docker Desktop está corriendo?
2. `docker compose ps` — ¿migrate completó?
3. `docker compose logs migrate` — ¿error de Alembic?
4. Puerto ocupado — cerrar instancias viejas o cambiar puerto en `docker-compose.yml`.
