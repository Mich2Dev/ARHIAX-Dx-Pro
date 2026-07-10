"""Prompts del Phenomenon Engine (P02–P07). P01 es determinista en código."""

P02_EPOCHE = """Eres un consultor fenomenológico. El cliente ya nombró su problema; muchas veces ese nombre es una SOLUCIÓN disfrazada de diagnóstico.

MATERIAL DEL CASO (JSON):
{p01_reception}

TAREA — Epoqué:
1. Lista los diagnósticos que el cliente (o el intake) ya trae ("falta personal", "cuello de botella", etc.).
2. Para cada uno explica por qué es un nombre ingenuo o prescribe una solución.
3. Describe qué aparece al suspender esos nombres (el fenómeno antes de interpretarlo).
4. Usa SOLO el material del caso. No inventes sector, procesos ni personas no mencionados.

Responde ÚNICAMENTE JSON:
{{
  "naive_diagnoses": [
    {{"label": "...", "why_prescribes_solution": "...", "what_it_hides": "..."}}
  ],
  "suspended_view": "descripción del fenómeno sin nombres falsos (2-4 oraciones)",
  "evidence_quotes": ["cita o dato del intake que sustenta"]
}}
"""

P03_CONVERGENCE = """Eres un analista Governex. Aplicas lentes configurables para converger en UN solo fenómeno nombrado.

EPOQUÉ:
{p02_epoche}

LENTES (aplica cada una con pregunta operativa y un hallazgo de 1-2 oraciones):
{lens_pack}

REGLAS:
- Los hallazgos deben anclarse al caso (síntoma, incidentes, sector, procesos).
- Al final converge en phenomenon_named: un nombre verdadero (no "cuello de botella" ni "falta de personal" salvo refutación).
- lenses_used debe tener exactamente una entrada por lente del pack.

JSON:
{{
  "lenses_used": [
    {{"id": "ver", "question": "...", "finding": "...", "tradition": "Husserl/Heidegger"}}
  ],
  "phenomenon_named": "nombre del fenómeno (ej. criterio cautivo, saber no sedimentado)",
  "convergence_summary": "2-3 oraciones integrando los hallazgos",
  "anchor_terms": ["términos clave del caso para validar downstream"]
}}
"""

P04_CONTRADICTION = """Formulas la contradicción maestra del caso (estilo TRIZ/Salamatov).

FENÓMENO NOMBRADO:
{p03_convergence}

CONTEXTO:
{p01_reception}

JSON:
{{
  "technical_contradiction": {{
    "improving": "qué parámetro se intenta mejorar",
    "worsening": "qué parámetro empeora con la solución obvia del cliente",
    "statement": "una oración"
  }},
  "physical_contradiction": {{
    "parameter": "qué debe estar en dos lugares/formas a la vez",
    "statement": "una oración"
  }},
  "resolution_motor": {{
    "name": "nombre corto del motor (ej. separación 80/20 por condición de tipicidad)",
    "rule": "lo repetible/típico → sistema; lo excepcional → persona",
    "ideal_direction": "hacia dónde evoluciona la operación"
  }}
}}
"""

P05_LOCALIZATION = """Localiza subsistemas y acoplamientos rotos (Luhmann aplicado).

FENÓMENO Y MOTOR:
{p04_contradiction}

MATERIAL:
{p01_reception}

Identifica 2-5 subsistemas/procesos del caso y dónde la información cruza por personas/WhatsApp en vez del sistema.

JSON:
{{
  "core_subsystems": [
    {{"id": "...", "name": "...", "function": "...", "pain_signal": "..."}}
  ],
  "broken_couplings": [
    {{"from": "...", "to": "...", "symptom": "...", "human_medium": "quién hace de puente"}}
  ],
  "hinge_question": "la pregunta bisagra que decide el primer entregable (ej. ¿lista sale del APU o se rearma?)",
  "priority_order": ["orden de ataque por dependencia del fenómeno, no por espectacularidad"]
}}
"""

P06_KILL_CRITIC = """Ataca la propia tesis antes que el cliente. Kill Critic.

ANÁLISIS PREVIO:
{p03_convergence}
{p04_contradiction}
{p05_localization}

Evalúa riesgos típicos adaptados al caso:
- dataset insuficiente
- frontera 80/20 mal calibrada
- dependencia elegida (founder)
- alcance diluido (otro negocio mezclado)

Cada riesgo: severity "block" o "warn", test concreto, passed true/false según evidencia del intake.

JSON:
{{
  "risks": [
    {{"id": "...", "description": "...", "severity": "block|warn", "test": "...", "passed": true, "mitigation": "..."}}
  ],
  "gates_passed": true,
  "blocking_reasons": [],
  "calibration_needs": ["qué falta medir o preguntar en descubrimiento"]
}}
"""

P07_DERIVATION = """Deriva el paquete de documentos y el siguiente paso operativo.

KILL CRITIC:
{p06_kill_critic}

LOCALIZACIÓN:
{p05_localization}

FENÓMENO:
{p03_convergence}

Tipos permitidos: internal_phenomenon, discovery_form, commercial_proposal, horizon_map, executive_report, seed_data_template, survey_instrument, architecture_tr, sprint_spec.

JSON:
{{
  "engagement_mode": "diagnosis_only|diagnosis_and_proposal|implementation",
  "recommended_documents": [
    {{"type": "...", "priority": 1, "audience": "...", "purpose": "...", "blocked_until": null}}
  ],
  "recommended_instruments": ["discovery_form", "seed_data_template"],
  "use_survey": true,
  "survey_rationale": "por qué sí o no encuesta Likert",
  "next_operational_step": "una oración para el consultor",
  "commercial_safe": true
}}
"""

DEFAULT_LENS_PACK = """[
  {"id": "ver", "tradition": "Husserl/Heidegger", "question": "¿Qué es antes del nombre falso?"},
  {"id": "interpretar", "tradition": "Gadamer", "question": "¿Qué tradición tácita existe pero no está escrita?"},
  {"id": "ampliar", "tradition": "Boaventura", "question": "¿Qué saber se produce como ausencia?"},
  {"id": "localizar", "tradition": "Luhmann", "question": "¿Dónde rompe el acoplamiento entre subsistemas?"},
  {"id": "proteger", "tradition": "Benjamin", "question": "¿Qué memoria/huella se pierde?"},
  {"id": "resolver", "tradition": "TRIZ/Salamatov", "question": "¿Cuál es la contradicción y su separación?"},
  {"id": "transformar", "tradition": "Dewey", "question": "¿Cómo aprende la operación de sí misma?"}
]"""
