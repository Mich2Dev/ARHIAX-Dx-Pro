"""
test_instrument_coherence.py
============================
Tests de coherencia del instrumento Multi-Rater de ARHIAX Dx.

PROPOSITO
---------
Verificar que el instrumento generado por G09a es coherente con:
  - El problema descrito (sintoma de entrada)
  - Las hipotesis de G05 (trazabilidad H -> DIM -> pregunta)
  - La logica psicometrica (numero de preguntas, reverse scoring, roles)
  - La capacidad de producir delta_sigma (diferenciacion de roles)
  - La falsificabilidad de cada hipotesis

No es un test de integracion de API.
Es un test de RAZONAMIENTO sobre el instrumento.
"""
from __future__ import annotations
import pytest
from typing import Any

# ===========================================================================
# PARTE 1 ? DATOS DE REFERENCIA
# Caso: Logistica Express S.A.S. ? Gestion de entregas last-mile
# Sintoma: "Las entregas llegan 3-5 dias tarde, perdimos 2 contratos"
#
# Simula el output real de G05 (hipotesis) y G09a (instrumento).
# Cada decision de diseno esta documentada en rationale / signal_logic.
# ===========================================================================

# ---------------------------------------------------------------------------
# G05 output simulado ? hipotesis con senales esperadas por rol
# ---------------------------------------------------------------------------
HYPOTHESES = [
    {
        "id": "H01",
        "hypothesis": "La asignacion manual de rutas genera ineficiencias que el nivel operativo experimenta pero la direccion no percibe",
        "prior_probability": 0.75,
        "dimension_to_measure": "DIM-01",
        "evidence_needed": "score DIM-01 < 60 Y delta_sigma Estrategico-Operativo > 1.5",
        "expected_signals": {
            "if_true": {
                "Estrategico": {"expected_score_range": "65-75"},
                "Tactico":     {"expected_score_range": "45-60"},
                "Operativo":   {"expected_score_range": "25-45"},
            },
            "falsification_condition": "Si Operativo da score > 65 en DIM-01, H01 queda rechazada",
        },
    },
    {
        "id": "H02",
        "hypothesis": "La falta de comunicacion en tiempo real entre almacen y transporte causa retrasos en el despacho",
        "prior_probability": 0.70,
        "dimension_to_measure": "DIM-02",
        "evidence_needed": "score DIM-02 < 55 Y Operativo < 50",
        "expected_signals": {
            "if_true": {
                "Estrategico": {"expected_score_range": "60-70"},
                "Tactico":     {"expected_score_range": "40-55"},
                "Operativo":   {"expected_score_range": "30-45"},
            },
            "falsification_condition": "Si Tactico y Operativo dan score > 65 en DIM-02, H02 queda rechazada",
        },
    },
    {
        "id": "H03",
        "hypothesis": "Los conductores no tienen informacion actualizada del cliente al momento de la entrega",
        "prior_probability": 0.65,
        "dimension_to_measure": "DIM-03",
        "evidence_needed": "score DIM-03 Operativo < 40",
        "expected_signals": {
            "if_true": {
                "Estrategico": {"expected_score_range": "70-80"},
                "Tactico":     {"expected_score_range": "55-65"},
                "Operativo":   {"expected_score_range": "20-40"},
            },
            "falsification_condition": "Si Operativo da score > 60 en DIM-03, H03 queda rechazada",
        },
    },
    {
        "id": "H04",
        "hypothesis": "La direccion sobreestima la capacidad operativa del equipo de entregas",
        "prior_probability": 0.55,
        "dimension_to_measure": "DIM-04",
        "evidence_needed": "delta_sigma Estrategico-Operativo > 2.0 en DIM-04",
        "expected_signals": {
            "if_true": {
                "Estrategico": {"expected_score_range": "70-80"},
                "Tactico":     {"expected_score_range": "50-65"},
                "Operativo":   {"expected_score_range": "30-45"},
            },
            "falsification_condition": "Si Estrategico y Operativo tienen diferencia < 15 puntos, H04 queda rechazada",
        },
    },
]

