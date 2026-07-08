"""
Core pipeline execution logic — used by both the worker and the API.
Separated from tasks.py to avoid Celery/Redis dependency.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

log = logging.getLogger("arhiax.pipeline")


async def run_diagnostic(diagnostic_id: str, request_id: str, payload: dict) -> dict:
    """Execute the full governed diagnostic pipeline for one diagnostic."""
    import uuid
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from api.config import settings
    from api.db import get_async_session_local
    from api.models import Diagnostic, HumanReview, PipelineStage, SurveySession
    from api.pipeline.executor import PipelineExecutor
    from api.pipeline.governance_client import GovernanceClient

    SessionLocal = get_async_session_local()

    # ── 1. Governance evaluation ─────────────────────────────────────────────
    client = GovernanceClient(settings.governance_api_url)
    try:
        gov_response = await client.evaluate(request_id, payload)
    except Exception as exc:
        async with SessionLocal() as db:
            d = await db.get(Diagnostic, diagnostic_id)
            if d:
                d.status = "failed"
                d.decision = "DENY"
                await db.commit()
        log.error("Governance evaluation failed: %s", exc)
        return {"error": str(exc)}

    decision = gov_response.get("decision", {}).get("status", "DENY")
    log.info("Governance decision for %s: %s", diagnostic_id, decision)

    async with SessionLocal() as db:
        result = await db.execute(
            select(Diagnostic).options(selectinload(Diagnostic.stages))
            .where(Diagnostic.id == diagnostic_id)
        )
        diagnostic = result.scalar_one_or_none()
        if not diagnostic:
            return {"error": "diagnostic not found"}

        diagnostic.decision = decision
        diagnostic.rule_results = gov_response.get("rule_results", [])
        diagnostic.certificate  = gov_response.get("certificate")
        diagnostic.execution_plan = gov_response.get("execution_plan")
        diagnostic.human_review_required = gov_response.get("human_review_required", False)

        if decision == "DENY":
            diagnostic.status = "denied"
            diagnostic.completed_at = datetime.now(timezone.utc)
            await db.commit()
            # Notify
            from api.notifications import notify_denied
            reasons = gov_response.get("decision", {}).get("reasons", [])
            await notify_denied(diagnostic_id, diagnostic.organization_name, reasons)
            return {"status": "denied"}

        if decision == "ESCALATE_TO_HUMAN":
            diagnostic.status = "awaiting_review"
            review_type = _infer_review_type(gov_response)
            db.add(HumanReview(
                diagnostic_id=diagnostic.id,
                review_type=review_type,
            ))
            await db.commit()
            from api.notifications import notify_review_needed
            await notify_review_needed(diagnostic_id, diagnostic.organization_name, review_type)
            return {"status": "awaiting_review"}

        diagnostic.status = "running"
        await db.commit()

    # ── 2. Execute tools sequentially ────────────────────────────────────────
    executor  = PipelineExecutor(settings)
    planned   = gov_response.get("execution_plan", {}).get("planned_tools", [])
    models    = gov_response.get("execution_plan", {}).get("active_models", [])

    # Update stage phases from execution plan
    async with SessionLocal() as db:
        result = await db.execute(
            select(Diagnostic).options(selectinload(Diagnostic.stages))
            .where(Diagnostic.id == diagnostic_id)
        )
        diagnostic = result.scalar_one_or_none()
        stage_map = {s.tool_name: s for s in (diagnostic.stages or [])}
        for pt in planned:
            if pt["name"] in stage_map:
                stage_map[pt["name"]].phase = pt.get("phase", "unknown")
        await db.commit()

    context: dict = {
        "organization_name": payload.get("organization_name", ""),
        "domain":            payload.get("domain", ""),
        "subprocess":        payload.get("subprocess", ""),
        "objective":         payload.get("objective", ""),
        "size_org":          payload.get("size_org", ""),
    }

    # ── Enrich context with uploaded documents ────────────────────────────────
    from api.models import DiagnosticDocument
    async with SessionLocal() as db:
        docs_result = await db.execute(
            select(DiagnosticDocument)
            .where(DiagnosticDocument.diagnostic_id == diagnostic_id)
            .where(DiagnosticDocument.extracted_text.isnot(None))
        )
        docs = docs_result.scalars().all()
        if docs:
            doc_context = "\n\n".join(
                f"[{d.doc_type.upper()} — {d.original_name}]\n{d.extracted_text[:2000]}"
                for d in docs
            )
            context["client_documents"] = doc_context
            log.info("Enriched context with %d documents for diagnostic %s", len(docs), diagnostic_id)

    for pt in planned:
        if not pt.get("allowed", True):
            log.info("Skipping %s — not allowed at autonomy %s",
                     pt["name"], payload.get("requested_autonomy_level"))
            continue

        tool_name = pt["name"]

        async with SessionLocal() as db:
            result = await db.execute(
                select(PipelineStage)
                .where(PipelineStage.diagnostic_id == diagnostic_id)
                .where(PipelineStage.tool_name == tool_name)
            )
            stage = result.scalar_one_or_none()
            if not stage:
                continue
            stage.status     = "running"
            stage.started_at = datetime.now(timezone.utc)
            await db.commit()
            stage_id = stage.id

        route = _find_route(tool_name, models)
        t0    = time.monotonic()
        log.info("Running tool %s with model %s", tool_name, route.get("primary", "gemini"))

        try:
            res = await executor.run_tool(tool_name, context, route)
            context[tool_name] = res.get("output", "")
            status     = "completed"
            model_used = res.get("model_used")
            tokens     = res.get("tokens_used")
            output     = res
            log.info("Tool %s completed — %s tokens", tool_name, tokens)
        except Exception as exc:
            status     = "failed"
            model_used = None
            tokens     = None
            output     = {"error": str(exc)}
            log.error("Tool %s failed: %s", tool_name, exc)

        latency = int((time.monotonic() - t0) * 1000)

        async with SessionLocal() as db:
            result = await db.execute(
                select(PipelineStage).where(PipelineStage.id == stage_id)
            )
            stage = result.scalar_one_or_none()
            if stage:
                stage.status       = status
                stage.model_used   = model_used
                stage.tokens_used  = tokens
                stage.output       = output
                stage.latency_ms   = latency
                stage.completed_at = datetime.now(timezone.utc)
            if status == "failed":
                diag = await db.get(Diagnostic, diagnostic_id)
                if diag:
                    diag.status = "failed"
                    diag.decision = "DENY"
                    diag.completed_at = datetime.now(timezone.utc)
                    diag.rule_results = [{
                        "rule_id": "PIPELINE-LLM-FAIL-CLOSED",
                        "outcome": "FAIL",
                        "severity": "CRITICAL",
                        "message": f"Etapa {tool_name} falló: {output.get('error', 'error')}",
                    }]
            await db.commit()

        if status == "failed":
            return {
                "status": "failed",
                "tool": tool_name,
                "error": output.get("error") if isinstance(output, dict) else str(output),
            }

        # ── Check G01 mandate validation ─────────────────────────────────────
        if tool_name == "g01_receptor" and status == "completed":
            g01_output = res.get("output", {}) if status == "completed" else {}
            if isinstance(g01_output, dict) and g01_output.get("mandate_confirmed") is False:
                rejection = g01_output.get("rejection_reason", "Mandato incoherente o inválido")
                log.warning("G01 rejected mandate for %s: %s", diagnostic_id, rejection)
                async with SessionLocal() as db:
                    diag = await db.get(Diagnostic, diagnostic_id)
                    if diag:
                        diag.status = "denied"
                        diag.decision = "DENY"
                        diag.completed_at = datetime.now(timezone.utc)
                        # Store rejection reason in rule_results
                        diag.rule_results = [{
                            "rule_id": "G01-MANDATE-COHERENCE",
                            "outcome": "FAIL",
                            "severity": "HIGH",
                            "message": f"Mandato rechazado por G01: {rejection}"
                        }]
                    await db.commit()
                return {"status": "denied", "reason": rejection}

        # ── Pre-G09a coherence check ──────────────────────────────────────────
        # Before the survey is created (after G09c), verify G05 produced real
        # hypotheses. If G05 output is weak/mock, log a warning so it's visible.
        if tool_name == "g09c_validacion" and status == "completed":
            g05_output = context.get("g05_brechas", {})
            hypotheses = g05_output.get("hypotheses", []) if isinstance(g05_output, dict) else []
            gaps       = g05_output.get("gaps", [])       if isinstance(g05_output, dict) else []

            has_real_hypotheses = (
                len(hypotheses) >= 2
                and any(isinstance(h, dict) and len(h.get("hypothesis", "")) > 20 for h in hypotheses)
            )
            has_real_gaps = (
                len(gaps) >= 2
                and any(isinstance(g, dict) and len(g.get("description", "")) > 10 for g in gaps)
            )

            if not has_real_hypotheses or not has_real_gaps:
                log.warning(
                    "Weak G05 context for %s — hypotheses=%d, gaps=%d. "
                    "Survey questions may lack specificity.",
                    diagnostic_id, len(hypotheses), len(gaps)
                )

            # Also verify G09a produced real questions (not just 1 mock question)
            g09a_output = context.get("g09a_preguntas", {})
            questions = g09a_output.get("questions", []) if isinstance(g09a_output, dict) else []
            if len(questions) < 5:
                log.warning(
                    "G09a produced only %d questions for %s — survey may be too short.",
                    len(questions), diagnostic_id
                )

        # ── Survey Session Creation ───────────────────────────────────────────
        # After G09c validation, create survey session and pause pipeline
        if tool_name == "g09c_validacion" and status == "completed":
            g09a_output = context.get("g09a_preguntas", {})
            g09b_output = context.get("g09b_ramificacion", {})

            if isinstance(g09a_output, dict) and g09a_output:
                async with SessionLocal() as db:
                    existing = await db.execute(
                        select(SurveySession).where(SurveySession.diagnostic_id == diagnostic_id)
                    )
                    if not existing.scalar_one_or_none():
                        survey_token = str(uuid.uuid4())
                        db.add(SurveySession(
                            diagnostic_id=diagnostic_id,
                            token=survey_token,
                            questions=g09a_output,
                            branching=g09b_output if isinstance(g09b_output, dict) else None,
                            status="open",
                            min_responses=5,
                            target_responses=20,
                            responses_count=0,
                        ))
                        diag = await db.get(Diagnostic, diagnostic_id)
                        if diag:
                            diag.status = "awaiting_responses"
                        await db.commit()
                        log.info("SurveySession created — pipeline paused. Token: %s", survey_token)
                        # Notify survey ready
                        from api.notifications import notify_survey_ready
                        from api.config import settings as _s
                        await notify_survey_ready(diagnostic_id, payload.get("organization_name", ""), survey_token, _s.app_url)
                        return {"status": "awaiting_responses", "survey_token": survey_token}
            else:
                log.warning("g09a_preguntas output empty — skipping survey creation")

    # ── 3. Completion — always direct, no human review gate ─────────────────
    async with SessionLocal() as db:
        diagnostic = await db.get(Diagnostic, diagnostic_id)
        if diagnostic:
            # Collect alerts from pipeline outputs (IRR, delta_sigma)
            alerts = _collect_pipeline_alerts(context)
            if alerts:
                existing = diagnostic.rule_results or []
                diagnostic.rule_results = existing + alerts

            diagnostic.status       = "completed"
            diagnostic.completed_at = datetime.now(timezone.utc)
            await db.commit()

            from api.notifications import notify_completed
            qa_score = context.get("g14_qa_control", {}).get("qa_score") if isinstance(context.get("g14_qa_control"), dict) else None
            await notify_completed(diagnostic_id, payload.get("organization_name", ""), qa_score)

    return {"status": "completed"}


def _find_route(tool: str, models: list[dict]) -> dict:
    for r in models:
        if tool in r.get("matched_tools", []):
            return r
    return {"primary": "gemini", "fallback": "anthropic", "max_tokens": 8000, "temperature": 0.2}


def _infer_review_type(gov: dict) -> str:
    reasons = " ".join(gov.get("decision", {}).get("reasons", []))
    if "publish"  in reasons.lower(): return "publication"
    if "irr"      in reasons.lower(): return "irr_followup"
    if "delta"    in reasons.lower(): return "critical_gap"
    if "autonomy" in reasons.lower(): return "autonomy_promotion"
    return "publication"


def _collect_pipeline_alerts(context: dict) -> list[dict]:
    """
    Collect informational alerts and audit entries from pipeline outputs.
    Stored in rule_results as LOG_ONLY entries — no action required, fully auditable.
    """
    alerts = []

    # ── Scoring audit trail ───────────────────────────────────────────────────
    # Record the reverse-scoring correction that was applied before G10a.
    # This makes the correction verifiable: anyone can check which items were
    # corrected and confirm the formula used.
    scoring_audit = context.get("scoring_audit")
    if isinstance(scoring_audit, dict) and scoring_audit.get("reverse_scored_items"):
        alerts.append({
            "rule_id":  "SCORING-AUDIT",
            "outcome":  "LOG_ONLY",
            "severity": "INFO",
            "message":  (
                f"Reverse-score correction applied to items: "
                f"{scoring_audit.get('reverse_scored_items')}. "
                f"Formula: {scoring_audit.get('correction_formula')}. "
                f"Applied by: {scoring_audit.get('applied_by')}. "
                f"Responses processed: {scoring_audit.get('n_responses_corrected')}."
            ),
            "audit_detail": scoring_audit,
        })

    # ── G10a scoring audit from output ────────────────────────────────────────
    # Also capture what G10a itself reported in its scoring_audit field.
    g10a = context.get("g10a_scoring", {})
    if isinstance(g10a, dict):
        g10a_audit = g10a.get("scoring_audit")
        if isinstance(g10a_audit, dict):
            alerts.append({
                "rule_id":  "G10A-SCORING-AUDIT",
                "outcome":  "LOG_ONLY",
                "severity": "INFO",
                "message":  (
                    f"G10a scoring audit: data_source={g10a.get('scoring_summary', {}).get('data_source', '?')}, "
                    f"n_respondents={g10a.get('scoring_summary', {}).get('n_respondents', '?')}, "
                    f"reverse_scored_items={g10a_audit.get('reverse_scored_items', [])}."
                ),
                "audit_detail": g10a_audit,
            })

    # ── IRR alert ─────────────────────────────────────────────────────────────
    irr = context.get("irr_calculator", {})
    if isinstance(irr, dict):
        alpha = irr.get("krippendorff_alpha")
        if alpha is not None and alpha < 0.70:
            alerts.append({
                "rule_id": "IRR-LOW",
                "outcome": "LOG_ONLY",
                "severity": "MEDIUM",
                "message": f"IRR bajo: α Krippendorff = {alpha:.2f} (mínimo recomendado: 0.70). Las respuestas entre niveles jerárquicos fueron inconsistentes.",
            })

    # ── Delta sigma alert ─────────────────────────────────────────────────────
    scoring = context.get("g10a_scoring", {})
    if isinstance(scoring, dict):
        delta = scoring.get("delta_sigma", {})
        if isinstance(delta, dict):
            max_gap = delta.get("max_gap", 0)
            if max_gap > 2.0:
                alerts.append({
                    "rule_id": "DELTA-SIGMA-CRITICAL",
                    "outcome": "LOG_ONLY",
                    "severity": "HIGH",
                    "message": f"Brecha de percepción crítica: δσ = {max_gap:.1f}. La dirección y los operarios tienen visiones significativamente distintas del proceso.",
                })

    # ── QA score alert ────────────────────────────────────────────────────────
    qa = context.get("g14_qa_control", {})
    if isinstance(qa, dict):
        qa_score = qa.get("qa_score")
        if qa_score is not None and qa_score < 85:
            alerts.append({
                "rule_id": "QA-LOW",
                "outcome": "LOG_ONLY",
                "severity": "MEDIUM",
                "message": f"QA Score bajo: {qa_score}/100 (mínimo recomendado: 85). El informe puede requerir revisión adicional.",
            })

    return alerts


async def run_diagnostic_from_g10a(diagnostic_id: str) -> dict:
    """
    Continue pipeline execution from G10a after survey is closed.
    Reads real survey responses from DB and passes them to G10a.
    """
    import json
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from api.config import settings
    from api.db import get_async_session_local
    from api.models import Diagnostic, HumanReview, PipelineStage, SurveyResponse, SurveySession
    from api.pipeline.executor import PipelineExecutor

    SessionLocal = get_async_session_local()
    executor = PipelineExecutor(settings)

    # ── Load diagnostic and survey responses ─────────────────────────────────
    async with SessionLocal() as db:
        result = await db.execute(
            select(Diagnostic)
            .options(selectinload(Diagnostic.stages))
            .where(Diagnostic.id == diagnostic_id)
        )
        diagnostic = result.scalar_one_or_none()
        if not diagnostic:
            return {"error": "diagnostic not found"}

        # Get survey session and responses
        survey_result = await db.execute(
            select(SurveySession).where(SurveySession.diagnostic_id == diagnostic_id)
        )
        survey = survey_result.scalar_one_or_none()

        responses_data = []
        if survey:
            resp_result = await db.execute(
                select(SurveyResponse).where(SurveyResponse.session_id == survey.id)
            )
            responses = resp_result.scalars().all()
            responses_data = [
                {
                    "role": r.role,
                    "answers": r.answers,
                    "open_answers": r.open_answers or {},
                }
                for r in responses
            ]

        # ── Build reverse-scored question map from G09a instrument ───────────
        # Apply reverse-scoring correction BEFORE passing to G10a.
        # This is deterministic Python — not delegated to the LLM.
        # Formula: corrected = (max_scale + 1) - raw  →  for Likert 1-5: 6 - raw
        reverse_scored_ids: set = set()
        g09a_output = None
        for stage in diagnostic.stages:
            if stage.tool_name == "g09a_preguntas" and stage.status == "completed" and stage.output:
                g09a_output = stage.output.get("output", stage.output)
                if isinstance(g09a_output, dict):
                    # Handle raw_output case (JSON stored as string)
                    if "raw_output" in g09a_output and len(g09a_output) == 1:
                        import json as _json
                        raw_str = g09a_output["raw_output"]
                        start = raw_str.find("{")
                        end   = raw_str.rfind("}")
                        if start != -1 and end > start:
                            try:
                                g09a_output = _json.loads(raw_str[start:end + 1])
                            except Exception:
                                pass
                    questions = g09a_output.get("questions", []) if isinstance(g09a_output, dict) else []
                    for q in questions:
                        if q.get("reverse_scored") is True:
                            reverse_scored_ids.add(q.get("id", ""))
                break

        if reverse_scored_ids:
            log.info(
                "Applying reverse-score correction to %d items: %s",
                len(reverse_scored_ids), sorted(reverse_scored_ids)
            )

        def _apply_reverse_scoring(answers: dict) -> dict:
            """Apply Likert 1-5 reverse correction: corrected = 6 - raw."""
            corrected = {}
            for qid, val in answers.items():
                if qid in reverse_scored_ids and isinstance(val, (int, float)):
                    corrected[qid] = 6 - int(val)
                else:
                    corrected[qid] = val
            return corrected

        # Apply correction to all responses
        if reverse_scored_ids and responses_data:
            responses_data = [
                {
                    "role":         r["role"],
                    "answers":      _apply_reverse_scoring(r["answers"]),
                    "open_answers": r["open_answers"],
                }
                for r in responses_data
            ]
            log.info("Reverse-score correction applied to %d responses", len(responses_data))

        # Rebuild context from completed stages FIRST
        context: dict = {
            "organization_name": diagnostic.organization_name,
            "domain":            diagnostic.domain,
            "subprocess":        diagnostic.subprocess,
            "objective":         diagnostic.objective or "",
            "size_org":          diagnostic.size_org or "",
        }

        for stage in diagnostic.stages:
            if stage.status == "completed" and stage.output:
                output = stage.output.get("output", stage.output)
                if isinstance(output, dict):
                    context[stage.tool_name] = output

        # ── Build scoring audit trail ─────────────────────────────────────────
        # This goes into the context so G10a includes it in its output,
        # making the reverse-score correction fully auditable in the DB.
        scoring_audit = {
            "reverse_scored_items": sorted(reverse_scored_ids),
            "correction_formula":   "corrected = 6 - raw  (Likert 1-5, applied before scoring)",
            "n_responses_corrected": len(responses_data) if reverse_scored_ids else 0,
            "applied_by":           "pipeline_runner.py — deterministic Python, not LLM",
        }
        context["scoring_audit"] = scoring_audit
        log.info("Scoring audit trail: %s", scoring_audit)

        # Inject real survey responses into context for G10a
        if responses_data:
            # Serialize responses — keep full fidelity up to 50 respondents.
            # If there are more, sample proportionally across roles to stay within
            # the context window while preserving role distribution.
            MAX_RESPONSES_IN_CONTEXT = 50
            if len(responses_data) > MAX_RESPONSES_IN_CONTEXT:
                from collections import defaultdict
                import random
                by_role: dict = defaultdict(list)
                for r in responses_data:
                    by_role[r["role"]].append(r)
                sampled = []
                per_role = MAX_RESPONSES_IN_CONTEXT // max(len(by_role), 1)
                for role_responses in by_role.values():
                    sampled.extend(random.sample(role_responses, min(per_role, len(role_responses))))
                # Fill remaining slots
                remaining = MAX_RESPONSES_IN_CONTEXT - len(sampled)
                all_remaining = [r for r in responses_data if r not in sampled]
                sampled.extend(random.sample(all_remaining, min(remaining, len(all_remaining))))
                context["survey_responses_real"] = json.dumps(sampled, ensure_ascii=False)
                log.info(
                    "Sampled %d/%d survey responses for context (role-stratified)",
                    len(sampled), len(responses_data)
                )
            else:
                context["survey_responses_real"] = json.dumps(responses_data, ensure_ascii=False)
            context["survey_responses_count"] = str(len(responses_data))
            log.info("Injected %d real survey responses into context", len(responses_data))

        # Get stages that still need to run (G10a onwards)
        analysis_tools = [
            "g10a_scoring", "g10b_psicometria", "g11a_bayesiano", "g11b_nlp",
            "irr_calculator", "scoring_engine", "g12_hallazgos",
            "g13_redactor", "g14_qa_control", "docx_generator",
        ]
        
        # Create missing stages if they don't exist
        existing_tool_names = {s.tool_name for s in diagnostic.stages}
        missing_tools = [t for t in analysis_tools if t not in existing_tool_names]
        
        if missing_tools:
            log.info("Creating %d missing stages for continuation: %s", len(missing_tools), missing_tools)
            async with SessionLocal() as db:
                for tool_name in missing_tools:
                    new_stage = PipelineStage(
                        diagnostic_id=diagnostic_id,
                        tool_name=tool_name,
                        phase="analysis",
                        status="pending"
                    )
                    db.add(new_stage)
                await db.commit()
                # Reload diagnostic with new stages
                result = await db.execute(
                    select(Diagnostic)
                    .options(selectinload(Diagnostic.stages))
                    .where(Diagnostic.id == diagnostic_id)
                )
                diagnostic = result.scalar_one()
        
        pending_stages = [
            s for s in diagnostic.stages
            if s.tool_name in analysis_tools and s.status in ("pending", "failed")
        ]
        # Sort by analysis_tools order
        pending_stages.sort(key=lambda s: analysis_tools.index(s.tool_name)
                            if s.tool_name in analysis_tools else 99)

        payload = {
            "processing_profile": {
                "publish_report": False,
                "issue_certificate": True,
            }
        }

    log.info("Resuming pipeline from G10a for diagnostic %s with %d tools", diagnostic_id, len(pending_stages))

    # ── Execute remaining tools ───────────────────────────────────────────────
    for stage in pending_stages:
        tool_name = stage.tool_name
        stage_id  = stage.id

        async with SessionLocal() as db:
            s = await db.get(PipelineStage, stage_id)
            if s:
                s.status     = "running"
                s.started_at = datetime.now(timezone.utc)
            await db.commit()

        route = {"primary": "gemini", "fallback": "anthropic", "max_tokens": 8192, "temperature": 0.2}
        t0 = time.monotonic()

        try:
            res = await executor.run_tool(tool_name, context, route)
            context[tool_name] = res.get("output", "")
            status     = "completed"
            model_used = res.get("model_used")
            tokens     = res.get("tokens_used")
            output     = res
            log.info("Tool %s completed — %s tokens", tool_name, tokens)

            # ── Audit log for G10a data source ───────────────────────────────
            if tool_name == "g10a_scoring":
                g10a_out = res.get("output", {})
                data_src = g10a_out.get("scoring_summary", {}).get("data_source", "unknown") if isinstance(g10a_out, dict) else "unknown"
                n_resp   = g10a_out.get("scoring_summary", {}).get("n_respondents", 0) if isinstance(g10a_out, dict) else 0
                log.info(
                    "G10a scoring data_source=%s n_respondents=%s for diagnostic %s",
                    data_src, n_resp, diagnostic_id
                )

        except Exception as exc:
            status     = "failed"
            model_used = None
            tokens     = None
            output     = {"error": str(exc)}
            log.error("Tool %s failed: %s", tool_name, exc)

        latency = int((time.monotonic() - t0) * 1000)

        async with SessionLocal() as db:
            s = await db.get(PipelineStage, stage_id)
            if s:
                s.status       = status
                s.model_used   = model_used
                s.tokens_used  = tokens
                s.output       = output
                s.latency_ms   = latency
                s.completed_at = datetime.now(timezone.utc)
            if status == "failed":
                diag = await db.get(Diagnostic, diagnostic_id)
                if diag:
                    diag.status = "failed"
                    diag.decision = "DENY"
                    diag.completed_at = datetime.now(timezone.utc)
                    diag.rule_results = [{
                        "rule_id": "PIPELINE-LLM-FAIL-CLOSED",
                        "outcome": "FAIL",
                        "severity": "CRITICAL",
                        "message": f"Etapa {tool_name} falló: {output.get('error', 'error')}",
                    }]
            await db.commit()

        if status == "failed":
            return {
                "status": "failed",
                "tool": tool_name,
                "error": output.get("error") if isinstance(output, dict) else str(output),
            }

    # ── Mark diagnostic complete ──────────────────────────────────────────────
    async with SessionLocal() as db:
        diag = await db.get(Diagnostic, diagnostic_id)
        if diag:
            alerts = _collect_pipeline_alerts(context)
            if alerts:
                existing = diag.rule_results or []
                diag.rule_results = existing + alerts
            diag.status       = "completed"
            diag.completed_at = datetime.now(timezone.utc)
        await db.commit()

    log.info("Pipeline completed from G10a for diagnostic %s", diagnostic_id)
    return {"status": "completed"}
