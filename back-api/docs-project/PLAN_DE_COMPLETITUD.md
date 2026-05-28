# ARHIAX Dx — Plan de Completitud del Producto

**Fecha:** 26 de abril de 2026  
**Versión:** 1.0  
**Estado:** Producto funcional pero incompleto — requiere 4 elementos críticos para producción

---

## Resumen Ejecutivo

ARHIAX Dx tiene **construido el 70% del producto**:

✅ **Motor de gobernanza completo** (18 reglas, políticas Rego, evidencia firmada)  
✅ **Pipeline de 24 agentes implementado** (todos los prompts, routing Gemini/Claude)  
✅ **Base de datos y persistencia** (PostgreSQL, migraciones Alembic)  
✅ **Frontend funcional** (Next.js, dashboard, formulario de mandato, vista de progreso)  
✅ **Ejecución asíncrona** (Celery + Redis, WebSocket en tiempo real)  
✅ **Flujo de revisión humana** (cola de aprobaciones, aprobación/rechazo)  
✅ **Generación de reportes** (narrativa ejecutiva, hallazgos, roadmap)

❌ **Falta el 30% crítico** para que sea un producto completo de producción.

---

## 🔴 CRÍTICO — Sin esto el producto NO está completo

### 1. **Encuesta Multi-Rater Real** 
**Impacto:** Sin esto, el diagnóstico trabaja con datos simulados. Es el corazón del producto.

**Problema:**  
El agente G09a diseña 40-60 preguntas, pero no hay forma de enviárselas a los empleados de la organización diagnosticada. El scoring, análisis Bayesiano y hallazgos trabajan con datos mock.

**Lo que falta construir:**

#### Backend (back-api/)
- [ ] **Modelo `SurveySession`** — ya existe en `models.py` ✅
- [ ] **Modelo `SurveyResponse`** — ya existe en `models.py` ✅
- [ ] **Endpoint público:** `GET /survey/{token}` — retorna preguntas para el respondente
- [ ] **Endpoint público:** `POST /survey/{token}/submit` — guarda respuesta anónima
- [ ] **Endpoint interno:** `GET /v1/diagnostics/{id}/survey/status` — progreso de respuestas
- [ ] **Endpoint interno:** `POST /v1/diagnostics/{id}/survey/close` — cierra encuesta y dispara análisis
- [ ] **Lógica de ramificación adaptativa** — mostrar preguntas según rol y respuestas previas
- [ ] **Trigger automático:** cuando `responses_count >= min_responses`, continuar pipeline desde G10a

#### Frontend (front/)
- [ ] **Página pública:** `/survey/[token]` — formulario de encuesta sin autenticación
- [ ] **Selector de rol:** Estratégico / Táctico / Operativo
- [ ] **Formulario adaptativo:** mostrar preguntas según rol y ramificación
- [ ] **Validación:** no permitir envío incompleto
- [ ] **Confirmación:** pantalla de agradecimiento post-envío
- [ ] **Panel del consultor:** ver progreso de respuestas en `/dashboard/diagnostics/[id]`
- [ ] **Botón manual:** "Cerrar encuesta y continuar análisis" si no se alcanza target

#### Flujo completo
```
1. G09a diseña preguntas → guarda en SurveySession
2. Sistema genera token único → URL: https://arhiax.app/survey/{token}
3. Consultor comparte URL con empleados de la organización
4. Empleados responden (anónimo, solo se guarda hash + rol)
5. Sistema cuenta respuestas en tiempo real
6. Cuando responses_count >= min_responses:
   → Trigger automático: continuar pipeline desde G10a (scoring)
   → O consultor cierra manualmente si quiere esperar más respuestas
7. G10a-G14 procesan respuestas reales (no mock)
```

**Estimación:** 3-4 días de desarrollo

---

### 2. **Notificaciones en Tiempo Real**
**Impacto:** El consultor no sabe cuándo termina un diagnóstico sin estar mirando la pantalla.

**Problema:**  
El badge del sidebar solo se actualiza si el usuario está activo en la app. No hay notificaciones push ni email.

**Lo que falta construir:**

