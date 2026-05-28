# Implementación de Encuestas Multi-Rater — Progreso

## ✅ Backend Completado

### 1. Router de Encuestas Públicas (`survey.py`)
**Archivo:** `back-api/src/api/routers/survey.py`

**Endpoints implementados:**
- `GET /survey/{token}` — Retorna preguntas de la encuesta (público, sin auth)
- `POST /survey/{token}/submit` — Guarda respuesta anónima (público, sin auth)
- `GET /survey/{token}/status` — Estado de la encuesta y conteo de respuestas

**Características:**
- ✅ Validación de rol (Estratégico/Táctico/Operativo)
- ✅ Hash anónimo del respondente (SHA256)
- ✅ Prevención de respuestas duplicadas
- ✅ Validación de completitud de respuestas
- ✅ Conteo automático de respuestas por rol
- ✅ Detección de cuándo alcanza min_responses

### 2. Integración en Main API
**Archivo:** `back-api/src/api/main.py`
- ✅ Router de survey registrado

### 3. Lógica de Pausa del Pipeline
**Archivo:** `back-api/src/api/pipeline_runner.py`

**Implementado:**
- ✅ Detección de finalización de G09c_validacion
- ✅ Creación automática de `SurveySession` con token único
- ✅ Extracción de preguntas de G09a y ramificación de G09b
- ✅ Cambio de estado del diagnóstico a "awaiting_responses"
- ✅ Pausa del pipeline (return early)
- ✅ Logging detallado

### 4. Endpoints de Gestión de Encuesta
**Archivo:** `back-api/src/api/routers/diagnostics.py`

**Nuevos endpoints:**
- `POST /v2/diagnostics/{id}/survey/close` — Cierra encuesta y continúa pipeline (auth requerido)
- `GET /v2/diagnostics/{id}/survey/status` — Estado de encuesta para el consultor (auth requerido)

**Características:**
- ✅ Cierre manual de encuesta por el consultor
- ✅ Cambio de estado de "awaiting_responses" a "running"
- ✅ Trigger de continuación del pipeline desde G10a
- ✅ Conteo de respuestas por rol
- ✅ URL de la encuesta generada

### 5. Sistema de Continuación del Pipeline
**Archivo:** `back-api/src/api/tasks.py`

**Implementado:**
- ✅ Función `continue_pipeline_from_g10a()`
- ✅ Logging de continuación

**Pendiente:**
- ⚠️ Implementar lógica completa en worker.py para detectar y continuar desde G10a

---

## 🚧 Pendiente — Frontend

### 1. Página Pública de Encuesta
**Archivo:** `front/src/app/survey/[token]/page.tsx` (CREAR)

**Funcionalidad requerida:**
- [ ] Layout sin autenticación (sin sidebar)
- [ ] Pantalla de bienvenida con selector de rol
- [ ] Formulario multi-paso con preguntas
- [ ] Aplicación de lógica de ramificación
- [ ] Validación de completitud
- [ ] Envío de respuestas
- [ ] Pantalla de confirmación

### 2. Panel de Encuesta en Dashboard
**Archivo:** `front/src/components/diagnostics/SurveyPanel.tsx` (CREAR)

**Funcionalidad requerida:**
- [ ] Mostrar URL de la encuesta
- [ ] Botón para copiar URL
- [ ] Progreso de respuestas (X/20)
- [ ] Conteo por rol
- [ ] Botón "Cerrar encuesta y continuar"
- [ ] Actualización en tiempo real

### 3. Integración en DiagnosticDetail
**Archivo:** `front/src/components/diagnostics/DiagnosticDetail.tsx`

**Cambios requeridos:**
- [ ] Detectar estado "awaiting_responses"
- [ ] Mostrar SurveyPanel cuando aplique
- [ ] Banner especial para este estado

---

## 📋 Próximos Pasos

### Paso 1: Completar Worker Logic (30 min)
Actualizar `worker.py` para:
- Detectar diagnósticos en estado "running" que vienen de "awaiting_responses"
- Cargar respuestas de la encuesta
- Continuar pipeline desde G10a con datos reales

### Paso 2: Frontend — Página Pública (2-3 horas)
- Crear layout sin auth
- Implementar formulario adaptativo
- Integrar con API

### Paso 3: Frontend — Panel de Consultor (1 hora)
- Crear SurveyPanel
- Integrar en DiagnosticDetail
- Polling de estado

### Paso 4: Testing End-to-End (1 hora)
- Crear diagnóstico
- Esperar a G09c
- Responder encuesta
- Verificar continuación
- Descargar reporte con datos reales

---

## 🎯 Estado Actual: 60% Completado

**Backend:** 90% ✅  
**Frontend:** 0% ⚠️  
**Testing:** 0% ⚠️

**Tiempo estimado restante:** 4-5 horas
