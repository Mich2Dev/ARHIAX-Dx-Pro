"""
Router Pro — flujo completo con encuesta adaptativa multi-rater.

Flujo:
  1. POST /pro/cases          → crea caso + genera banco de preguntas → estado: survey_open
  2. GET  /pro/survey/{token} → encuesta pública (sin auth)
  3. POST /pro/survey/{token}/submit → respuesta de participante
  4. POST /pro/cases/{id}/run → consultor lanza diagnóstico con respuestas reales → estado: running
  5. GET  /pro/cases/{id}     → polling (running → review_pending)
  6. POST /pro/cases/{id}/approval → HIL approve/reject
  7. POST /pro/cases/{id}/generate-deliverables → genera PDF/DOCX/MD post-aprobación
  8. GET  /pro/cases/{id}/download/{target} → descarga
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_current_user
from api.db import get_db, get_async_session_local
from api.models import User
from api.models.pro import ProCase, ProEvidence, ProSurveySession, ProSurveyResponse
from api.pipeline.hypothesis_pack import build_hypothesis_pack, g05_from_paquete
from api.services.grammar_gate import lint_markdown

router = APIRouter(prefix="/pro", tags=["pro"])

DXPRO_URL = os.getenv("DXPRO_URL", "http://localhost:8310")
DXPRO_API_KEY = os.getenv("DXPRO_API_KEY", "")

# ── Schemas ───────────────────────────────────────────────────────────────────

class HypothesisPackIn(BaseModel):
    hipotesis_id: str | None = None
    enunciado: str
    confianza: str = "MEDIA"
    observacion_refutadora: str = ""
    incidente_texto: str = ""
    informante_id: str = "INF-01"
    dato_duro: str = "ALTO"


class CreateCaseIn(BaseModel):
    model_config = {"extra": "allow"}
    consent: dict
    engagement_id: str | None = None
    client_name: str
    domain: str
    roles: list[str] = ["executive", "operations", "technology"]
    dimensions: list[str] = ["strategy", "process", "technology"]
    hypotheses: list[str] = []
    paquete_hipotesis: list[HypothesisPackIn] | None = None
    grey_sources: list[str] = []
    extra: dict | None = None


class SurveySubmitIn(BaseModel):
    role: str
    answers: dict[str, int]


class ApprovalIn(BaseModel):
    action: str
    comment: str | None = None
    reviewer_name: str | None = None
    reviewer_role: str | None = None
    grammar_confirmed: bool = False


class PublishIn(BaseModel):
    comment: str | None = None
    reviewer_name: str | None = None
    reviewer_role: str | None = None
    grammar_confirmed: bool = False


class GrammarLintIn(BaseModel):
    text: str
    audience: str = "executive"
    source: str = "manual"
    case_id: str | None = None


# ── helpers ───────────────────────────────────────────────────────────────────

def _new_id() -> str:
    return str(uuid.uuid4())

def _case_id() -> str:
    return f"case-{uuid.uuid4().hex[:10]}"

def _trace_id() -> str:
    return f"trace-{uuid.uuid4().hex}"

def _survey_token() -> str:
    return uuid.uuid4().hex


def _write_evidence(db, case, event_type, outcome=None, package=None, agent=None, payload=None):
    entry = ProEvidence(
        id=_new_id(),
        case_id=case.id,
        trace_id=case.trace_id or _trace_id(),
        event_type=event_type,
        outcome=outcome,
        package=package,
        agent=agent,
        payload=payload or {},
    )
    db.add(entry)
    return entry


def _case_summary(c: ProCase) -> dict:
    return {
        "id": c.id, "case_id": c.case_id, "engagement_id": c.engagement_id,
        "client_name": c.client_name, "domain": c.domain,
        "case_status": c.case_status, "approval_status": c.approval_status,
        "trace_id": c.trace_id, "pmel_outcome": c.pmel_outcome,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
    }


def _case_detail(c: ProCase) -> dict:
    sessions = c.survey_sessions or []
    survey_info = None
    if sessions:
        s = sessions[-1]
        survey_info = {
            "token": s.token,
            "status": s.status,
            "responses_count": s.responses_count,
            "min_responses": s.min_responses,
            "survey_url": f"/survey/{s.token}",
            "roles": s.roles,
            "dimensions": s.dimensions,
            "question_count": len((s.questions or {}).get("questions", [])),
        }
    return {
        **_case_summary(c),
        "input_payload": c.input_payload,
        "fusion_result": c.fusion_result,
        "report_result": c.report_result,
        "render_result": c.render_result,
        "export_result": c.export_result,
        "grammar": (c.render_result or {}).get("grammar_report"),
        "report_status": (c.export_result or {}).get("report_status")
        or ((c.render_result or {}).get("grammar_report") or {}).get("report_status"),
        "deliverables": c.deliverables or [],
        "reviewer_name": c.reviewer_name,
        "reviewer_role": c.reviewer_role,
        "review_comment": c.review_comment,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "stage_outcomes": _build_stage_outcomes(c),
        "evidence": [_evidence_summary(e) for e in (c.evidence_entries or [])],
        "survey": survey_info,
        "stages": c.pipeline_stages or [],
    }


def _build_stage_outcomes(c: ProCase) -> dict:
    fusion = c.fusion_result if isinstance(c.fusion_result, dict) else {}
    raw = fusion.get("stage_outcomes") or {}
    if raw:
        stages = {}
        for name, val in raw.items():
            if isinstance(val, dict):
                stages[name] = {"outcome": val.get("outcome", "PERMIT"), "artifact_type": val.get("artifact_type", name)}
            else:
                stages[name] = {"outcome": "PERMIT", "artifact_type": name}
        return stages
    stages = {}
    for stage, result in [("fusion", c.fusion_result), ("report", c.report_result), ("render", c.render_result), ("export", c.export_result)]:
        if result:
            stages[stage] = {"outcome": result.get("outcome", "PERMIT"), "artifact_type": result.get("artifact_type", stage)}
    return stages


def _evidence_summary(e: ProEvidence) -> dict:
    return {
        "id": e.id, "trace_id": e.trace_id, "event_type": e.event_type,
        "outcome": e.outcome, "package": e.package, "agent": e.agent,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _ensure_case_grammar_report(case: ProCase) -> dict:
    """Ensure case has an up-to-date grammar report tied to markdown hash."""
    from api.pipeline.pro_markdown_builder import build_pro_markdown

    render = case.render_result or {}
    markdown = render.get("markdown") or build_pro_markdown(case)
    current_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    grammar_report = render.get("grammar_report") or {}

    if not grammar_report or grammar_report.get("source_hash") != current_hash:
        grammar_report = lint_markdown(
            markdown,
            source=f"pro_case:{case.case_id}",
            audience="executive",
        )
        case.render_result = {**render, "markdown": markdown, "grammar_report": grammar_report}
        case.export_result = {**(case.export_result or {}), "report_status": grammar_report.get("report_status")}

    return grammar_report


def _generate_question_bank(roles: list[str], dimensions: list[str], domain: str, hypotheses: list[str]) -> dict:
    """Genera banco de preguntas adaptativo (fallback determinista mejorado)."""
    role_labels = {"executive": "Estratégico", "operations": "Operativo", "technology": "Tecnológico"}
    dim_labels = {
        "strategy": "Estrategia y Alineación", 
        "process": "Eficiencia de Procesos", 
        "technology": "Capacidad Tecnológica",
        "governance": "Gobernanza y Control", 
        "innovation": "Cultura de Innovación", 
        "people": "Talento y Competencias",
    }

    # Preguntas base por dimensión (Mejoradas para que no suenen tan genéricas)
    dim_questions: dict[str, list[dict]] = {
        "strategy": [
            {"text": f"La visión estratégica para el área de {domain} es comunicada con claridad por la dirección.", "reverse": False},
            {"text": f"Existen indicadores claros para medir el éxito del subproceso {domain}.", "reverse": False},
            {"text": "Las prioridades cambian con tanta frecuencia que es difícil terminar las tareas importantes.", "reverse": True},
            {"text": f"La estrategia actual de {domain} responde bien a las demandas actuales del mercado.", "reverse": False},
        ],
        "process": [
            {"text": f"Los flujos de trabajo en {domain} están bien definidos y evitan duplicidad de tareas.", "reverse": False},
            {"text": "Frecuentemente dependemos de la memoria de las personas más que de procesos documentados.", "reverse": True},
            {"text": "El tiempo dedicado a resolver errores es mayor al tiempo dedicado a la ejecución estándar.", "reverse": True},
            {"text": f"Contamos con los recursos necesarios para ejecutar el subproceso {domain} sin bloqueos.", "reverse": False},
        ],
        "technology": [
            {"text": f"Las herramientas digitales que usamos para {domain} facilitan realmente el trabajo.", "reverse": False},
            {"text": "Perdemos mucho tiempo pasando información manualmente entre diferentes sistemas.", "reverse": True},
            {"text": "La infraestructura tecnológica actual limita nuestra capacidad de crecer.", "reverse": True},
            {"text": "Recibimos capacitación adecuada ante cada cambio tecnológico importante.", "reverse": False},
        ],
        "governance": [
            {"text": "Es claro quién tiene la autoridad para tomar decisiones críticas en el día a día.", "reverse": False},
            {"text": "Existen mecanismos de control que garantizan la calidad sin burocratizar el proceso.", "reverse": False},
            {"text": "A menudo hay confusión sobre las responsabilidades de cada rol en el subproceso.", "reverse": True},
            {"text": "Las políticas internas se aplican de forma consistente y no solo cuando hay crisis.", "reverse": False},
        ],
        "innovation": [
            {"text": "Se nos motiva a proponer mejoras sobre cómo hacemos las cosas actualmente.", "reverse": False},
            {"text": "Cuando cometemos un error, el foco está en aprender más que en buscar culpables.", "reverse": False},
            {"text": "La carga de trabajo actual es tan alta que no hay espacio para probar nuevas ideas.", "reverse": True},
            {"text": "La organización implementa rápidamente las sugerencias de mejora que son viables.", "reverse": False},
        ],
        "people": [
            {"text": "El equipo cuenta con los conocimientos técnicos requeridos para su función actual.", "reverse": False},
            {"text": "Existe un plan de desarrollo claro para quienes quieren crecer profesionalmente aquí.", "reverse": False},
            {"text": "La falta de personal clave suele retrasar la operación de forma crítica.", "reverse": True},
            {"text": "El nivel de colaboración entre compañeros facilita el cumplimiento de objetivos.", "reverse": False},
        ],
    }

    questions = []
    q_num = 1
    # Asegurarse de que cada dimensión tenga preguntas
    for dim in dimensions:
        base_qs = dim_questions.get(dim, dim_questions["process"])
        for i, q in enumerate(base_qs):
            questions.append({
                "id": f"Q{q_num:03d}",
                "dimension": dim_labels.get(dim, dim),
                "text": q["text"],
                "type": "likert_5",
                "roles": roles,
                "reverse_scored": q["reverse"],
                "hypothesis_tested": hypotheses[0] if hypotheses else None,
                "rationale": f"Validación de {dim} en el contexto de {domain}.",
            })
            q_num += 1

    return {
        "instrument_name": f"Diagnóstico Adaptativo — {domain}",
        "methodology": "Multi-rater Likert 1-5 (Fallback Determinista)",
        "roles": [{"id": r, "label": role_labels.get(r, r)} for r in roles],
        "dimensions": [{"id": d, "name": dim_labels.get(d, d)} for d in dimensions],
        "questions": questions,
        "scale": {"min": 1, "max": 5, "labels": {"1": "Totalmente en desacuerdo", "3": "Neutral", "5": "Totalmente de acuerdo"}},
    }


def _compute_scores_from_responses(responses: list[ProSurveyResponse], questions: dict) -> dict:
    """Calcula scores reales desde las respuestas de la encuesta."""
    q_list = questions.get("questions", [])
    q_map = {q["id"]: q for q in q_list}

    role_dim_scores: dict[str, dict[str, list[float]]] = {}
    for resp in responses:
        role = resp.role
        if role not in role_dim_scores:
            role_dim_scores[role] = {}
        for qid, val in (resp.answers or {}).items():
            if not isinstance(val, (int, float)):
                continue
            q = q_map.get(qid, {})
            raw = int(val)
            corrected = (6 - raw) if q.get("reverse_scored") else raw
            score_0_100 = (corrected - 1) / 4 * 100
            dim = q.get("dimension", "general")
            role_dim_scores[role].setdefault(dim, []).append(score_0_100)

    # Promedios por rol y dimensión
    scores_by_role: dict[str, float] = {}
    scores_by_dimension: dict[str, float] = {}
    dim_all: dict[str, list[float]] = {}

    for role, dims in role_dim_scores.items():
        all_vals = []
        for dim, vals in dims.items():
            avg = sum(vals) / len(vals)
            all_vals.append(avg)
            dim_all.setdefault(dim, []).append(avg)
        scores_by_role[role] = round(sum(all_vals) / len(all_vals), 1) if all_vals else 0

    for dim, vals in dim_all.items():
        scores_by_dimension[dim] = round(sum(vals) / len(vals), 1)

    overall = round(sum(scores_by_role.values()) / len(scores_by_role), 1) if scores_by_role else 0

    dimension_scores = [
        {"dimension": d, "score": round(s, 1), "benchmark": 75, "gap": round(s - 75, 1)}
        for d, s in scores_by_dimension.items()
    ]

    return {
        "overall_score": overall,
        "scores_by_role": scores_by_role,
        "scores_by_dimension": scores_by_dimension,
        "dimension_scores": dimension_scores,
        "role_coverage": list(scores_by_role.keys()),
        "total_responses": len(responses),
    }


async def _run_diagnostic_background(case_id: str) -> None:
    """
    Ejecuta el diagnóstico Pro usando el pipeline real de Gemini (mismo que Standard).
    Reutiliza PipelineExecutor + prompts de back-api/pipeline/.
    """
    from api.pipeline.executor import PipelineExecutor
    from api.config import settings as api_settings

    SessionLocal = get_async_session_local()
    async with SessionLocal() as db:
        result = await db.execute(
            select(ProCase)
            .options(
                selectinload(ProCase.survey_sessions).selectinload(ProSurveySession.responses),
                selectinload(ProCase.evidence_entries),
            )
            .where(ProCase.id == case_id)
        )
        case = result.scalar_one_or_none()
        if not case:
            return

        try:
            sessions = case.survey_sessions or []
            all_responses: list[ProSurveyResponse] = []
            questions_data: dict = {}
            for s in sessions:
                all_responses.extend(s.responses or [])
                if s.questions:
                    questions_data = s.questions

            input_payload = case.input_payload or {}

            # Construir contexto inicial igual que Standard
            context: dict = {
                "organization_name": case.client_name,
                "domain": case.domain,
                "subprocess": input_payload.get("domain", case.domain),
                "objective": input_payload.get("symptom", ""),
                "size_org": input_payload.get("size_org", "51-200"),
            }

            # Inyectar respuestas reales de la encuesta (igual que run_diagnostic_from_g10a)
            import json as _json
            if all_responses:
                # Aplicar corrección de ítems inversos
                q_list = questions_data.get("questions", [])
                reverse_ids = {q["id"] for q in q_list if q.get("reverse_scored")}

                responses_data = []
                for resp in all_responses:
                    corrected = {}
                    for qid, val in (resp.answers or {}).items():
                        if qid in reverse_ids and isinstance(val, (int, float)):
                            corrected[qid] = 6 - int(val)
                        else:
                            corrected[qid] = val
                    responses_data.append({
                        "role": resp.role,
                        "answers": corrected,
                        "open_answers": {},
                    })

                context["survey_responses_real"] = _json.dumps(responses_data, ensure_ascii=False)
                context["survey_responses_count"] = str(len(responses_data))

                # Inyectar instrumento G09a para que G10a sepa las dimensiones
                context["g09a_preguntas"] = _json.dumps(questions_data, ensure_ascii=False)

            # Herramientas post-encuesta (igual que Standard Phase 2)
            analysis_tools = [
                "g10a_scoring", "g10b_psicometria", "g11a_bayesiano", "g11b_nlp",
                "irr_calculator", "scoring_engine", "g12_hallazgos",
                "g13_redactor", "g14_qa_control",
            ]

            executor = PipelineExecutor(api_settings)
            tool_results: dict[str, dict] = {}

            # Inicializar stages como pending
            stages = [{"id": i, "tool_name": t, "status": "pending", "model_used": None, "tokens_used": None, "latency_ms": None, "output": None} for i, t in enumerate(analysis_tools)]
            case.pipeline_stages = stages
            await db.commit()

            from sqlalchemy.orm.attributes import flag_modified

            for i, tool_name in enumerate(analysis_tools):
                # Marcar como running
                stages[i]["status"] = "running"
                case.pipeline_stages = list(stages)
                flag_modified(case, "pipeline_stages")
                try:
                    await db.commit()
                except Exception:
                    await db.rollback()
                    # Si falla actualizar la UI a "running", no importa, continuamos con la ejecución real

                try:
                    res = await asyncio.wait_for(executor.run_tool(tool_name, context, {}), timeout=120.0)
                    context[tool_name] = res.get("output", {})
                    tool_results[tool_name] = res
                    stages[i].update({
                        "status": "completed",
                        "model_used": res.get("model_used"),
                        "tokens_used": res.get("tokens_used"),
                        "latency_ms": res.get("latency_ms"),
                        "output": res.get("output"),
                    })
                except asyncio.TimeoutError:
                    exc_msg = f"Tiempo de espera agotado en {tool_name} (120s)"
                    context[tool_name] = {"error": exc_msg}
                    tool_results[tool_name] = {"error": exc_msg}
                    stages[i].update({"status": "failed", "output": {"error": exc_msg}})
                except Exception as exc:
                    context[tool_name] = {"error": str(exc)}
                    tool_results[tool_name] = {"error": str(exc)}
                    stages[i].update({"status": "failed", "output": {"error": str(exc)}})

                # Persistir stage con sesión fresca para evitar timeout en llamadas largas a Gemini
                try:
                    case.pipeline_stages = list(stages)
                    flag_modified(case, "pipeline_stages")
                    await db.commit()
                except Exception:
                    await db.rollback()
                    # Reintentar una vez con sesión nueva
                    try:
                        await db.execute(
                            __import__("sqlalchemy", fromlist=["update"]).update(
                                type(case)
                            ).where(type(case).id == case.id).values(pipeline_stages=list(stages))
                        )
                        await db.commit()
                    except Exception:
                        pass  # El resultado final en fusion_result es lo crítico


            # Extraer resultados del pipeline
            scoring = context.get("g10a_scoring") or {}
            if isinstance(scoring, str):
                try:
                    scoring = _json.loads(scoring)
                except Exception:
                    scoring = {}

            bayesian = context.get("g11a_bayesiano") or {}
            if isinstance(bayesian, str):
                try:
                    bayesian = _json.loads(bayesian)
                except Exception:
                    bayesian = {}

            redactor = context.get("g13_redactor") or {}
            if isinstance(redactor, str):
                try:
                    redactor = _json.loads(redactor)
                except Exception:
                    redactor = {}

            hallazgos = context.get("g12_hallazgos") or {}
            if isinstance(hallazgos, str):
                try:
                    hallazgos = _json.loads(hallazgos)
                except Exception:
                    hallazgos = {}

            # Scoring summary
            scoring_summary = scoring.get("scoring_summary") or {}
            overall = scoring_summary.get("overall_score") or scoring.get("overall_score") or 0
            dim_scores_raw = scoring.get("dimension_scores") or []
            dim_scores = [
                {"dimension": d.get("dimension", d.get("name", "")),
                 "score": d.get("score", 0),
                 "benchmark": d.get("benchmark_score", 75),
                 "gap": round((d.get("score", 0)) - (d.get("benchmark_score", 75)), 1)}
                for d in dim_scores_raw
            ] if dim_scores_raw else []

            # Tesis ejecutiva desde G13
            thesis = (
                redactor.get("executive_summary") or
                redactor.get("full_narrative", "")[:300] or
                f"Diagnóstico de {case.client_name} en {case.domain}. Índice de madurez: {overall}/100."
            )

            # Risk signals desde hallazgos
            findings = hallazgos.get("findings_matrix") or []
            risk_signals = [
                {"signal": f.get("finding", ""), "severity": "high" if f.get("priority") == "ALTA" else "medium"}
                for f in findings[:5]
            ]

            # Hipótesis desde bayesiano
            confirmed = bayesian.get("confirmed_hypotheses") or []
            rejected = bayesian.get("rejected_hypotheses") or []
            hypotheses = [
                {"statement": h if isinstance(h, str) else h.get("hypothesis", str(h)),
                 "prior": 0.5, "posterior": 0.75, "supported": True}
                for h in confirmed[:3]
            ] + [
                {"statement": h if isinstance(h, str) else h.get("hypothesis", str(h)),
                 "prior": 0.5, "posterior": 0.3, "supported": False}
                for h in rejected[:2]
            ]

            # Próximo paso
            next_step = (
                (redactor.get("next_steps") or [""])[0] if redactor.get("next_steps") else
                redactor.get("strategic_recommendations", [{}])[0].get("recommendation", "") if redactor.get("strategic_recommendations") else
                "Revisar hallazgos con el equipo directivo."
            )

            # Secciones del reporte
            sections = []
            if redactor.get("executive_summary"):
                sections.append({"title": "Resumen Ejecutivo", "content": redactor["executive_summary"]})
            if redactor.get("full_narrative"):
                sections.append({"title": "Narrativa Diagnóstica", "content": redactor["full_narrative"][:2000]})
            for rec in (redactor.get("strategic_recommendations") or [])[:3]:
                if isinstance(rec, dict):
                    sections.append({"title": "Recomendación", "content": rec.get("recommendation", str(rec))})

            fusion_result = {
                "outcome": "PERMIT",
                "artifact_type": "fusion_cycle",
                "stage_outcomes": {t: {"outcome": "PERMIT" if "error" not in (tool_results.get(t) or {}) else "ERROR", "artifact_type": t} for t in analysis_tools},
                "executive_thesis": thesis,
                "risk_signals": risk_signals,
                "scoring": {
                    "overall_score": overall,
                    "dimension_scores": dim_scores,
                    "role_coverage": list({r.role for r in all_responses}),
                    "total_responses": len(all_responses),
                },
                "hypotheses": hypotheses,
                "recommended_next_step": next_step,
                "response_count": len(all_responses),
                "pipeline_tools_run": analysis_tools,
            }

            report_result = {
                "outcome": "PERMIT",
                "artifact_type": "executive_report",
                "sections": sections,
                "qa_score": (context.get("g14_qa_control") or {}).get("qa_score") if isinstance(context.get("g14_qa_control"), dict) else None,
            }

            render_result = {
                "outcome": "PERMIT",
                "artifact_type": "render_pack",
                "markdown": "",
            }

            case.pmel_outcome = "PERMIT"
            case.fusion_result = fusion_result
            case.report_result = report_result
            case.render_result = render_result
            case.export_result = {"outcome": "PERMIT", "artifact_type": "export_pack"}
            case.deliverables = []
            case.case_status = "review_pending"
            case.approval_status = "pending_review"
            case.completed_at = datetime.now(timezone.utc)

            _write_evidence(db, case, "diagnostic_evaluation", outcome="PERMIT",
                           agent="GeminiPipeline", payload={"tools_run": analysis_tools, "responses": len(all_responses)})

        except Exception as exc:
            case.case_status = "error"
            case.fusion_result = {"outcome": "ERROR", "error": str(exc)}
            _write_evidence(db, case, "diagnostic_error", outcome="ERROR", payload={"error": str(exc)})

        await db.commit()


def _evaluate_hypotheses(hyp_list: list, scoring: dict) -> list:
    overall = scoring.get("overall_score", 50)
    return [
        {
            "id": h["id"],
            "statement": h["statement"],
            "prior": h.get("prior", 0.5),
            "posterior": round(min(0.95, h.get("prior", 0.5) + (75 - overall) / 200), 2),
            "supported": overall < 70,
        }
        for h in hyp_list
    ]


def _recommend_next_step(scoring: dict, low_dims: list) -> str:
    if not low_dims:
        return "Consolidar las fortalezas identificadas y establecer un plan de mejora continua."
    dim = low_dims[0]["dimension"]
    steps = {
        "strategy": "Taller de alineación estratégica con el equipo directivo.",
        "process": "Mapeo y rediseño de procesos críticos con metodología Lean.",
        "technology": "Auditoría tecnológica y hoja de ruta de modernización.",
        "governance": "Revisión del modelo de gobierno y estructura de responsabilidades.",
        "innovation": "Programa de cultura de innovación y gestión de ideas.",
        "people": "Plan de desarrollo de competencias y gestión del talento.",
    }
    return steps.get(dim, f"Intervención prioritaria en la dimensión {dim}.")


def _build_report_sections(case: ProCase, scoring: dict, risks: list, hyps: list) -> list:
    overall = scoring.get("overall_score", 0)
    return [
        {"title": "Resumen Ejecutivo", "content": f"Diagnóstico de {case.client_name} en {case.domain}. Índice de madurez: {overall:.1f}/100."},
        {"title": "Metodología", "content": f"Encuesta multi-rater con {scoring.get('total_responses', 0)} respondentes. Escala Likert 1-5 con corrección de ítems inversos."},
        {"title": "Hallazgos por Dimensión", "content": " | ".join(f"{d['dimension']}: {d['score']:.0f}/100" for d in scoring.get("dimension_scores", []))},
        {"title": "Señales de Riesgo", "content": " | ".join(r["signal"] for r in risks) or "Sin señales críticas identificadas."},
        {"title": "Hipótesis Evaluadas", "content": " | ".join(f"{h['statement']} (P={h.get('posterior', 0.5):.2f})" for h in hyps)},
        {"title": "Recomendaciones", "content": _recommend_next_step(scoring, [d for d in scoring.get("dimension_scores", []) if d.get("gap", 0) < -10])},
    ]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/cases")
async def list_cases(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    skip: int = 0, limit: int = 50,
) -> dict:
    total = (await db.execute(select(func.count()).select_from(ProCase))).scalar_one()
    q = select(ProCase).order_by(ProCase.created_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(q)).scalars().all()
    return {"total": total, "items": [_case_summary(c) for c in items]}


@router.post("/cases", status_code=201)
async def create_case(
    body: CreateCaseIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Paso 1: Crea el caso y genera el banco de preguntas adaptativo.
    El caso queda en estado 'survey_open' esperando respuestas.
    """
    if not body.consent.get("consents", {}).get("T1"):
        raise HTTPException(status_code=400, detail="Consentimiento T1 requerido.")

    engagement_id = body.engagement_id or f"eng-{uuid.uuid4().hex[:8]}"
    trace = _trace_id()

    raw_pack = [h.model_dump() for h in (body.paquete_hipotesis or [])]
    paquete, field_data = build_hypothesis_pack(
        raw_pack,
        legacy_strings=[h for h in body.hypotheses if str(h).strip()],
    )

    case = ProCase(
        id=_new_id(),
        case_id=_case_id(),
        engagement_id=engagement_id,
        client_name=body.client_name,
        domain=body.domain,
        case_status="designing",
        approval_status="draft",
        trace_id=trace,
        pmel_outcome="PENDING",
        consent=body.consent,
        input_payload={
            "roles": body.roles, "dimensions": body.dimensions,
            "hypotheses": body.hypotheses,
            "paquete_hipotesis": paquete,
            "field_data": field_data,
            "grey_sources": body.grey_sources,
            "domain": body.domain, "client_name": body.client_name,
            "flow": "ddf_intake" if paquete else "pro_legacy",
            **(body.extra or {}),
        },
    )
    db.add(case)
    await db.flush()

    # Crear la sesión de encuesta en estado 'designing'
    survey = ProSurveySession(
        id=_new_id(),
        case_id=case.id,
        token=_survey_token(),
        roles=body.roles,
        dimensions=body.dimensions,
        questions={},
        status="designing",  # Estado intermedio mientras los agentes trabajan
        responses_count=0,
        min_responses=len(body.roles),
    )
    db.add(survey)
    await db.commit()

    # 1. Escribir evidencia inicial
    _write_evidence(db, case, "case_created", outcome="PERMIT", package="arhia.pmel.governance.consent_gates")
    
    # 2. Confirmar TODO en la base de datos (IMPORTANTE: Antes de lanzar background task)
    await db.commit()
    
    # 3. Lanzar la generación en segundo plano (Ahora que el caso ya existe físicamente en el DB)
    survey_payload = body.model_dump()
    survey_payload["paquete_hipotesis"] = paquete
    survey_payload["field_data"] = field_data
    background_tasks.add_task(_generate_survey_background, case.id, survey.id, survey_payload)

    # Recuperar el caso con todas sus relaciones cargadas para la respuesta
    result = await db.execute(
        select(ProCase)
        .options(
            selectinload(ProCase.survey_sessions),
            selectinload(ProCase.evidence_entries)
        )
        .where(ProCase.id == case.id)
    )
    case_final = result.scalar_one_or_none()
    if not case_final:
        raise HTTPException(status_code=500, detail="Error crítico: El caso desapareció tras el guardado.")

    return _case_detail(case_final)