#### Backend
- [ ] **Servicio de notificaciones:** integrar con webhook HIC (ya configurado en .env)
- [ ] **Eventos a notificar:**
  - Diagnóstico completado
  - Diagnóstico requiere revisión humana
  - Encuesta alcanzó mínimo de respuestas
  - QA rechazó informe (score < 85)
  - Hallazgo crítico (delta_sigma > 2.0)
- [ ] **Endpoint:** `POST /v1/notifications/send` — envía notificación vía webhook

#### Frontend
- [ ] **Notificaciones en navegador:** usar Web Push API o polling cada 30s
- [ ] **Badge en sidebar:** actualizar en tiempo real (ya existe, mejorar)
- [ ] **Centro de notificaciones:** dropdown con historial de notificaciones

#### Opcional (v2)
- [ ] Email notifications vía SendGrid/AWS SES
- [ ] WhatsApp Business API para notificaciones CRITICAL (ya está en el briefing)

**Estimación:** 1-2 días

---

### 3. **Docker Compose Completo**
**Impacto:** Hoy hay que arrancar 4 procesos manualmente. Mala experiencia de instalación.

**Problema:**  
El `docker-compose.yml` existe pero falta:
- Migraciones automáticas al iniciar
- Healthchecks completos
- Volúmenes persistentes para outputs
- Variables de entorno bien documentadas

**Lo que falta:**

- [ ] **Migración automática:** agregar `command` en `pipeline-api` que ejecute `alembic upgrade head` antes de `uvicorn`
- [ ] **Healthcheck del worker:** verificar que Celery está procesando tareas
- [ ] **Volumen para reportes:** montar `./back/var/outputs` para persistir .docx generados
- [ ] **Seed de usuario admin:** script que crea usuario admin@sinergia.co si no existe
- [ ] **README actualizado:** instrucciones claras de instalación en 3 pasos

**Estimación:** 1 día

---

### 4. **Generación de DOCX Real**
**Impacto:** El agente G14 aprueba el informe pero no se genera el Word final.

**Problema:**  
`docx_generator` está implementado como mock. Falta usar `python-docx` para generar el documento real.

**Lo que falta construir:**

#### Backend (back-api/src/api/pipeline/)
- [ ] **Archivo:** `docx_builder.py` — ya existe ✅ (revisar si está completo)
- [ ] **Función:** `generate_docx(narrative: dict, output_path: str)` — genera Word profesional
- [ ] **Secciones del documento:**
  - Portada con logo Sinergia
  - Resumen ejecutivo
  - Hallazgos principales (con tablas)
  - Análisis de brechas de percepción
  - Cuellos de botella cuantificados (con gráficos si es posible)
  - Recomendaciones estratégicas
  - Roadmap 90/180/365 días
  - Anexos (certificado firmado, metadata)
- [ ] **Estilos profesionales:** fuentes, colores corporativos, encabezados
- [ ] **Guardar en:** `back/var/outputs/{diagnostic_id}/report.docx`
- [ ] **Actualizar modelo Report:** guardar `docx_path` en la base de datos

#### Frontend
- [ ] **Botón de descarga:** en `/dashboard/diagnostics/[id]` cuando status = completed
- [ ] **Endpoint:** `GET /v1/diagnostics/{id}/download/docx` — descarga el archivo

**Estimación:** 2 días

---

## 🟠 IMPORTANTE — El producto funciona pero está incompleto

### 5. **PDF Export**
**Impacto:** Los clientes ejecutivos prefieren PDF sobre Word.

**Solución:**  
Convertir el .docx generado a PDF usando `docx2pdf` (Windows) o `libreoffice --headless` (Linux/Docker).

- [ ] **Función:** `convert_docx_to_pdf(docx_path: str) -> str`
- [ ] **Guardar en:** `back/var/outputs/{diagnostic_id}/report.pdf`
- [ ] **Endpoint:** `GET /v1/diagnostics/{id}/download/pdf`

**Estimación:** 1 día

---

### 6. **BBR Metrics Completas**
**Impacto:** El panel de admin no mide las métricas de gobernanza definidas en el briefing.

