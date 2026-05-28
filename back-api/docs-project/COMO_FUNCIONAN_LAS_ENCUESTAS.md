# ARHIAX Dx — Cómo Funcionan las Encuestas Multi-Rater

## 🎯 Concepto Central

El diagnóstico **Multi-Rater** significa que **3 niveles jerárquicos** de la organización responden la misma encuesta:
- **Estratégico** (C-suite, directores) — 3-5 personas
- **Táctico** (gerentes, coordinadores) — 8-12 personas  
- **Operativo** (analistas, operadores) — 15-20 personas

Esto permite detectar **brechas de percepción** entre niveles. Por ejemplo:
- Dirección piensa que el proceso funciona bien (score: 8/10)
- Operarios reportan problemas graves (score: 3/10)
- **Delta_sigma = 2.5** → Brecha crítica → Escala a humano

---

## 📊 CÓMO DEBERÍA FUNCIONAR (Diseño Completo)

### Fase 1: Diseño de la Encuesta (Agentes G09a-G09c)

```
┌─────────────────────────────────────────────────────────────┐
│ DIAGNÓSTICO CREADO                                          │
│ Cliente: "Acme Logistics"                                   │
│ Problema: "Entregas retrasadas"                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G01-G08: Investigación y Mapeo                              │
│ - G05 detecta 6 brechas (GAP-01 a GAP-06)                  │
│ - G05 formula 6 hipótesis (H01 a H06)                      │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G09a: Diseñador de Preguntas                                │
│                                                              │
│ Genera 45 preguntas distribuidas así:                       │
│ - 15 preguntas para TODOS los roles (comunes)              │
│ - 10 preguntas solo para Estratégico                       │
│ - 12 preguntas solo para Táctico                           │
│ - 8 preguntas solo para Operativo                          │
│                                                              │
│ Agrupadas en 5 dimensiones:                                 │
│ - DIM-01: Planificación y coordinación                     │
│ - DIM-02: Comunicación interna                             │
│ - DIM-03: Recursos y herramientas                          │
│ - DIM-04: Procesos y procedimientos                        │
│ - DIM-05: Liderazgo y cultura                              │
│                                                              │
│ Tipos de pregunta:                                          │
│ - 38 preguntas Likert 1-5                                  │
│ - 7 preguntas abiertas (texto libre)                       │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G09b: Ramificación                                          │
│                                                              │
│ Define lógica de salto:                                     │
│ - Si Q05 < 3 → mostrar Q05a (profundizar problema)         │
│ - Si rol = "Estratégico" → saltar Q12-Q18 (operativas)     │
│ - Si Q20 = "Sí" → mostrar Q21 (seguimiento)                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G09c: Validación                                            │
│                                                              │
│ Valida el instrumento:                                      │
│ - Cada dimensión tiene ≥ 4 preguntas ✓                     │
│ - No hay preguntas ambiguas ✓                              │
│ - IRR estimado: α = 0.78 (> 0.70) ✓                        │
│ - Veredicto: APROBADO                                       │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ CREAR SURVEY SESSION                                        │
│                                                              │
│ SurveySession:                                              │
│   id: "550e8400-e29b-41d4-a716-446655440000"               │
│   diagnostic_id: "abc123"                                   │
│   token: "7f3d9c2a-1b4e-4f8a-9d2c-5e6f7a8b9c0d"           │
│   questions: { ... output de G09a ... }                     │
│   branching: { ... output de G09b ... }                     │
│   status: "open"                                            │
│   min_responses: 5                                          │
│   target_responses: 20                                      │
│   responses_count: 0                                        │
│                                                              │
│ URL generada:                                               │
│ https://arhiax.app/survey/7f3d9c2a-1b4e-4f8a-9d2c-5e6f7a8b9c0d
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ PIPELINE SE PAUSA                                           │
│ Estado del diagnóstico: "awaiting_responses"               │
│                                                              │
│ El consultor recibe:                                        │
│ - URL de la encuesta                                        │
│ - Instrucciones para compartir con empleados                │
│ - Dashboard muestra: "0/20 respuestas recibidas"           │
└─────────────────────────────────────────────────────────────┘
```

---

### Fase 2: Recolección de Respuestas (Empleados)