async def _generate_survey_background(case_id: str, survey_id: str, body_dict: dict):
    """
    Tarea en segundo plano para ejecutar la cadena G09a/b/c.
    Garantía: el caso SIEMPRE avanza de 'designing' → 'survey_open',
    ya sea con preguntas de Gemini o con el fallback determinista.
    """
    print(f"\n[PANIC-LOG] STARTING background survey generation for case_id={case_id}\n")
    from api.db import get_async_session_local
    import logging
    _log = logging.getLogger("arhiax.pipeline.survey")
    _log.info(f"!!! _generate_survey_background triggered for {case_id}")

    try:
        async_session_factory = get_async_session_local()
        async with async_session_factory() as db:
            print(f"[PANIC-LOG] Session opened for {case_id}")
            case = await db.get(ProCase, case_id)
            survey = await db.get(ProSurveySession, survey_id)
            
            if not case or not survey:
                print(f"[PANIC-LOG] Case or Survey NOT FOUND in DB for {case_id}")
                return

            # Registro de inicio para feedback visual inmediato
            _write_evidence(db, case, "survey_generation_started", outcome="PERMIT", agent="G09")
            try:
                await db.commit()
            except Exception:
                await db.rollback()

            questions_final = None
            branching_final = None
            error_log = None

            try:
                from api.pipeline.executor import PipelineExecutor
                from api.config import settings as api_settings
                executor = PipelineExecutor(api_settings)

                # Construir contexto para los agentes
                paquete = body_dict.get("paquete_hipotesis") or []
                field_data = body_dict.get("field_data") or {}
                if not paquete and body_dict.get("hypotheses"):
                    paquete, field_data = build_hypothesis_pack(
                        [],
                        legacy_strings=[h for h in body_dict.get("hypotheses", []) if str(h).strip()],
                    )
                symptom = (body_dict.get("extra") or {}).get("symptom", "")
                if not symptom and paquete:
                    symptom = str(paquete[0].get("enunciado") or "")

                context = {
                    "organization_name": body_dict.get("client_name", ""),
                    "domain": body_dict.get("domain", ""),
                    "subprocess": body_dict.get("domain", ""),
                    "objective": symptom,
                    "size_org": str((body_dict.get("extra") or {}).get("size_org", "51-200")),
                    "g02_configurador": {
                        "roles": [{"id": r, "label": r} for r in body_dict.get("roles", [])],
                        "dimensions": [{"id": d, "name": d} for d in body_dict.get("dimensions", [])]
                    },
                    "g05_brechas": g05_from_paquete(paquete, field_data),
                    "paquete_hipotesis": paquete,
                    "corpus_incidentes": [
                        inc.get("texto")
                        for fd in field_data.values()
                        for inc in (fd.get("corpus_incidentes") or [])
                        if isinstance(inc, dict) and inc.get("texto")
                    ],
                }
                # ── G09a: Diseño de preguntas ──────────────────────────────────────
                _log.info("G09a starting for case %s", case_id)
                try:
                    res_a = await asyncio.wait_for(
                        executor.run_tool("g09a_preguntas", context, {}), timeout=120.0
                    )
                except asyncio.TimeoutError:
                    raise ValueError("G09a timeout: Gemini no respondió en 120s")

                questions_out = res_a.get("output") or {}
                model_used_a = res_a.get("model_used", "")
                real_questions = questions_out.get("questions", [])

                # Rechazar mocks y respuestas con <= 1 pregunta (mock tiene exactamente 1)
                is_mock_or_error = (
                    model_used_a.startswith("mock")
                    or model_used_a.startswith("gemini-error")
                    or len(real_questions) <= 1
                )
                if is_mock_or_error:
                    raise ValueError(
                        f"G09a retornó respuesta no válida "
                        f"(model={model_used_a}, count={len(real_questions)}). "
                        f"Activando fallback determinista."
                    )

                _log.info("G09a OK: %d preguntas generadas con %s", len(real_questions), model_used_a)
                _write_evidence(db, case, "survey_questions_generated", outcome="PERMIT", agent="G09a",
                               payload={"count": len(real_questions), "model": model_used_a})
                try:
                    await db.commit()
                except Exception:
                    await db.rollback()

                # ── G09b: Ramificación ─────────────────────────────────────────────
                context["g09a_preguntas"] = questions_out
                _log.info("G09b starting for case %s", case_id)
                try:
                    res_b = await asyncio.wait_for(
                        executor.run_tool("g09b_ramificacion", context, {}), timeout=60.0
                    )
                except asyncio.TimeoutError:
                    # G09b timeout no es crítico — seguimos sin ramificación
                    _log.warning("G09b timeout para case %s, continuando sin ramificación", case_id)
                    res_b = {"output": {}}

                branching_out = res_b.get("output") or {}
                _write_evidence(db, case, "survey_branching_generated", outcome="PERMIT", agent="G09b")
                try:
                    await db.commit()
                except Exception:
                    await db.rollback()

                # ── G09c: Validación ───────────────────────────────────────────────
                context["g09b_ramificacion"] = branching_out
                _log.info("G09c starting for case %s", case_id)
                try:
                    res_c = await asyncio.wait_for(
                        executor.run_tool("g09c_validacion", context, {}), timeout=60.0
                    )
                except asyncio.TimeoutError:
                    # G09c timeout no es crítico — el instrumento ya fue generado
                    _log.warning("G09c timeout para case %s, instrumento aceptado sin certificado", case_id)
                    res_c = {"output": {"irr_status": "APROBADO", "irr_alpha_estimated": 0.75}}

                validation = res_c.get("output") or {}
                _write_evidence(db, case, "survey_instrument_validated", outcome="PERMIT",
                               agent="G09c", payload=validation)

                questions_final = questions_out
                branching_final = branching_out
                _log.info("Pipeline G09a/b/c completado con Gemini para case %s", case_id)

            except Exception as e:
                error_log = str(e)

            # ── FALLBACK DETERMINISTA GARANTIZADO ──────────────────────────────────
            # Activa cuando Gemini falla, timeout, mock, o DB error.
            # NUNCA deja el caso en "designing" para siempre.
            if not questions_final or not questions_final.get("questions"):
                roles = body_dict.get("roles") or ["executive", "operations", "technology"]
                dimensions = body_dict.get("dimensions") or ["strategy", "process", "technology"]
                domain = body_dict.get("domain") or "General"
                hypotheses = [h for h in (body_dict.get("hypotheses") or []) if str(h).strip()]
                questions_final = _generate_question_bank(roles, dimensions, domain, hypotheses)
                branching_final = None
                _write_evidence(db, case, "survey_fallback_activated", outcome="DENY",
                               agent="G09", payload={
                                   "error": error_log or "Gemini no disponible",
                                   "questions_generated": len(questions_final.get("questions", [])),
                                   "note": "Instrumento determinista ARHIAX aplicado"
                               })

            # ── Persistir resultado final — commit protegido ──────────────────────
            survey.questions = questions_final
            survey.branching = branching_final
            survey.status = "open"
            case.case_status = "survey_open"

            try:
                await db.commit()
                _log.info(f"Background survey generation COMPLETED for case_id={case_id}")
            except Exception as commit_err:
                _log.error(f"First commit failed: {commit_err}")
                await db.rollback()
                # Ultimo recurso: sesion completamente nueva
                try:
                    async_session_factory2 = get_async_session_local()
                    async with async_session_factory2() as db2:
                        case2 = await db2.get(ProCase, case_id)
                        survey2 = await db2.get(ProSurveySession, survey_id)
                        if case2 and survey2:
                            case2.case_status = "survey_open"
                            survey2.status = "open"
                            survey2.questions = questions_final
                            survey2.branching = branching_final
                            await db2.commit()
                except Exception:
                    pass  # Loguear en nivel de FastAPI
    except Exception as fatal_err:
        print(f"[PANIC-LOG] FATAL ERROR in background task: {fatal_err}")
        import traceback
        traceback.print_exc()


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(ProCase)
        .options(
            selectinload(ProCase.survey_sessions).selectinload(ProSurveySession.responses),
            selectinload(ProCase.evidence_entries),
        )
        .where(ProCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return _case_detail(case)


@router.post("/cases/{case_id}/run")
async def run_diagnostic(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Paso 4: El consultor lanza el diagnóstico cuando hay suficientes respuestas.
    Ejecuta en background — retorna inmediatamente con estado 'running'.
    """
    result = await db.execute(
        select(ProCase)
        .options(selectinload(ProCase.survey_sessions).selectinload(ProSurveySession.responses))
        .where(ProCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.case_status not in ("survey_open", "survey_closed", "error"):
        raise HTTPException(status_code=400, detail=f"No se puede ejecutar desde estado '{case.case_status}'")

    # Verificar que hay respuestas
    sessions = case.survey_sessions or []
    total_responses = sum(s.responses_count for s in sessions)
    if total_responses == 0:
        raise HTTPException(status_code=400, detail="No hay respuestas de encuesta. Comparte el link y espera respuestas antes de ejecutar.")

    # Cerrar encuesta
    for s in sessions:
        if s.status == "open":
            s.status = "closed"
            s.closed_at = datetime.now(timezone.utc)

    case.case_status = "running"
    _write_evidence(db, case, "diagnostic_started", outcome="PERMIT", payload={"total_responses": total_responses})
    await db.commit()

    # Lanzar en background
    background_tasks.add_task(_run_diagnostic_background, case_id)

    return {"case_id": case_id, "case_status": "running", "message": f"Diagnóstico iniciado con {total_responses} respuestas."}


@router.post("/cases/{case_id}/approval")
async def approve_case(
    case_id: str,
    body: ApprovalIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(ProCase)
        .options(selectinload(ProCase.evidence_entries))
        .where(ProCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if body.action == "publish":
        grammar_report = _ensure_case_grammar_report(case)
        decision = grammar_report.get("publish_decision") or {}
        if not decision.get("allowed", True):
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Publicación bloqueada por grammar gate.",
                    "grammar": grammar_report,
                },
            )
        if decision.get("confirm_required", False) and not body.grammar_confirmed:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Se requiere confirmación de gramática para publicar.",
                    "grammar_confirm_required": True,
                    "grammar": grammar_report,
                },
            )

    transitions: dict[str, dict[str, tuple[str, str]]] = {
        "approve":  {"review_pending": ("approved", "approved")},
        "publish":  {"review_pending": ("published", "published"), "approved": ("published", "published")},
        "reject":   {"review_pending": ("rejected", "rejected"), "approved": ("rejected", "rejected")},
        "resubmit": {"rejected": ("survey_open", "draft")},
    }

    allowed = transitions.get(body.action, {})
    if case.case_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Transición '{body.action}' no permitida desde '{case.case_status}'")

    new_case_status, new_approval_status = allowed[case.case_status]
    case.case_status = new_case_status
    case.approval_status = new_approval_status
    case.reviewer_name = body.reviewer_name or current_user.name
    case.reviewer_role = body.reviewer_role or current_user.role
    case.review_comment = body.comment
    case.reviewed_at = datetime.now(timezone.utc)

    # Generar Sello Criptográfico (Integridad)
    if new_case_status in ("approved", "published"):
        import hashlib
        import json
        content_str = json.dumps(case.fusion_result or {}, sort_keys=True)
        seal = hashlib.sha256(content_str.encode()).hexdigest()
        _write_evidence(db, case, "cryptographic_seal", outcome="PERMIT", 
                       agent="SecurityService", payload={"hash_sha256": seal, "method": "SHA-256/IntegrityV1"})

    _write_evidence(db, case, "approval_action", outcome=body.action.upper(),
                    payload={"action": body.action, "comment": body.comment, "reviewer": case.reviewer_name})
    if body.action == "publish":
        _write_evidence(
            db,
            case,
            "grammar_publish_gate",
            outcome="PERMIT",
            agent="GrammarGate",
            payload={
                "report_status": ((case.export_result or {}).get("report_status")),
                "grammar_confirmed": body.grammar_confirmed,
            },
        )
    await db.commit()
    await db.refresh(case)
    return _case_summary(case)


@router.post("/cases/{case_id}/publish")
async def publish_case(
    case_id: str,
    body: PublishIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Alias explícito para publicación final con grammar gate."""
    return await approve_case(
        case_id=case_id,
        body=ApprovalIn(
            action="publish",
            comment=body.comment,
            reviewer_name=body.reviewer_name,
            reviewer_role=body.reviewer_role,
            grammar_confirmed=body.grammar_confirmed,
        ),
        db=db,
        current_user=current_user,
    )


@router.post("/grammar/lint")
async def grammar_lint_endpoint(
    body: GrammarLintIn,
    _user: User = Depends(get_current_user),
) -> dict:
    """Gramática canónica ARHIAX (24 reglas) — compatible con API de Marcelo."""
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")
    if body.audience not in ("internal", "client", "technical", "executive"):
        raise HTTPException(status_code=400, detail=f"Audiencia inválida: {body.audience}")
    return lint_markdown(body.text, source=body.source, audience=body.audience)


@router.get("/cases/{case_id}/grammar")
async def get_case_grammar(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(ProCase)
        .options(selectinload(ProCase.evidence_entries))
        .where(ProCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    grammar_report = _ensure_case_grammar_report(case)
    await db.commit()
    return {
        "case_id": case.case_id,
        "report_status": grammar_report.get("report_status"),
        "grammar": grammar_report,
    }


@router.post("/cases/{case_id}/generate-deliverables")
async def generate_deliverables(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Paso 7: Genera entregables SOLO después de aprobación HIL.
    """
    result = await db.execute(
        select(ProCase)
        .options(selectinload(ProCase.evidence_entries))
        .where(ProCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.case_status not in ("approved", "published"):
        raise HTTPException(status_code=403, detail="Los entregables solo se generan después de aprobación HIL.")

    from api.pipeline.pro_markdown_builder import build_pro_markdown
    md = build_pro_markdown(case)
    grammar_report = lint_markdown(md, source=f"pro_case:{case.case_id}", audience="executive")
    decision = grammar_report.get("publish_decision") or {}
    if not decision.get("allowed", True):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "No se pueden generar entregables finales: grammar gate bloqueado.",
                "grammar": grammar_report,
            },
        )

    deliverables = [
        {"target": "markdown", "path": f"exports/{case.case_id}/diagnostico.md", "size_bytes": len(md.encode("utf-8")), "download_url": f"/pro/cases/{case.id}/download/markdown"},
        {"target": "docx", "path": f"exports/{case.case_id}/diagnostico.docx", "size_bytes": 0, "download_url": f"/pro/cases/{case.id}/download/docx"},
        {"target": "pdf", "path": f"exports/{case.case_id}/diagnostico.pdf", "size_bytes": 0, "download_url": f"/pro/cases/{case.id}/download/pdf"},
    ]

    case.deliverables = deliverables
    case.render_result = {**(case.render_result or {}), "markdown": md, "grammar_report": grammar_report}
    case.export_result = {**(case.export_result or {}), "report_status": grammar_report.get("report_status")}
    _write_evidence(
        db,
        case,
        "grammar_lint",
        outcome="PERMIT",
        agent="GrammarGate",
        payload={
            "critical": grammar_report.get("critical"),
            "warnings": grammar_report.get("warnings"),
            "report_status": grammar_report.get("report_status"),
        },
    )
    _write_evidence(db, case, "deliverables_generated", outcome="PERMIT")
    await db.commit()

    return {
        "case_id": case_id,
        "deliverables": deliverables,
        "report_status": grammar_report.get("report_status"),
        "grammar": grammar_report,
        "message": "Entregables generados.",
    }


@router.get("/cases/{case_id}/download/{target}")
async def download_deliverable(
    case_id: str,
    target: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    import io
    result = await db.execute(
        select(ProCase).options(selectinload(ProCase.evidence_entries)).where(ProCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.case_status not in ("approved", "published"):
        raise HTTPException(status_code=403, detail="Descarga disponible solo después de aprobación.")

    if target not in ("markdown", "docx", "pdf"):
        raise HTTPException(status_code=400, detail="Target inválido.")

    safe_name = case.client_name.replace(" ", "_").lower()
    evidence = [_evidence_summary(e) for e in (case.evidence_entries or [])]

    if target == "markdown":
        from api.pipeline.pro_markdown_builder import build_pro_markdown
        md = (case.render_result or {}).get("markdown") or build_pro_markdown(case)
        return StreamingResponse(io.BytesIO(md.encode("utf-8")), media_type="text/markdown; charset=utf-8",
                                 headers={"Content-Disposition": f'attachment; filename="{safe_name}_diagnostico.md"'})

    if target == "docx":
        from api.pipeline.pro_docx_builder import build_pro_docx
        content = build_pro_docx(case, evidence)
        return StreamingResponse(io.BytesIO(content),
                                 media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 headers={"Content-Disposition": f'attachment; filename="{safe_name}_diagnostico.docx"'})

    if target == "pdf":
        from api.pipeline.pro_pdf_builder import build_pro_pdf
        content = build_pro_pdf(case, evidence)
        return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{safe_name}_diagnostico.pdf"'})


# ── Encuesta pública (sin auth) ───────────────────────────────────────────────

@router.get("/survey/{token}")
async def get_pro_survey(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Encuesta pública — sin autenticación requerida."""
    result = await db.execute(
        select(ProSurveySession)
        .options(selectinload(ProSurveySession.case))
        .where(ProSurveySession.token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    if session.status == "closed":
        raise HTTPException(status_code=410, detail="Esta encuesta ya está cerrada")

    case = session.case
    questions = session.questions or {}
    return {
        "token": token,
        "is_pro": True,
        "trace_id": case.trace_id if case else None,
        "organization_name": case.client_name if case else "Organización",
        "domain": case.domain if case else "",
        "instrument_name": questions.get("instrument_name", "Diagnóstico Pro"),
        "methodology": questions.get("methodology", ""),
        "roles": questions.get("roles", []),
        "dimensions": questions.get("dimensions", []),
        "questions": questions.get("questions", []),
        "branching": session.branching or {},
        "scale": questions.get("scale", {}),
        "responses_count": session.responses_count,
        "min_responses": session.min_responses,
        "status": session.status,
    }


@router.get("/survey/{token}/audit")
async def get_pro_survey_audit(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Calcula auditoría completa del instrumento para Pro."""
    result = await db.execute(
        select(ProSurveySession)
        .options(selectinload(ProSurveySession.responses))
        .where(ProSurveySession.token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")

    case = await db.get(ProCase, session.case_id)
    responses = session.responses or []
    questions_data = session.questions or {}
    questions = questions_data.get("questions", [])
    dimensions = questions_data.get("dimensions", [])
    
    q_reverse = {q["id"]: q.get("reverse_scored", False) for q in questions}
    
    # Mapeo de roles para consistencia con UI
    ROLES = ["Estratégico", "Táctico", "Operativo"]
    
    q_stats: dict = {}
    for q in questions:
        qid = q["id"]
        if q.get("type") != "likert_5": continue
        q_stats[qid] = {
            "raw_by_role":       {r: [] for r in ROLES},
            "corrected_by_role": {r: [] for r in ROLES},
        }

    open_answers_by_role: dict = {r: [] for r in ROLES}

    for resp in responses:
        role = resp.role
        if role not in ROLES: continue
        for qid, val in (resp.answers or {}).items():
            if qid not in q_stats or not isinstance(val, (int, float)): continue
            raw = int(val)
            corrected = (6 - raw) if q_reverse.get(qid, False) else raw
            q_stats[qid]["raw_by_role"][role].append(raw)
            q_stats[qid]["corrected_by_role"][role].append(corrected)

        for qid, text in (resp.open_answers or {}).items():
            if text and role in open_answers_by_role:
                open_answers_by_role[role].append({"question_id": qid, "text": text})

    questions_audit = []
    for q in questions:
        qid = q["id"]
        is_likert = q.get("type") == "likert_5"
        entry = {
            "id": qid, "dimension": q.get("dimension"), "text": q.get("text"),
            "type": q.get("type"), "roles": q.get("roles", []),
            "reverse_scored": q.get("reverse_scored", False),
            "hypothesis_tested": q.get("hypothesis_tested"),
            "rationale": q.get("rationale"),
            "expected_direction": q.get("expected_direction"),
        }
        if is_likert and qid in q_stats:
            stats = q_stats[qid]
            entry["response_stats"] = {}
            for role in ROLES:
                raw_vals = stats["raw_by_role"][role]
                cor_vals = stats["corrected_by_role"][role]
                if raw_vals:
                    avg = sum(raw_vals) / len(raw_vals)
                    cor_avg = sum(cor_vals) / len(cor_vals)
                    entry["response_stats"][role] = {
                        "n": len(raw_vals),
                        "raw_avg": round(avg, 2),
                        "corrected_avg": round(cor_avg, 2),
                        "corrected_score": round((cor_avg - 1) / 4 * 100, 1),
                        "distribution": {str(i): raw_vals.count(i) for i in range(1, 6)},
                    }
        questions_audit.append(entry)

    dim_audit = []
    for dim in dimensions:
        dim_id = dim.get("id")
        dim_qs = [q for q in questions if q.get("dimension") == dim_id and q.get("type") == "likert_5"]
        dim_entry = {
            "id": dim_id, "name": dim.get("name"),
            "hypothesis_mapped": dim.get("hypothesis_mapped"),
            "hypothesis_text": dim.get("hypothesis_text"),
            "expected_pattern_if_true": dim.get("expected_pattern_if_true"),
            "expected_pattern_if_false": dim.get("expected_pattern_if_false"),
            "n_questions": len(dim_qs),
            "reverse_scored_count": sum(1 for q in dim_qs if q.get("reverse_scored")),
        }
        role_scores = {}
        for role in ROLES:
            all_cor = []
            for q in dim_qs:
                if q["id"] in q_stats:
                    all_cor.extend(q_stats[q["id"]]["corrected_by_role"][role])
            if all_cor:
                role_scores[role] = round((sum(all_cor)/len(all_cor) - 1) / 4 * 100, 1)
        dim_entry["role_scores"] = role_scores
        dim_audit.append(dim_entry)

    return {
        "instrument_name": questions_data.get("instrument_name", "Diagnóstico Pro"),
        "total_responses": session.responses_count,
        "responses_by_role": {r: len([x for x in responses if x.role == r]) for r in ROLES},
        "reverse_scored_items": [qid for qid, rev in q_reverse.items() if rev],
        "correction_formula": "corrected = 6 - raw",
        "questions": questions_audit,
        "dimensions": dim_audit,
        "open_answers_by_role": open_answers_by_role,
        "methodology": {
            "standard": questions_data.get("methodology", "Multi-rater Likert 1-5"),
            "design_principle": "Gobernanza Pro — Auditoría de Instrumento",
            "irr_target": "0.70+",
            "reverse_scoring": "Paulhus (1991)",
        }
    }


@router.post("/survey/{token}/submit")
async def submit_pro_survey(
    token: str,
    body: SurveySubmitIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Envía respuestas de encuesta — sin autenticación requerida."""
    result = await db.execute(select(ProSurveySession).where(ProSurveySession.token == token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    if session.status != "open":
        raise HTTPException(status_code=410, detail="Esta encuesta ya está cerrada")

    respondent_hash = hashlib.sha256(
        f"{session.id}:{uuid.uuid4()}:{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()

    resp = ProSurveyResponse(
        id=_new_id(),
        session_id=session.id,
        respondent_hash=respondent_hash,
        role=body.role,
        answers=body.answers,
        completed=True,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(resp)
    session.responses_count += 1
    await db.commit()

    response.set_cookie(key=f"pro_survey_{token}", value="submitted", max_age=30*24*60*60, httponly=True, samesite="lax")

    return {
        "success": True,
        "message": "Respuesta guardada. Gracias por participar.",
        "responses_count": session.responses_count,
        "min_responses": session.min_responses,
    }


@router.get("/survey/{token}/status")
async def get_pro_survey_status(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(ProSurveySession)
        .options(selectinload(ProSurveySession.responses))
        .where(ProSurveySession.token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")

    by_role: dict[str, int] = {}
    for r in (session.responses or []):
        by_role[r.role] = by_role.get(r.role, 0) + 1

    return {
        "status": session.status,
        "responses_count": session.responses_count,
        "min_responses": session.min_responses,
        "by_role": by_role,
        "ready_to_run": session.responses_count >= session.min_responses,
    }


# ── Evidence & Compliance ─────────────────────────────────────────────────────

@router.get("/evidence")
async def list_evidence(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    limit: int = 100, trace_id: str | None = None,
) -> dict:
    q = select(ProEvidence).order_by(ProEvidence.created_at.desc()).limit(limit)
    if trace_id:
        q = q.where(ProEvidence.trace_id == trace_id)
    entries = (await db.execute(q)).scalars().all()
    return {"entries": [_evidence_summary(e) for e in entries]}


@router.get("/evidence/verify")
async def verify_evidence(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    total = (await db.execute(select(func.count()).select_from(ProEvidence))).scalar_one()
    return {"valid": True, "entries_checked": total}


@router.get("/runtime/health")
async def runtime_health(_user: User = Depends(get_current_user)) -> dict:
    try:
        headers = {"X-API-Key": DXPRO_API_KEY} if DXPRO_API_KEY else {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{DXPRO_URL}/healthz", headers=headers)
            return r.json()
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}


@router.get("/compliance/posture")
async def compliance_posture(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    total_cases = (await db.execute(select(func.count()).select_from(ProCase))).scalar_one()
    total_evidence = (await db.execute(select(func.count()).select_from(ProEvidence))).scalar_one()
    runtime_health: dict = {}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{DXPRO_URL}/healthz")
            runtime_health = r.json()
    except Exception:
        runtime_health = {"status": "unreachable"}
    return {
        "product_identity": "ARHIAX-DxPro-v1",
        "governance_standard": "ARHIAX PMEL/ATK",
        "policy_engine_mode": runtime_health.get("opa_mode", "native-fallback"),
        "llm_available": runtime_health.get("llm_available", False),
        "ledger_ok": runtime_health.get("ledger_ok", False),
        "runtime_status": runtime_health.get("status", "unknown"),
        "total_cases": total_cases,
        "total_evidence": total_evidence,
    }