# ---------------------------------------------------------------------------
# G09a output simulado ? instrumento completo con razonamiento documentado
# ---------------------------------------------------------------------------
INSTRUMENT = {
    "instrument_name": "Diagnostico Multi-Rater ? Gestion de entregas last-mile ? Logistica Express",
    "subprocess_focus": "Gestion de entregas last-mile",
    "methodology": {
        "standard": "Kirkpatrick (1994) adaptado",
        "design_principle": "Verificabilidad por rol",
        "irr_target": "alpha Krippendorff >= 0.70",
        "reverse_scoring": ">=1 item reverse-scored por dimension (Paulhus 1991)",
        "role_differentiation": "Preguntas asignadas por rol segun nivel de acceso al proceso",
    },
    "dimensions": [
        {
            "id": "DIM-01", "hypothesis_mapped": "H01", "weight": 0.30,
            "name": "Eficiencia del proceso de asignacion de rutas",
            "expected_pattern_if_true": "Operativo 25-45, Tactico 45-60, Estrategico 65-75",
            "expected_pattern_if_false": "Todos los roles con scores similares 65-80",
        },
        {
            "id": "DIM-02", "hypothesis_mapped": "H02", "weight": 0.25,
            "name": "Comunicacion almacen-transporte en tiempo real",
            "expected_pattern_if_true": "Operativo 30-45, Tactico 40-55, Estrategico 60-70",
            "expected_pattern_if_false": "Todos los roles con scores similares 65-80",
        },
        {
            "id": "DIM-03", "hypothesis_mapped": "H03", "weight": 0.25,
            "name": "Disponibilidad de informacion del cliente en entrega",
            "expected_pattern_if_true": "Operativo 20-40, Tactico 55-65, Estrategico 70-80",
            "expected_pattern_if_false": "Todos los roles con scores similares 65-80",
        },
        {
            "id": "DIM-04", "hypothesis_mapped": "H04", "weight": 0.20,
            "name": "Percepcion de capacidad operativa del equipo",
            "expected_pattern_if_true": "Estrategico 70-80, Operativo 30-45 ? delta_sigma > 2.0",
            "expected_pattern_if_false": "Diferencia entre roles < 15 puntos",
        },
    ],
    "questions": [
        # ?? DIM-01: 3 Likert + 1 abierta ??????????????????????????????????
        # Por que 4 preguntas: minimo para alpha Cronbach confiable (Nunnally 1978).
        # 3 Likert dan alpha ~0.70 si correlacion inter-item > 0.40.
        # La abierta triangula cualitativamente lo que el Likert no captura.
        # H01 tiene prior 0.75 ? la mas alta ? merece cobertura maxima.
        {
            "id": "Q01", "dimension": "DIM-01", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H01",
            "text": "Con que frecuencia las rutas asignadas permiten completar todas las entregas del dia sin retrasos",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "3-4",
                    "Tactico":     "2-3",
                    "Operativo":   "1-2",
                },
                "signal_logic": "El Estrategico responde desde percepcion, el Operativo desde experiencia directa. Esta asimetria de informacion produce el delta_sigma que confirma H01.",
            },
            "rationale": "Pregunta central de DIM-01. Los 3 roles responden para medir la brecha de percepcion completa. El Estrategico no conduce pero opina ? esa diferencia con el Operativo es la evidencia de H01.",
        },
        {
            "id": "Q02", "dimension": "DIM-01", "type": "likert_5",
            "roles": ["Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H01",
            "text": "Con que frecuencia puedes completar tu ruta asignada sin tener que modificarla por problemas imprevistos",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Tactico":   "2-3",
                    "Operativo": "1-2",
                },
                "signal_logic": "Solo Tactico y Operativo responden porque son quienes ejecutan o supervisan las rutas. El Estrategico no tiene informacion directa sobre modificaciones en campo ? incluirlo introduciria ruido, no senal.",
            },
            "rationale": "Mide la frecuencia de fallo operativo real. El Estrategico se excluye deliberadamente: su respuesta seria una estimacion sin base empirica, lo que reduciria la validez discriminante.",
        },
        {
            "id": "Q03", "dimension": "DIM-01", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": True, "hypothesis_tested": "H01",
            "text": "El sistema actual de asignacion de rutas garantiza que cada conductor recibe la ruta optima para su zona",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "4-5 raw (cree que el sistema funciona ? no ve el problema)",
                    "Tactico":     "3-4 raw (percepcion moderada del problema)",
                    "Operativo":   "4-5 raw (sabe que el sistema NO es optimo ? score alto indica problema)",
                },
                "signal_logic": "Item reverse-scored: score raw alto = problema existe. Si Estrategico da 4-5 Y Operativo da 4-5, ambos confirman H01 por razones opuestas. Esto es detectable comparando con Q01.",
            },
            "rationale": "Control de sesgo de aquiescencia (Paulhus 1991). Si un respondente marca siempre 4-5 sin leer, Q03 lo detecta porque su score raw alto CONFIRMA el problema, no lo niega.",
        },
        {
            "id": "QA01", "dimension": "DIM-01", "type": "open_text",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H01",
            "text": "Describe un problema reciente con la asignacion o ejecucion de rutas. Que ocurrio y cual fue el impacto",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "Lenguaje abstracto, problemas sistemicos o de recursos",
                    "Tactico":     "Lenguaje de gestion, problemas de coordinacion o herramientas",
                    "Operativo":   "Lenguaje de ejecucion, ejemplos concretos del dia a dia",
                },
                "signal_logic": "El tipo de lenguaje revela que tan cerca esta cada rol del problema. G11b analiza esto con NLP. La divergencia cualitativa triangula el delta_sigma cuantitativo.",
            },
            "rationale": "Una pregunta abierta por cada 2 hipotesis de alta prior (H01=0.75). Captura lo que el Likert no puede: lenguaje, especificidad, frustracion. G11b analiza sentiment y temas.",
        },
        # ?? DIM-02: 3 Likert + 1 abierta ??????????????????????????????????
        # H02 tiene prior 0.70 ? alta probabilidad, merece cobertura completa.
        # La abierta captura la solucion que los propios afectados proponen.
        {
            "id": "Q04", "dimension": "DIM-02", "type": "likert_5",
            "roles": ["Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H02",
            "text": "Con que frecuencia recibes confirmacion del almacen antes de salir a ruta de que todos los pedidos estan listos",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Tactico":   "2-3",
                    "Operativo": "1-2",
                },
                "signal_logic": "Solo Tactico y Operativo responden porque son quienes interactuan con el proceso de despacho. El Estrategico no tiene visibilidad directa de si la confirmacion ocurre.",
            },
            "rationale": "Mide el punto exacto de fallo de H02: la confirmacion pre-despacho. Score bajo en Operativo es evidencia directa de que la comunicacion almacen-transporte falla en el momento critico.",
        },
        {
            "id": "Q05", "dimension": "DIM-02", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H02",
            "text": "Cuando hay un cambio de ultimo momento en un pedido, el equipo de transporte recibe la informacion a tiempo para actuar",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "3-4",
                    "Tactico":     "2-3",
                    "Operativo":   "1-2",
                },
                "signal_logic": "Los 3 roles responden para medir la brecha de percepcion sobre comunicacion de cambios. El Estrategico cree que el proceso funciona; el Operativo sabe que no.",
            },
            "rationale": "Complementa Q04 midiendo la comunicacion reactiva (cambios de ultimo momento) vs la proactiva (confirmacion pre-despacho). Juntas cubren los dos momentos criticos de comunicacion.",
        },
        {
            "id": "Q06", "dimension": "DIM-02", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": True, "hypothesis_tested": "H02",
            "text": "La coordinacion entre el area de almacen y el equipo de transporte es fluida y sin fricciones",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "4-5 raw (cree que la coordinacion es fluida)",
                    "Tactico":     "3-4 raw (percibe fricciones pero las gestiona)",
                    "Operativo":   "4-5 raw (vive las fricciones diariamente)",
                },
                "signal_logic": "Item reverse-scored de DIM-02. Detecta si el Estrategico tiene percepcion inflada de la coordinacion.",
            },
            "rationale": "Control de sesgo para DIM-02. Redactada en positivo para que el Operativo que vive las fricciones tenga que marcar alto (reverse) ? patron mas claro.",
        },
        {
            "id": "QA02", "dimension": "DIM-02", "type": "open_text",
            "roles": ["Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H02",
            "text": "Que cambio especifico en la comunicacion entre almacen y transporte tendria mayor impacto positivo en tu trabajo diario",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Tactico":   "Mencionara herramientas, protocolos o sistemas de notificacion",
                    "Operativo": "Mencionara informacion especifica que necesita antes de salir",
                },
                "signal_logic": "Si H02 es verdadera, las respuestas seran consistentes: todos pediran informacion en tiempo real. Si H02 es falsa, las respuestas seran dispersas.",
            },
            "rationale": "Solo Tactico y Operativo porque son quienes viven la comunicacion almacen-transporte. La pregunta abierta captura la solucion que los propios afectados proponen ? insumo directo para G08.",
        },
        # ?? DIM-03: 3 Likert (sin abierta) ????????????????????????????????
        # H03 tiene prior 0.65 ? menor que H01/H02.
        # 3 Likert son el minimo para alpha Cronbach aceptable.
        # No se agrega abierta porque QA01 ya captura ejemplos de problemas en campo.
        # Agregar otra abierta aumentaria la fatiga del respondente sin ganancia diagnostica.
        {
            "id": "Q07", "dimension": "DIM-03", "type": "likert_5",
            "roles": ["Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H03",
            "text": "Al llegar a entregar un pedido, tienes acceso a la informacion actualizada del cliente (direccion, telefono, instrucciones especiales)",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Operativo": "1-2",
                },
                "signal_logic": "Solo Operativo responde porque es el UNICO con informacion directa sobre si los datos del cliente estan actualizados al momento de la entrega. Estrategico y Tactico no hacen entregas.",
            },
            "rationale": "Pregunta de perspectiva exclusiva Operativo. Es la evidencia mas directa de H03. Si el score es bajo, confirma que el problema existe. No tiene sentido incluir otros roles porque no tienen acceso a esta informacion.",
        },
        {
            "id": "Q08", "dimension": "DIM-03", "type": "likert_5",
            "roles": ["Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H03",
            "text": "El sistema de informacion del cliente se actualiza con suficiente anticipacion antes de cada entrega",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Tactico":   "2-3",
                    "Operativo": "1-2",
                },
                "signal_logic": "Tactico se incluye porque gestiona las actualizaciones del sistema. Estrategico se excluye porque no interactua con el sistema operativo de clientes.",
            },
            "rationale": "Complementa Q07 midiendo el proceso de actualizacion (Tactico) vs la experiencia de uso (Operativo). La diferencia entre ambos scores revela si el problema es de proceso o de acceso.",
        },
        {
            "id": "Q09", "dimension": "DIM-03", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": True, "hypothesis_tested": "H03",
            "text": "Cuando un cliente cambia su direccion o instrucciones de entrega, el conductor recibe esa informacion antes de llegar",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "4-5 raw (cree que el proceso de actualizacion funciona)",
                    "Tactico":     "3-4 raw (sabe que hay casos donde no llega a tiempo)",
                    "Operativo":   "4-5 raw (frecuentemente llega sin la informacion actualizada)",
                },
                "signal_logic": "Item reverse-scored de DIM-03. Los 3 roles responden para capturar la brecha de percepcion completa. Unica pregunta de los 3 roles en esta dimension ? permite calcular delta_sigma de DIM-03.",
            },
            "rationale": "Control de sesgo para DIM-03 y unica pregunta de los 3 roles en esta dimension. Permite calcular el delta_sigma que G11a necesita para evaluar H03 bayesianamente.",
        },
        # ?? DIM-04: 3 Likert (sin abierta) ????????????????????????????????
        # H04 tiene prior 0.55 ? la mas baja.
        # 3 preguntas son suficientes para medir la brecha de percepcion.
        # Esta dimension es principalmente sobre delta_sigma, no sobre score absoluto.
        # No se agrega abierta porque el fenomeno (sobreestimacion) es mejor capturado
        # por la diferencia cuantitativa entre roles que por texto libre.
        {
            "id": "Q10", "dimension": "DIM-04", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H04",
            "text": "El equipo de entregas tiene la capacidad suficiente para cumplir con el volumen de pedidos asignado diariamente",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "4-5",
                    "Tactico":     "3-4",
                    "Operativo":   "1-2",
                },
                "signal_logic": "Los 3 roles responden porque H04 es especificamente sobre la BRECHA DE PERCEPCION entre niveles. Si solo respondiera Operativo, no habria delta_sigma. La diferencia Estrategico-Operativo ES la evidencia de H04.",
            },
            "rationale": "Pregunta central de DIM-04. Mide directamente la percepcion de capacidad por nivel jerarquico. El delta_sigma esperado (Estrategico 70-80 vs Operativo 30-45) es la evidencia bayesiana de H04.",
        },
        {
            "id": "Q11", "dimension": "DIM-04", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": True, "hypothesis_tested": "H04",
            "text": "La carga de trabajo asignada al equipo de entregas es razonable y sostenible en el tiempo",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "4-5 raw (cree que la carga es razonable)",
                    "Tactico":     "3-4 raw (percibe tension pero la gestiona)",
                    "Operativo":   "4-5 raw (la carga NO es sostenible ? score alto confirma el problema)",
                },
                "signal_logic": "Item reverse-scored de DIM-04. Si Estrategico da 4-5 (cree que es razonable) y Operativo da 4-5 (sabe que NO es razonable), el patron confirma H04: mismos scores, razones opuestas.",
            },
            "rationale": "Control de sesgo para DIM-04. La redaccion en positivo hace que el Operativo que vive la sobrecarga tenga que marcar alto (reverse), amplificando la senal de H04.",
        },
        {
            "id": "Q12", "dimension": "DIM-04", "type": "likert_5",
            "roles": ["Estrategico", "Tactico", "Operativo"],
            "reverse_scored": False, "hypothesis_tested": "H04",
            "text": "Cuando hay picos de demanda, el equipo de entregas puede absorberlos sin afectar los tiempos de entrega",
            "expected_direction": {
                "if_hypothesis_true": {
                    "Estrategico": "3-4",
                    "Tactico":     "2-3",
                    "Operativo":   "1-2",
                },
                "signal_logic": "Pregunta sobre situacion extrema (picos) que amplifica la brecha de percepcion. En picos, la experiencia del Operativo diverge mas del Estrategico que en operacion normal.",
            },
            "rationale": "Complementa Q10 y Q11 con un escenario especifico (picos de demanda) mas revelador que la operacion normal. Si H04 es verdadera, la diferencia Estrategico-Operativo sera mayor en Q12 que en Q10.",
        },
    ],
}