```
┌─────────────────────────────────────────────────────────────┐
│ EMPLEADO ABRE LA URL                                        │
│ https://arhiax.app/survey/7f3d9c2a...                      │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ PANTALLA 1: Bienvenida                                      │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Diagnóstico Organizacional — Acme Logistics          │   │
│ │                                                       │   │
│ │ Estamos realizando un diagnóstico para mejorar       │   │
│ │ nuestros procesos. Tus respuestas son anónimas       │   │
│ │ y confidenciales.                                     │   │
│ │                                                       │   │
│ │ Tiempo estimado: 12 minutos                          │   │
│ │                                                       │   │
│ │ Selecciona tu rol:                                    │   │
│ │ ○ Estratégico (Director, C-suite)                    │   │
│ │ ○ Táctico (Gerente, Coordinador)                     │   │
│ │ ● Operativo (Analista, Operador)  ← seleccionado    │   │
│ │                                                       │   │
│ │           [Comenzar Encuesta]                         │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ PANTALLA 2: Preguntas (Adaptadas por Rol)                  │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Pregunta 1 de 23                                      │   │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │   │
│ │                                                       │   │
│ │ Dimensión: Planificación y coordinación              │   │
│ │                                                       │   │
│ │ ¿Con qué frecuencia recibes información clara        │   │
│ │ sobre las prioridades del día?                       │   │
│ │                                                       │   │
│ │ 1 ○ Nunca                                            │   │
│ │ 2 ○ Rara vez                                         │   │
│ │ 3 ○ A veces                                          │   │
│ │ 4 ● Frecuentemente  ← seleccionado                  │   │
│ │ 5 ○ Siempre                                          │   │
│ │                                                       │   │
│ │                    [← Anterior]  [Siguiente →]       │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ PANTALLA 3: Pregunta Abierta                                │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Pregunta 18 de 23                                     │   │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │   │
│ │                                                       │   │
│ │ Describe el principal obstáculo que enfrentas        │   │
│ │ en tu trabajo diario:                                │   │
│ │                                                       │   │
│ │ ┌───────────────────────────────────────────────┐   │   │
│ │ │ No tenemos acceso al sistema de inventario    │   │
│ │ │ en tiempo real, entonces tenemos que llamar   │   │
│ │ │ al almacén cada vez que necesitamos verificar │   │
│ │ │ stock. Esto retrasa las entregas.             │   │
│ │ │                                                │   │
│ │ └───────────────────────────────────────────────┘   │   │
│ │                                                       │   │
│ │                    [← Anterior]  [Siguiente →]       │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ PANTALLA 4: Confirmación                                    │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ ✓ Encuesta Completada                                │   │
│ │                                                       │   │
│ │ Gracias por tu participación. Tus respuestas         │   │
│ │ ayudarán a mejorar nuestros procesos.                │   │
│ │                                                       │   │
│ │ Tus respuestas han sido guardadas de forma anónima.  │   │
│ │                                                       │   │
│ │              [Cerrar]                                 │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ GUARDAR RESPUESTA EN BD                                     │
│                                                              │
│ SurveyResponse:                                             │
│   id: "resp-001"                                            │
│   session_id: "550e8400-..."                                │
│   respondent_hash: "sha256(session_id + anon_id)"          │
│   role: "Operativo"                                         │
│   answers: {                                                │
│     "Q01": 4,                                               │
│     "Q02": 3,                                               │
│     "Q03": 5,                                               │
│     ...                                                     │
│   }                                                         │
│   open_answers: {                                           │
│     "QA01": "No tenemos acceso al sistema..."              │
│   }                                                         │
│   completed: true                                           │
│                                                              │
│ SurveySession.responses_count += 1  (ahora = 1)            │
└─────────────────────────────────────────────────────────────┘
```

---

### Fase 3: Monitoreo y Continuación (Consultor)