**Métricas faltantes:**
- [ ] `tool_calls_hora` — promedio de llamadas a herramientas por hora
- [ ] `p50_latencia_ms` — mediana de latencia por agente
- [ ] `p95_latencia_ms` — percentil 95 de latencia
- [ ] `ratio_escalado` — % de diagnósticos que escalaron a HIC
- [ ] `ratio_deny` — % de diagnósticos denegados
- [ ] `tokens_promedio_por_agente` — consumo de tokens por herramienta

**Dónde construir:**
- [ ] **Backend:** endpoint `GET /v1/metrics/bbr` — calcula métricas desde `pipeline_stages`
- [ ] **Frontend:** panel `/dashboard/admin` — gráficos de métricas BBR

**Estimación:** 2 días

---

### 7. **Panel del Cliente Externo**
**Impacto:** El cliente de Sinergia (la empresa diagnosticada) no puede ver su reporte.

**Solución:**  
Portal público con autenticación por token donde el cliente puede:
- Ver el estado de su diagnóstico
- Descargar el reporte final (DOCX/PDF)
- Ver el certificado firmado
- Ver el ledger de evidencia de su diagnóstico

- [ ] **Ruta:** `/client/[token]` — portal del cliente
- [ ] **Autenticación:** token único generado al crear el diagnóstico
- [ ] **Vistas:** estado, reporte, certificado, evidencia

**Estimación:** 2-3 días

---

## 🟡 MEJORAS DE CALIDAD — No bloquean producción

### 8. **Versionado de Reportes**
Si un Reviewer rechaza el informe, no hay trazabilidad de versiones.

**Solución:**
- [ ] Tabla `report_versions` con historial de cambios
- [ ] Campo `version` en modelo `Report`
- [ ] Vista de historial en frontend

**Estimación:** 1 día

---

### 9. **Validación de Agentes con Gemini Real**
G01, G02, G05 cayeron al mock en el diagnóstico de prueba porque usaban `gemini-2.0-flash` (no disponible).

**Estado:** Ya corregidos en `prompts.py` (usan `gemini-2.5-flash`) ✅

**Pendiente:**
- [ ] Ejecutar diagnóstico completo end-to-end con Gemini real
- [ ] Validar que todos los 24 agentes retornan JSON válido
- [ ] Medir latencias reales y ajustar timeouts si es necesario

**Estimación:** 1 día de testing

---

### 10. **Validación del Formulario en Móvil**
El formulario de mandato es largo y difícil de navegar en pantallas pequeñas.

**Solución:**
- [ ] Mejorar responsive design del formulario multi-paso
- [ ] Agregar indicador de progreso más visible
- [ ] Validación inline por campo (no solo al enviar)

**Estimación:** 1 día

---

## Orden de Implementación Recomendado

### Sprint 1 — Completar el núcleo (5-6 días)
1. **Encuesta Multi-Rater Real** (3-4 días) 🔴
2. **Generación de DOCX Real** (2 días) 🔴

### Sprint 2 — Operaciones y despliegue (3-4 días)
3. **Docker Compose Completo** (1 día) 🔴
4. **Notificaciones en Tiempo Real** (1-2 días) 🔴
5. **PDF Export** (1 día) 🟠

### Sprint 3 — Métricas y cliente externo (4-5 días)
6. **BBR Metrics Completas** (2 días) 🟠
7. **Panel del Cliente Externo** (2-3 días) 🟠

### Sprint 4 — Calidad y refinamiento (3 días)
8. **Versionado de Reportes** (1 día) 🟡
9. **Testing completo con Gemini** (1 día) 🟡
10. **Validación móvil** (1 día) 🟡

**Total estimado:** 15-18 días de desarrollo

---

## Estado Actual del Código

### ✅ Completamente implementado
- Motor de gobernanza (18 reglas)
- Políticas Rego
- Ledger de evidencia con hash encadenado
- Firma Ed25519 de certificados
- 24 prompts de agentes (calidad consultora)
- Routing de modelos Gemini/Claude
- Base de datos PostgreSQL + migraciones
- Autenticación JWT
- Dashboard frontend (Next.js + shadcn/ui)
- Formulario de mandato multi-paso
- Vista de progreso en tiempo real (WebSocket)
- Cola de revisión humana
- Aprobación/rechazo de informes

### ⚠️ Parcialmente implementado
- Encuesta Multi-Rater (modelos existen, falta UI y lógica)
- Generación DOCX (existe `docx_builder.py`, revisar completitud)
- Notificaciones (webhook configurado, falta integración)
- Docker Compose (existe, falta migraciones automáticas)