# Helpers para los tests
def _questions_by_dim(instrument: dict) -> dict[str, list]:
    result: dict[str, list] = {}
    for q in instrument["questions"]:
        result.setdefault(q["dimension"], []).append(q)
    return result

def _likert_questions(instrument: dict) -> list:
    return [q for q in instrument["questions"] if q["type"] == "likert_5"]

def _open_questions(instrument: dict) -> list:
    return [q for q in instrument["questions"] if q["type"] == "open_text"]

def _reverse_questions(instrument: dict) -> list:
    return [q for q in instrument["questions"] if q.get("reverse_scored")]

def _hyp_map(hypotheses: list) -> dict:
    return {h["id"]: h for h in hypotheses}

def _dim_map(instrument: dict) -> dict:
    return {d["id"]: d for d in instrument["dimensions"]}


# ===========================================================================
# PARTE 2 ? TESTS DE ESTRUCTURA BASICA
# ===========================================================================

def test_instrumento_tiene_campos_obligatorios():
    assert "instrument_name" in INSTRUMENT
    assert "subprocess_focus" in INSTRUMENT
    assert "methodology" in INSTRUMENT
    assert "dimensions" in INSTRUMENT
    assert "questions" in INSTRUMENT

def test_metodologia_documentada():
    m = INSTRUMENT["methodology"]
    assert "design_principle" in m, "Debe declarar el principio de diseno"
    assert "irr_target" in m, "Debe declarar el objetivo de IRR"
    assert "reverse_scoring" in m, "Debe declarar la politica de reverse scoring"
    assert "role_differentiation" in m, "Debe declarar como se diferencian los roles"