```
┌─────────────────────────────────────────────────────────────┐
│ DASHBOARD DEL CONSULTOR                                     │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Diagnóstico: Acme Logistics                          │   │
│ │ Estado: Esperando respuestas                         │   │
│ │                                                       │   │
│ │ Progreso de Encuesta:                                │   │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │   │
│ │ 12 / 20 respuestas (60%)                             │   │
│ │                                                       │   │
│ │ Por rol:                                             │   │
│ │ • Estratégico:  2 / 3  ━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│ │ • Táctico:      5 / 8  ━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│ │ • Operativo:    5 / 9  ━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│ │                                                       │   │
│ │ Mínimo requerido: 5 respuestas ✓                    │   │
│ │                                                       │   │
│ │ [Cerrar Encuesta y Continuar Análisis]              │   │
│ │ [Esperar más respuestas]                             │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ TRIGGER AUTOMÁTICO O MANUAL                                 │
│                                                              │
│ Opción A: Automático                                        │
│ - Cuando responses_count >= min_responses (5)               │
│ - Sistema cierra la encuesta automáticamente                │
│ - Continúa con G10a (scoring)                               │
│                                                              │
│ Opción B: Manual                                            │
│ - Consultor decide cuándo cerrar                            │
│ - Puede esperar más respuestas si quiere                    │
│ - Click en "Cerrar Encuesta y Continuar"                    │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ CERRAR ENCUESTA                                             │
│                                                              │
│ SurveySession:                                              │
│   status: "closed"                                          │
│   closed_at: "2026-04-26T15:30:00Z"                        │
│   responses_count: 12                                       │
│                                                              │
│ Diagnóstico:                                                │
│   status: "running"  (vuelve a running)                     │
└─────────────────────────────────────────────────────────────┘
```

---

### Fase 4: Análisis con Datos Reales (Agentes G10a-G14)

```
┌─────────────────────────────────────────────────────────────┐
│ G10a: Scoring Psicométrico                                  │
│                                                              │
│ Procesa las 12 respuestas reales:                           │
│                                                              │
│ Scores por dimensión:                                       │
│ - DIM-01 (Planificación): 3.2 / 5.0                        │
│ - DIM-02 (Comunicación):  2.8 / 5.0                        │
│ - DIM-03 (Recursos):      2.1 / 5.0  ← crítico             │
│ - DIM-04 (Procesos):      3.5 / 5.0                        │
│ - DIM-05 (Liderazgo):     3.8 / 5.0                        │
│                                                              │
│ Scores por rol:                                             │
│ - Estratégico:  3.9 / 5.0  (optimista)                     │
│ - Táctico:      3.2 / 5.0  (moderado)                      │
│ - Operativo:    2.4 / 5.0  (crítico)                       │
│                                                              │
│ Delta_sigma:                                                │
│ - Estratégico vs Operativo en DIM-03: δ = 2.7  ← CRÍTICO   │
│   (Dirección piensa que hay recursos, operarios no)        │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G10b: Psicometría                                           │
│                                                              │
│ Cronbach Alpha: 0.82  (buena consistencia interna)         │
│ IRR (Krippendorff): 0.76  (acuerdo moderado-alto)          │
│ Validez convergente: 0.78                                   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G11a: Análisis Bayesiano                                    │
│                                                              │
│ Actualiza hipótesis con evidencia real:                     │
│                                                              │
│ H01: "Falta de visibilidad de inventario"                  │
│   Prior: 0.70 → Posterior: 0.94  ✓ CONFIRMADA              │
│   Evidencia: DIM-03 score bajo + respuestas abiertas       │
│                                                              │
│ H02: "Comunicación deficiente entre áreas"                 │
│   Prior: 0.65 → Posterior: 0.88  ✓ CONFIRMADA              │
│                                                              │
│ H03: "Falta de capacitación"                               │
│   Prior: 0.60 → Posterior: 0.45  ✗ RECHAZADA               │
│                                                              │
│ Brecha crítica detectada:                                   │
│ - Delta_sigma = 2.7 en DIM-03                               │
│ - Escala a humano (HIC MEDIUM)                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G11b: Análisis NLP                                          │
│                                                              │
│ Analiza las 7 respuestas abiertas:                         │
│                                                              │
│ Temas principales:                                          │
│ 1. "Sistema de inventario" (mencionado 8 veces)            │
│ 2. "Retrasos" (mencionado 6 veces)                         │
│ 3. "Comunicación con almacén" (mencionado 5 veces)         │
│                                                              │
│ Sentimiento por rol:                                        │
│ - Estratégico: 60% positivo, 30% neutral, 10% negativo     │
│ - Táctico:     40% positivo, 30% neutral, 30% negativo     │
│ - Operativo:   20% positivo, 30% neutral, 50% negativo     │
│                                                              │
│ Cita representativa:                                        │
│ "No tenemos acceso al sistema de inventario en tiempo      │
│  real, entonces tenemos que llamar al almacén cada vez     │
│  que necesitamos verificar stock. Esto retrasa las         │
│  entregas."                                                 │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G12-G14: Hallazgos, Redacción y QA                         │
│                                                              │
│ Genera informe ejecutivo con datos reales                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ❌ CÓMO FUNCIONA AHORA (Realidad Actual)

```
┌─────────────────────────────────────────────────────────────┐
│ G09a diseña 45 preguntas ✓                                 │
│ G09b define ramificación ✓                                 │
│ G09c valida instrumento ✓                                  │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ ❌ NO SE CREA SurveySession                                 │
│ ❌ NO SE GENERA URL                                         │
│ ❌ NO HAY FORMULARIO PÚBLICO                                │
│ ❌ PIPELINE CONTINÚA INMEDIATAMENTE                         │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ G10a-G14 trabajan con DATOS MOCK                            │
│                                                              │
│ executor.py línea 85-120:                                   │
│ mock_outputs = {                                            │
│   "g10a_scoring": {                                         │
│     "scoring_matrix": {},  ← VACÍO                          │
│     "composite_scores": {},                                 │
│   },                                                        │
│   "g11a_bayesiano": {                                       │
│     "posterior_probabilities": {},  ← VACÍO                 │
│   }                                                         │
│ }                                                           │
│                                                              │
│ El informe final tiene datos simulados, no reales          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 LO QUE HAY QUE IMPLEMENTAR

