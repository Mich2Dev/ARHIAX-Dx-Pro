# Checklist de verificación DDF — para revisión con IA

**Rama:** `dev`  
**Monorepo:** `ARIHAX-Dx-Pro/`  
**Referencia:** motor DDF en `main` (`src/dxpro_runtime/`)

---

## Cómo levantar

```powershell
cd ARIHAX-Dx-Pro
docker compose up --build -d
```

Login: `admin@arhiax.com` / `arhiax-admin-2026`

---

## Ya integrado (debería decir "sí")

| Módulo en `main` | Equivalente en `dev` |
|---|---|
| `grammar/` | `back-api/src/api/pipeline/canonical_grammar/` + `ARIHAX-Dx-Pro/src/dxpro_runtime/grammar/` |
| `pro_agents.py` (fusión, reporte, PMEL) | `ARIHAX-Dx-Pro/src/dxpro_runtime/pro_agents.py` |
| `policy.py`, `evidence.py`, `capture_agent.py` | Mismo path en runtime embebido |
| `report_exports.py` | Runtime + `back-api/src/api/pipeline/pro_pdf_builder.py` |
| Prompts G09a/b/c | `back-api/src/api/pipeline/prompts/survey.py` |
| Intake con incidentes | `front/.../ProStep2Scope.tsx` + `back-api/.../hypothesis_pack.py` |

Comandos de verificación:

```powershell
curl http://localhost:8000/healthz
curl http://localhost:8310/healthz
python scripts/run_pro_e2e.py
```

---

## En progreso / pendiente de port completo

| Módulo en `main` | Estado en `dev` |
|---|---|
| `ddf_case.py` | Pendiente en runtime (`ARIHAX-Dx-Pro/src/dxpro_runtime/`) |
| `orchestrator.py` | Pendiente |
| `ddf_report.py` (mapa forense) | Pendiente |
| Agentes S1–S8 en `pro_agents.py` (líneas ~2196+) | Pendiente |
| Endpoints `/v1/ddf/cases/*` | Pendiente en `api.py` del runtime |
| UI `DdfConsole.tsx` | Pendiente en `front/` |

Buscar en el monorepo:

```powershell
rg "ddf_case|orchestrator|mapa_forense" ARIHAX-Dx-Pro/
```

Si no hay hits en `ARIHAX-Dx-Pro/src/dxpro_runtime/`, el pipeline DDF de 8 etapas aún no está cableado — solo la plataforma + G09.

---

## Flujo actual vs flujo DDF completo

**Hoy (`dev`):** intake → G09a/b/c (Gemini) → encuesta → fusión → aprobación → PDF

**`main` (DDF):** intake → S1 compuerta hipótesis → S2+S5 ítems → compuerta ítems → campo → S6–S8 → mapa forense → informe

---

## Prompt sugerido para la IA de Marcelo

> Revisa el monorepo ARHIAX-Dx-Pro rama dev.  
> Compara `docs/CHECKLIST_VERIFICACION_DDF.md` con los archivos listados.  
> Confirma gramática, runtime base y prompts G09.  
> Señala si faltan `ddf_case.py`, `orchestrator.py` y endpoints `/v1/ddf/`.  
> Prueba crear un caso con hipótesis + incidente concreto y verifica que la encuesta muestre `rationale` por pregunta.