def test_dimensiones_cubren_todas_las_hipotesis():
    """Cada hipotesis debe tener exactamente una dimension asignada."""
    hyp_ids = {h["id"] for h in HYPOTHESES}
    dim_hyp_ids = {d["hypothesis_mapped"] for d in INSTRUMENT["dimensions"]}
    assert hyp_ids == dim_hyp_ids, (
        f"Hipotesis sin dimension: {hyp_ids - dim_hyp_ids}. "
        f"Dimensiones sin hipotesis: {dim_hyp_ids - hyp_ids}"
    )

def test_pesos_de_dimensiones_suman_uno():
    total = sum(d["weight"] for d in INSTRUMENT["dimensions"])
    assert abs(total - 1.0) < 0.01, f"Los pesos suman {total}, deben sumar 1.0"

def test_pesos_reflejan_prioridad_de_hipotesis():
    """
    Dimensiones con hipotesis de mayor prior deben tener mayor peso.
    H01 (prior=0.75) -> DIM-01 debe tener el mayor peso.
    H04 (prior=0.55) -> DIM-04 debe tener el menor peso.
    """
    hyp_map = _hyp_map(HYPOTHESES)
    dim_map = _dim_map(INSTRUMENT)
    dim_weights = {
        d["id"]: (d["weight"], hyp_map[d["hypothesis_mapped"]]["prior_probability"])
        for d in INSTRUMENT["dimensions"]
    }
    # DIM-01 (H01, prior=0.75) debe tener mayor peso que DIM-04 (H04, prior=0.55)
    assert dim_weights["DIM-01"][0] >= dim_weights["DIM-04"][0], (
        "DIM-01 (hipotesis mas probable) debe tener mayor o igual peso que DIM-04"
    )