### ❌ No implementado
- Formulario público de encuesta
- Trigger automático al alcanzar min_responses
- PDF export
- BBR metrics completas
- Panel del cliente externo
- Versionado de reportes

---

## Dependencias Técnicas

### Backend
```
✅ FastAPI 0.115+
✅ SQLAlchemy + Alembic
✅ Celery + Redis
✅ google-generativeai (Gemini)
✅ anthropic (Claude fallback)
✅ cryptography (Ed25519)
⚠️ python-docx (instalado, revisar uso)
❌ docx2pdf o libreoffice (para PDF)
```

### Frontend
```
✅ Next.js 14
✅ shadcn/ui + Tailwind
✅ TanStack Query
✅ React Hook Form + Zod
✅ WebSocket (nativo)
❌ Web Push API (notificaciones)
```

### Infraestructura
```
✅ PostgreSQL 16
✅ Redis 7
✅ Docker + Docker Compose
⚠️ Migraciones automáticas (falta)
❌ Nginx (para producción)
❌ SSL/TLS (para producción)
```

---

## Riesgos y Mitigaciones

### Riesgo 1: Encuesta sin respuestas reales
**Impacto:** El diagnóstico no tiene valor sin datos reales de empleados.  
**Mitigación:** Priorizar Sprint 1 — Encuesta Multi-Rater.

### Riesgo 2: Latencias altas de Gemini
**Impacto:** Pipeline puede tardar 20-30 minutos en completarse.  
**Mitigación:** Ya implementado con Celery async + WebSocket. Monitorear latencias reales.

### Riesgo 3: Costos de API de Gemini
**Impacto:** Un diagnóstico completo puede consumir 200k-500k tokens.  
**Mitigación:** Usar `gemini-2.5-flash` para la mayoría de agentes (ya implementado). Solo `gemini-2.5-pro` para G11a, G13, G14.

### Riesgo 4: Calidad de outputs de LLM
**Impacto:** Gemini puede retornar JSON inválido o respuestas fuera de scope.  
**Mitigación:** G14 (QA Control) valida calidad antes de aprobar. Prompts son específicos y estructurados.

---

## Criterios de Aceptación para Producción

### Funcionales
- [ ] Un diagnóstico completo end-to-end con encuesta real genera reporte DOCX descargable
- [ ] El consultor recibe notificación cuando el diagnóstico está listo
- [ ] El cliente externo puede ver y descargar su reporte con un token
- [ ] `docker-compose up` levanta todo el stack sin intervención manual
- [ ] BBR metrics se calculan correctamente y se muestran en el panel de admin

### No funcionales
- [ ] Pipeline completo tarda < 30 minutos con 20 respuestas de encuesta
- [ ] Latencia p95 de agentes < 45 segundos (según briefing)
- [ ] Ratio de escalado < 10% (según briefing)
- [ ] Ratio de deny < 5% (según briefing)
- [ ] Certificados firmados verificables con clave pública

### Seguridad
- [ ] Respuestas de encuesta son anónimas (solo hash + rol)
- [ ] Tokens de encuesta son únicos y no adivinables (UUID v4)
- [ ] Claves Ed25519 nunca se exponen en logs ni respuestas
- [ ] API keys de Gemini/Claude solo en .env, nunca en código

---

## Conclusión

**ARHIAX Dx está al 70% de completitud.**

El motor de gobernanza y el pipeline de agentes están completos y funcionando. Lo que falta es crítico pero acotado:

1. **Encuesta real** — sin esto, el producto no tiene valor
2. **DOCX real** — sin esto, no hay entregable final
3. **Docker completo** — sin esto, la instalación es manual y propensa a errores
4. **Notificaciones** — sin esto, la experiencia de usuario es pobre

Con **2 sprints (9-10 días)** se completa el producto mínimo viable para producción.  
Con **4 sprints (15-18 días)** se tiene un producto completo y pulido.

---

**Próximo paso recomendado:**  
Comenzar Sprint 1 con la **Encuesta Multi-Rater Real** — es el corazón del diagnóstico y desbloquea el valor completo del producto.
