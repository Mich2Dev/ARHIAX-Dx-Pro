# Frontend: Relación fuente/espejo y puntos de integración

**Versión:** 0.1  
**Fecha:** 2026-06-23

---

## 1. Relación frontend fuente vs espejo

### Preguntas respondidas

**1. ¿Cuál es la fuente activa?**

`runtime/dxpro-runtime/frontend/arhiax-dxpro-site`

Es el directorio donde se realizan todos los cambios, builds y pruebas. Contiene el proyecto Vite + React completo con `package.json`, `tsconfig`, `vite.config`, etc.

**2. ¿Cuál es el espejo?**

`dx Pro/runtime/dxpro-runtime/frontend/arhiax-dxpro-site`

Es una copia sincronizada del frontend fuente, ubicada dentro del árbol del runtime (rama dx Pro) para que el backend pueda servirla o referenciarla. No debe editarse directamente.

**3. ¿Se deben sincronizar ahora?**

Sí, después de cada etapa de cambios en la fuente, debe copiarse al espejo.

Comando de sincronización:
```powershell
robocopy "runtime/dxpro-runtime/frontend/arhiax-dxpro-site" "dx Pro/runtime/dxpro-runtime/frontend/arhiax-dxpro-site" /E /XD "node_modules" "dist"
```

**4. ¿Qué archivos difieren?**

Se requiere diff para determinarlo. La fuente tiene todos los cambios de v0.1 y v0.2. El espejo se actualizó por última vez en v0.1 temprano y necesita re-sincronización completa.

**5. ¿Cómo evitar que futuras IAs editen el lugar equivocado?**

- El archivo `AGENTS.md` (o equivalente en `.claude/settings.json`) debe especificar:
  > "Frontend fuente: `runtime/dxpro-runtime/frontend/arhiax-dxpro-site`. No editar `dx Pro/runtime/dxpro-runtime/frontend/arhiax-dxpro-site` directamente — es espejo."
- El pipeline CI/CD (futuro) debe copiar desde fuente a espejo como paso de build.

---

## 2. Puntos de integración con informe final

### Estado actual del backend

El directorio `dx Pro/runtime/dxpro-runtime/src/dxpro_runtime/` contiene los tres módulos con implementación funcional:
- `api.py` — FastAPI con endpoints existentes (sin endpoint `/v1/agents/grammar/lint` aún)
- `pro_agents.py` — Agentes gobernados por PMEL (~1993 líneas, sin agente de gramática canónica aún)
- `report_exports.py` — Exportación DOCX/PDF/reportlab (~141 líneas, sin integración de lint previo)

Pendiente para v0.3: exponer endpoint lint, crear agente de gramática, integrar lint en exportación.

### Puntos de integración identificados

| Punto | Archivo esperado | Función |
|---|---|---|
| Fuente del texto | `report_exports.py` | El markdown del informe se genera aquí; debe pasarse al lint |
| Momento de revisión | `api.py` / endpoint lint | Antes de exportar, llamar a lint |
| Estado que debe producir | `GrammarReport` | Score, findings, publish decision |
| Cómo bloquea publicación | `api.py` / approval | Si publish_decision.allowed = false, rechazar |
| Qué queda para backend | Ver sección 3 | |

### Pipeline de revisión ideal (futuro)

```
1. Generar informe  (pro_agents)
       │
2. Producir markdown (report_exports)
       │
3. Ejecutar lint     (POST /v1/agents/grammar/lint)
       │
4. Evaluar resultado (frontend + backend)
       │
5. Si OK → exportar / publicar
   Si NO → bloquear + mostrar hallazgos
```

### Dónde se produce/almacena el texto del informe

| Formato | Origen | Estado |
|---|---|---|
| Markdown | Report pack generado por backend | Pendiente de implementación backend |
| DOCX | Exportación desde report_exports | Pendiente |
| PDF | Exportación desde report_exports | Pendiente |
| Executive thesis | Sección del report pack | Pendiente |
| Appendices | Sección del report pack | Pendiente |
| Exhibits | Sección del report pack | Pendiente |

Actualmente, el frontend solo puede revisar texto pegado manualmente o texto extraído del expediente (cliente, dominio, estado, archivos). La integración completa con el markdown del informe requiere backend.

---

## 3. Qué queda para backend

1. Implementar endpoint `POST /v1/agents/grammar/lint` según contrato en `docs/GRAMMAR_LINT_API_CONTRACT_v0.1.md`.
2. Implementar `pro_agents.py` con el motor de lint server-side.
3. Integrar lint en el flujo de exportación (`report_exports.py`).
4. Persistir el `GrammarReport` en el `CaseRecord`.
5. Persistir las excepciones en el expediente.
6. Proveer endpoint `GET /v1/cases/{id}/grammar` para consultar estado canónico histórico.
7. Incluir el audit pack (lint + excepciones) en el reporte final exportado.