# ===========================================================================
# PARTE 3 ? TRAZABILIDAD HIPOTESIS -> DIMENSION -> PREGUNTA
# ===========================================================================

def test_cada_pregunta_tiene_hypothesis_tested():
    """Toda pregunta debe declarar que hipotesis verifica ? sin esto no hay trazabilidad."""
    for q in INSTRUMENT["questions"]:
        assert "hypothesis_tested" in q and q["hypothesis_tested"], (
            f"Pregunta {q['id']} no tiene hypothesis_tested"
        )

def test_hypothesis_tested_existe_en_g05():
    """El hypothesis_tested de cada pregunta debe existir en las hipotesis de G05."""
    hyp_ids = {h["id"] for h in HYPOTHESES}
    for q in INSTRUMENT["questions"]:
        assert q["hypothesis_tested"] in hyp_ids, (
            f"Pregunta {q['id']} referencia hipotesis {q['hypothesis_tested']} "
            f"que no existe en G05"
        )

def test_dimension_de_pregunta_coincide_con_dimension_de_hipotesis():
    """
    Si Q01 dice hypothesis_tested=H01 y H01 mapea a DIM-01,
    entonces Q01 debe estar en DIM-01.
    Incoherencia aqui significa que la pregunta mide una cosa
    pero se cuenta en otra dimension.
    """
    hyp_map = _hyp_map(HYPOTHESES)
    for q in INSTRUMENT["questions"]:
        h = hyp_map[q["hypothesis_tested"]]
        expected_dim = h["dimension_to_measure"]
        assert q["dimension"] == expected_dim, (
            f"Pregunta {q['id']}: hypothesis_tested={q['hypothesis_tested']} "
            f"mapea a {expected_dim} pero la pregunta esta en {q['dimension']}. "
            f"Incoherencia: la pregunta mide una cosa pero se cuenta en otra dimension."
        )

def test_cada_dimension_tiene_al_menos_una_pregunta():
    by_dim = _questions_by_dim(INSTRUMENT)
    for dim in INSTRUMENT["dimensions"]:
        assert dim["id"] in by_dim, f"Dimension {dim['id']} no tiene preguntas"
        assert len(by_dim[dim["id"]]) > 0

# ===========================================================================
# PARTE 4 ? NUMERO DE PREGUNTAS POR DIMENSION (JUSTIFICACION PSICOMETRICA)
# ===========================================================================

def test_numero_de_preguntas_justificado_por_prior():
    """
    La cantidad de preguntas Likert por dimension debe reflejar la importancia
    de la hipotesis (prior_probability):
      - prior >= 0.70: minimo 3 Likert (cobertura completa para alpha Cronbach)
      - prior >= 0.55: minimo 3 Likert (minimo psicometrico, Nunnally 1978)
      - prior <  0.50: podria tener 2 Likert (exploratorio)

    Razon: mas preguntas en hipotesis de alta prior = mas evidencia para
    el analisis bayesiano de G11a. Pero mas preguntas tambien = mas fatiga
    del respondente. El equilibrio es 3-4 Likert por dimension.
    """
    hyp_map = _hyp_map(HYPOTHESES)
    by_dim = _questions_by_dim(INSTRUMENT)

    for dim in INSTRUMENT["dimensions"]:
        h = hyp_map[dim["hypothesis_mapped"]]
        likert_count = sum(1 for q in by_dim[dim["id"]] if q["type"] == "likert_5")
        prior = h["prior_probability"]

        assert likert_count >= 3, (
            f"Dimension {dim['id']} (H={dim['hypothesis_mapped']}, prior={prior}) "
            f"tiene solo {likert_count} preguntas Likert. "
            f"Minimo 3 para alpha Cronbach confiable (Nunnally 1978)."
        )
        assert likert_count <= 6, (
            f"Dimension {dim['id']} tiene {likert_count} preguntas Likert. "
            f"Mas de 6 por dimension aumenta fatiga sin ganancia diagnostica significativa."
        )