### 1. Backend — Endpoints de Encuesta

**Archivo:** `back-api/src/api/routers/survey.py` (NUEVO)

```python
@router.get("/survey/{token}")
async def get_survey(token: str, db: AsyncSession = Depends(get_db)):
    """Endpoint público — retorna preguntas de la encuesta."""
    session = await db.execute(
        select(SurveySession).where(SurveySession.token == token)
    )
    session = session.scalar_one_or_none()
    
    if not session or session.status != "open":
        raise HTTPException(404, "Survey not found or closed")
    
    return {
        "questions": session.questions,
        "branching": session.branching,
        "organization_name": session.diagnostic.organization_name,
    }

@router.post("/survey/{token}/submit")
async def submit_response(
    token: str,
    body: SurveyResponseIn,
    db: AsyncSession = Depends(get_db)
):
    """Endpoint público — guarda respuesta anónima."""
    # Crear SurveyResponse
    # Incrementar responses_count
    # Si responses_count >= min_responses → trigger pipeline
```

### 2. Backend — Lógica de Pausa/Continuación

**Archivo:** `back-api/src/api/pipeline_runner.py`

```python
# Después de G09c:
if tool_name == "g09c_validacion":
    # Crear SurveySession
    session = SurveySession(
        diagnostic_id=diagnostic_id,
        token=str(uuid.uuid4()),
        questions=context["g09a_preguntas"],
        branching=context["g09b_ramificacion"],
    )
    db.add(session)
    
    # Pausar pipeline
    diagnostic.status = "awaiting_responses"
    await db.commit()
    
    # NO continuar con G10a
    break
```

### 3. Frontend — Página Pública

**Archivo:** `front/src/app/survey/[token]/page.tsx` (NUEVO)

```tsx
export default function SurveyPage({ params }: { params: { token: string } }) {
  const [role, setRole] = useState<string | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  
  // Fetch questions
  // Render formulario adaptativo
  // Submit respuestas
}
```

---

## 📊 RESUMEN

### Estado Actual
- ✅ Modelos de BD existen
- ✅ G09a-G09c diseñan la encuesta
- ❌ No se crea SurveySession
- ❌ No hay formulario público
- ❌ Pipeline no se pausa
- ❌ G10a-G14 usan datos mock

### Lo que falta
1. Crear `SurveySession` después de G09c
2. Pausar pipeline en estado "awaiting_responses"
3. Endpoints públicos `/survey/{token}`
4. Página pública `/survey/[token]`
5. Trigger para continuar cuando `responses_count >= min_responses`

### Impacto
Sin la encuesta real, **el diagnóstico Multi-Rater no tiene valor** porque trabaja con datos simulados. Es como hacer un diagnóstico médico sin examinar al paciente.

---

¿Quieres que implemente la encuesta completa?
