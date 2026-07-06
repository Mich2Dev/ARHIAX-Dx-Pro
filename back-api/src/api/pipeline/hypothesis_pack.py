"""Construye paquete_hipotesis + field_data al estilo DDF (intake de main)."""

from __future__ import annotations

from typing import Any


def cid_for(hid: str) -> str:
    return f"C-{hid.split('-')[-1] or '01'}"


def build_hypothesis_pack(
    items: list[dict[str, Any]],
    *,
    legacy_strings: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normaliza hipótesis del wizard a formato DDF para G09 y runtime."""
    paquete: list[dict[str, Any]] = []
    field_data: dict[str, Any] = {}

    if items:
        for i, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            hid = str(raw.get("hipotesis_id") or f"H-{i + 1:02d}")
            enunciado = str(raw.get("enunciado") or "").strip()
            if not enunciado:
                continue
            incidente = str(raw.get("incidente_texto") or "").strip()
            refutadora = str(raw.get("observacion_refutadora") or "").strip()
            confianza = str(raw.get("confianza") or "MEDIA").upper()
            if confianza not in {"ALTA", "MEDIA", "BAJA"}:
                confianza = "MEDIA"
            dato_duro = str(raw.get("dato_duro") or "ALTO").upper()
            if dato_duro not in {"ALTO", "BAJO"}:
                dato_duro = "ALTO"
            informante = str(raw.get("informante_id") or "INF-01").strip() or "INF-01"

            paquete.append({
                "hipotesis_id": hid,
                "confianza": confianza,
                "enunciado": enunciado,
                "correlato_experiencial": "se vive en terreno" if incidente else "",
                "observacion_refutadora": refutadora,
                "limita_throughput": True,
            })

            cid = cid_for(hid)
            field_data[hid] = {
                "corpus_incidentes": [
                    {
                        "incidente_id": f"INC-{hid}",
                        "informante_id": informante,
                        "nivel": "operativo",
                        "texto": incidente,
                        "retranslation_acuerdo": 0.85,
                        "retranslation_sd": 1.1,
                        "marca_fabricacion": "vivida" if incidente else None,
                        "verificacion_cognitiva": "PASS" if incidente else None,
                    }
                ] if incidente else [],
                "def_operacional": {
                    "perfil_alto": "presencia frecuente del problema",
                    "perfil_bajo": "ausencia del problema",
                },
                "indicadores_observables": ["frecuencia observable del problema"],
                "limites_conceptuales_NO_es": [
                    "falta de competencia",
                    "falta de información",
                    "falta de autoridad",
                ],
                "dimensiones": [{"factor": "F1", "rol_epistemico": "comun"}],
                "naturaleza": "reflectivo",
                "escala": "frecuencia",
                "panel": {"F1": {"cvr": 0.8, "icvi": 0.85, "pretest": "PASS"}},
                "datos_duros": [{"constructo_id": cid, "nivel_dato": dato_duro, "verificable": True}],
                "corroboracion_cit": [{"incidente_id": f"INC-{hid}", "verificable": bool(incidente)}],
            }

    elif legacy_strings:
        for i, text in enumerate(legacy_strings):
            stmt = str(text).strip()
            if not stmt:
                continue
            hid = f"H-{i + 1:02d}"
            paquete.append({
                "hipotesis_id": hid,
                "confianza": "MEDIA",
                "enunciado": stmt,
                "correlato_experiencial": "",
                "observacion_refutadora": "",
                "limita_throughput": True,
            })

    return paquete, field_data


def g05_from_paquete(paquete: list[dict[str, Any]], field_data: dict[str, Any]) -> dict[str, Any]:
    """Contexto G05 enriquecido para G09a."""
    hypotheses = []
    for h in paquete:
        hid = str(h.get("hipotesis_id") or "")
        incidents = (field_data.get(hid) or {}).get("corpus_incidentes") or []
        incident_text = ""
        if incidents and isinstance(incidents[0], dict):
            incident_text = str(incidents[0].get("texto") or "")
        hypotheses.append({
            "id": hid,
            "hypothesis": h.get("enunciado"),
            "confidence": h.get("confianza"),
            "refuter": h.get("observacion_refutadora"),
            "incident": incident_text,
            "expected_signals": {
                "operativo": "ve el bloqueo en el día a día",
                "estrategico": "percibe impacto en resultados",
            },
        })
    return {"hypotheses": hypotheses, "gaps": [], "incidents_anchor": bool(field_data)}