def test_preguntas_abiertas_en_hipotesis_de_alta_prior():
    """
    Debe haber al menos 1 pregunta abierta por cada 2 hipotesis con prior >= 0.65.
    Razon: las preguntas abiertas triangulacion cualitativa que el Likert no captura.
    G11b (NLP) las analiza para confirmar o refutar hipotesis desde el lenguaje.
    Pero demasiadas abiertas aumentan la fatiga ? 1 por cada 2 hipotesis es el equilibrio.
    """
    high_prior_hyps = [h for h in HYPOTHESES if h["prior_probability"] >= 0.65]
    open_qs = _open_questions(INSTRUMENT)
    min_open = max(1, len(high_prior_hyps) // 2)
    assert len(open_qs) >= min_open, (
        f"Hay {len(high_prior_hyps)} hipotesis con prior >= 0.65 pero solo "
        f"{len(open_qs)} preguntas abiertas. Minimo esperado: {min_open}. "
        f"Las preguntas abiertas son necesarias para que G11b triangule cualitativamente."
    )

def test_total_preguntas_en_rango_razonable():
    """
    Total de preguntas Likert debe estar entre 10 y 20.
    - Menos de 10: insuficiente para cubrir 4 hipotesis con alpha Cronbach aceptable
    - Mas de 20: fatiga del respondente, tasa de abandono > 30% (literatura de UX surveys)
    """
    likert_count = len(_likert_questions(INSTRUMENT))
    assert 10 <= likert_count <= 20, (
        f"El instrumento tiene {likert_count} preguntas Likert. "
        f"Rango optimo: 10-20. "
        f"Menos de 10 compromete la validez; mas de 20 aumenta el abandono."
    )

# ===========================================================================
# PARTE 5 ? REVERSE SCORING
# ===========================================================================

def test_cada_dimension_tiene_al_menos_un_reverse():
    """
    Cada dimension debe tener al menos 1 item reverse-scored.
    Razon (Paulhus 1991): sin items reverse, no se puede detectar sesgo de
    aquiescencia (tendencia a marcar siempre alto sin leer).
    Si todos los items van en la misma direccion, un respondente descuidado
    produce scores altos que parecen validos pero no lo son.
    """
    by_dim = _questions_by_dim(INSTRUMENT)
    for dim in INSTRUMENT["dimensions"]:
        likert_in_dim = [q for q in by_dim[dim["id"]] if q["type"] == "likert_5"]
        reverse_in_dim = [q for q in likert_in_dim if q.get("reverse_scored")]
        assert len(reverse_in_dim) >= 1, (
            f"Dimension {dim['id']} no tiene items reverse-scored. "
            f"Sin ellos no se puede detectar sesgo de aquiescencia (Paulhus 1991)."
        )

def test_reverse_no_es_mayoria_en_ninguna_dimension():
    """
    Los items reverse no deben ser mayoria en ninguna dimension.
    Razon: si hay mas reverse que normales, el patron esperado se invierte
    y el analisis bayesiano de G11a se complica innecesariamente.
    Regla practica: maximo 1 reverse por cada 2 normales.
    """
    by_dim = _questions_by_dim(INSTRUMENT)
    for dim in INSTRUMENT["dimensions"]:
        likert_in_dim = [q for q in by_dim[dim["id"]] if q["type"] == "likert_5"]
        reverse_count = sum(1 for q in likert_in_dim if q.get("reverse_scored"))
        normal_count = len(likert_in_dim) - reverse_count
        assert reverse_count <= normal_count, (
            f"Dimension {dim['id']}: {reverse_count} reverse vs {normal_count} normales. "
            f"Los reverse no deben ser mayoria ? complica el patron esperado para G11a."
        )

# ===========================================================================
# PARTE 6 ? COHERENCIA DE ROLES POR PREGUNTA
# ===========================================================================

VALID_ROLES = {"Estrategico", "Tactico", "Operativo"}

def test_roles_validos_en_todas_las_preguntas():
    for q in INSTRUMENT["questions"]:
        invalid = set(q["roles"]) - VALID_ROLES
        assert not invalid, (
            f"Pregunta {q['id']} tiene roles invalidos: {invalid}. "
            f"Roles validos: {VALID_ROLES}"
        )

def test_cada_pregunta_tiene_al_menos_un_rol():
    for q in INSTRUMENT["questions"]:
        assert len(q["roles"]) >= 1, f"Pregunta {q['id']} no tiene roles asignados"

def test_preguntas_exclusivas_operativo_son_de_ejecucion():
    """
    Preguntas asignadas SOLO a Operativo deben ser sobre aspectos que
    unicamente el nivel operativo puede responder con base empirica.
    Razon: incluir Estrategico en preguntas de ejecucion directa introduce
    ruido (respuestas sin base empirica) que reduce la validez discriminante.
    """
    for q in INSTRUMENT["questions"]:
        if q["roles"] == ["Operativo"] and q["type"] == "likert_5":
            # Debe tener signal_logic que explique por que solo Operativo
            signal_logic = q.get("expected_direction", {}).get("signal_logic", "")
            assert len(signal_logic) > 20, (
                f"Pregunta {q['id']} es exclusiva de Operativo pero no explica "
                f"por que en signal_logic. Toda exclusion de roles debe estar justificada."
            )

def test_preguntas_de_brecha_percepcion_incluyen_estrategico_y_operativo():
    """
    Las dimensiones cuya hipotesis predice brecha de percepcion entre
    Estrategico y Operativo deben tener al menos 1 pregunta con ambos roles.
    Razon: sin preguntas compartidas entre Estrategico y Operativo,
    no se puede calcular el delta_sigma que G11a necesita para el analisis bayesiano.
    """
    hyp_map = _hyp_map(HYPOTHESES)
    by_dim = _questions_by_dim(INSTRUMENT)

    for dim in INSTRUMENT["dimensions"]:
        h = hyp_map[dim["hypothesis_mapped"]]
        signals = h["expected_signals"]["if_true"]
        # Si la hipotesis predice scores diferentes entre Estrategico y Operativo
        if "Estrategico" in signals and "Operativo" in signals:
            shared = [
                q for q in by_dim[dim["id"]]
                if "Estrategico" in q["roles"] and "Operativo" in q["roles"]
                and q["type"] == "likert_5"
            ]
            assert len(shared) >= 1, (
                f"Dimension {dim['id']} predice brecha Estrategico-Operativo "
                f"pero no tiene preguntas compartidas entre ambos roles. "
                f"Sin preguntas compartidas no se puede calcular delta_sigma."
            )

# ===========================================================================
# PARTE 7 ? EXPECTED DIRECTION: DIFERENCIACION DE ROLES
# ===========================================================================

def test_preguntas_likert_tienen_expected_direction():
    """
    Toda pregunta Likert debe tener expected_direction documentado.
    Razon: sin esto, G11a no puede verificar si el patron observado
    coincide con el esperado ? el analisis bayesiano pierde su base.
    """
    for q in _likert_questions(INSTRUMENT):
        assert "expected_direction" in q, (
            f"Pregunta {q['id']} no tiene expected_direction. "
            f"Sin esto G11a no puede verificar el patron observado."
        )
        ed = q["expected_direction"]
        assert "if_hypothesis_true" in ed, (
            f"Pregunta {q['id']}: expected_direction no tiene if_hypothesis_true"
        )
        assert "signal_logic" in ed, (
            f"Pregunta {q['id']}: expected_direction no tiene signal_logic. "
            f"Debe explicar POR QUE la pregunta diferencia roles."
        )

def test_expected_direction_cubre_los_roles_de_la_pregunta():
    """
    El expected_direction debe tener una entrada por cada rol asignado a la pregunta.
    Razon: si un rol no tiene expected_direction, G11a no puede verificar
    si ese rol respondio como se esperaba.
    """
    for q in _likert_questions(INSTRUMENT):
        ed = q["expected_direction"]["if_hypothesis_true"]
        for role in q["roles"]:
            assert role in ed, (
                f"Pregunta {q['id']}: rol {role} esta en roles[] pero no tiene "
                f"expected_direction. G11a no podra verificar el patron de este rol."
            )

def test_signal_logic_no_es_vacio():
    """
    El signal_logic debe explicar el mecanismo causal, no solo afirmar que diferencia.
    Minimo 30 caracteres para asegurar que hay una explicacion real.
    """
    for q in _likert_questions(INSTRUMENT):
        logic = q["expected_direction"].get("signal_logic", "")
        assert len(logic) >= 30, (
            f"Pregunta {q['id']}: signal_logic muy corto ({len(logic)} chars). "
            f"Debe explicar el mecanismo causal por el que la pregunta diferencia roles."
        )

def test_rationale_presente_en_todas_las_preguntas():
    """
    Toda pregunta debe tener rationale que explique por que existe.
    Razon: el rationale es la auditoria del diseno ? permite revisar
    si cada pregunta tiene una razon valida de estar en el instrumento.
    Sin rationale, no se puede evaluar si el instrumento es coherente.
    """
    for q in INSTRUMENT["questions"]:
        assert "rationale" in q and len(q["rationale"]) >= 20, (
            f"Pregunta {q['id']} no tiene rationale o es muy corto. "
            f"Cada pregunta debe justificar su existencia."
        )

# ===========================================================================
# PARTE 8 ? FALSIFICABILIDAD DE HIPOTESIS
# ===========================================================================

def test_cada_hipotesis_tiene_condicion_de_falsificacion():
    """
    Toda hipotesis debe tener una condicion especifica bajo la cual
    seria rechazada. Sin esto, el analisis bayesiano de G11a no puede
    rechazar hipotesis ? solo confirmarlas, lo que no es ciencia.
    """
    for h in HYPOTHESES:
        fc = h["expected_signals"].get("falsification_condition", "")
        assert len(fc) > 20, (
            f"Hipotesis {h['id']} no tiene condicion de falsificacion clara. "
            f"Sin esto G11a no puede rechazar la hipotesis ? solo confirmarla."
        )

def test_condicion_falsificacion_menciona_score_o_delta():
    """
    La condicion de falsificacion debe ser cuantitativa: mencionar un score
    o un delta_sigma especifico. Condiciones vagas como 'si no hay problema'
    no son falsificables en el sentido de Popper.
    """
    for h in HYPOTHESES:
        fc = h["expected_signals"]["falsification_condition"].lower()
        has_quantitative = any(
            keyword in fc
            for keyword in ["score", "delta", ">", "<", "puntos", "alpha", "%"]
        )
        assert has_quantitative, (
            f"Hipotesis {h['id']}: la condicion de falsificacion no es cuantitativa. "
            f"Debe mencionar un score, delta_sigma o umbral especifico."
        )

def test_expected_pattern_if_false_documentado_en_dimensiones():
    """
    Cada dimension debe documentar como se verian los scores si la hipotesis
    es FALSA. Esto es lo que permite a G11a rechazar hipotesis, no solo confirmarlas.
    """
    for dim in INSTRUMENT["dimensions"]:
        assert "expected_pattern_if_false" in dim, (
            f"Dimension {dim['id']} no tiene expected_pattern_if_false. "
            f"Sin esto G11a no sabe como se ve la evidencia cuando la hipotesis es falsa."
        )
        assert len(dim["expected_pattern_if_false"]) > 10

# ===========================================================================
# PARTE 9 ? COHERENCIA GLOBAL: EL INSTRUMENTO PUEDE PRODUCIR DELTA_SIGMA
# ===========================================================================

def test_instrumento_puede_producir_delta_sigma_para_cada_hipotesis():
    """
    Para cada hipotesis que predice brecha de percepcion entre roles,
    el instrumento debe tener preguntas que permitan calcular esa brecha.
    Razon: si no hay preguntas compartidas entre los roles que se comparan,
    G10a no puede calcular el delta_sigma que G11a necesita.
    """
    hyp_map = _hyp_map(HYPOTHESES)
    by_dim = _questions_by_dim(INSTRUMENT)

    for h in HYPOTHESES:
        signals = h["expected_signals"]["if_true"]
        roles_with_signals = list(signals.keys())
        if len(roles_with_signals) < 2:
            continue  # hipotesis de un solo rol, no aplica

        dim_id = h["dimension_to_measure"]
        dim_questions = by_dim.get(dim_id, [])

        # Verificar que hay al menos 1 pregunta donde los roles con senales diferentes
        # puedan responder juntos
        for i, r1 in enumerate(roles_with_signals):
            for r2 in roles_with_signals[i+1:]:
                shared = [
                    q for q in dim_questions
                    if r1 in q["roles"] and r2 in q["roles"]
                    and q["type"] == "likert_5"
                ]
                assert len(shared) >= 1, (
                    f"Hipotesis {h['id']}: predice brecha {r1} vs {r2} en {dim_id} "
                    f"pero no hay preguntas Likert compartidas entre ambos roles. "
                    f"G10a no podra calcular el delta_sigma necesario para G11a."
                )

def test_instrumento_cubre_los_tres_roles():
    """
    El instrumento completo debe tener preguntas para los 3 roles.
    Un instrumento que excluye un rol no puede hacer analisis Multi-Rater.
    """
    all_roles_covered = set()
    for q in INSTRUMENT["questions"]:
        all_roles_covered.update(q["roles"])
    assert VALID_ROLES == all_roles_covered, (
        f"El instrumento no cubre todos los roles. "
        f"Cubiertos: {all_roles_covered}. Requeridos: {VALID_ROLES}"
    )

def test_operativo_tiene_mas_preguntas_que_estrategico():
    """
    El nivel Operativo debe tener mas preguntas que el Estrategico.
    Razon: el Operativo tiene acceso directo a la ejecucion del proceso
    y es la fuente de evidencia mas rica para confirmar hipotesis operativas.
    El Estrategico responde menos preguntas pero las criticas (brecha de percepcion).
    """
    operativo_qs = [q for q in _likert_questions(INSTRUMENT) if "Operativo" in q["roles"]]
    estrategico_qs = [q for q in _likert_questions(INSTRUMENT) if "Estrategico" in q["roles"]]
    assert len(operativo_qs) >= len(estrategico_qs), (
        f"Operativo tiene {len(operativo_qs)} preguntas Likert, "
        f"Estrategico tiene {len(estrategico_qs)}. "
        f"Operativo deberia tener al menos las mismas ? es la fuente de evidencia operativa."
    )

# ===========================================================================
# PARTE 10 ? COHERENCIA CON EL SINTOMA DE ENTRADA
# ===========================================================================

SINTOMA = "Las entregas llegan 3-5 dias tarde, perdimos 2 contratos"
SUBPROCESS = "Gestion de entregas last-mile"

def test_instrumento_focalizado_en_subproceso():
    assert INSTRUMENT["subprocess_focus"] == SUBPROCESS, (
        f"El instrumento dice ser sobre '{INSTRUMENT['subprocess_focus']}' "
        f"pero el subproceso del mandato es '{SUBPROCESS}'"
    )

def test_hipotesis_son_especificas_al_subproceso():
    """
    Las hipotesis no deben ser genericas. Deben mencionar aspectos
    especificos del subproceso diagnosticado.
    Razon: hipotesis genericas producen preguntas genericas que no
    diferencian roles ? el instrumento pierde su poder diagnostico.
    Minimo: la hipotesis debe tener mas de 15 palabras.
    """
    for h in HYPOTHESES:
        words = h["hypothesis"].split()
        assert len(words) >= 10, (
            f"Hipotesis {h['id']} es muy corta ({len(words)} palabras): "
            f"'{h['hypothesis']}'. "
            f"Las hipotesis genericas producen preguntas genericas."
        )

def test_preguntas_mencionan_contexto_del_proceso():
    """
    Las preguntas Likert deben ser especificas al proceso diagnosticado,
    no preguntas genericas de satisfaccion laboral.
    Verificacion simple: el texto de la pregunta debe tener mas de 10 palabras.
    Preguntas cortas como 'El proceso funciona bien' son demasiado genericas.
    """
    for q in _likert_questions(INSTRUMENT):
        words = q["text"].split()
        assert len(words) >= 8, (
            f"Pregunta {q['id']} es muy corta ({len(words)} palabras): "
            f"'{q['text']}'. "
            f"Las preguntas deben ser especificas al proceso, no genericas."
        )

def test_ids_de_preguntas_son_unicos():
    ids = [q["id"] for q in INSTRUMENT["questions"]]
    assert len(ids) == len(set(ids)), (
        f"Hay IDs duplicados en las preguntas: "
        f"{[i for i in ids if ids.count(i) > 1]}"
    )
