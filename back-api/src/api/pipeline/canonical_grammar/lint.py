from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from api.pipeline.canonical_grammar.models import (
    GrammarAudience,
    GrammarFinding,
    GrammarException,
    GrammarReport,
    PublishDecision,
)
from api.pipeline.canonical_grammar.rules import CATALOG_BY_ID, get_rules_for_audience


def _make_finding_id() -> str:
    import uuid
    return str(uuid.uuid4())


def lint_text(
    text: str,
    audience: GrammarAudience = "client",
    source: str = "manual",
    exceptions: list[GrammarException] | None = None,
) -> GrammarReport:
    findings: list[GrammarFinding] = []
    excepted_ids: set[str] = set()
    if exceptions:
        for exc in exceptions:
            if exc.reason.strip():
                excepted_ids.add(f"{exc.rule_id}||{exc.detected_text}")

    rules = get_rules_for_audience(audience)

    for rule in rules:
        pattern = re.compile(rule.pattern, re.UNICODE)
        for match in pattern.finditer(text):
            detected = match.group(0)
            if len(detected) > 200:
                continue

            finding_id = _make_finding_id()
            key = f"{rule.id}||{detected}"
            is_excepted = key in excepted_ids

            findings.append(GrammarFinding(
                finding_id=finding_id,
                rule_id=rule.id,
                block=rule.block,
                severity=rule.severity,
                message=rule.title,
                detected_text=detected,
                suggestion=rule.suggestion,
                rationale=rule.rationale,
                index=match.start(),
                excepted=is_excepted,
            ))

    findings.sort(key=lambda f: ({"critical": 0, "major": 1, "minor": 2, "advisory": 3}.get(f.severity, 4), f.index or 0))

    critical = sum(1 for f in findings if f.severity == "critical")
    major = sum(1 for f in findings if f.severity == "major")
    minor = sum(1 for f in findings if f.severity == "minor")
    advisory = sum(1 for f in findings if f.severity == "advisory")
    total = len(findings)

    score = max(0, min(100, round(100 - (critical * 25 + major * 8 + minor * 3 + advisory * 1))))

    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()

    publish_decision = _can_publish_inner(findings, exceptions or [])

    return GrammarReport(
        score=score,
        critical=critical,
        major=major,
        minor=minor,
        advisory=advisory,
        total=total,
        findings=findings,
        text_hash_sha256=text_hash,
        timestamp=timestamp,
        audience=audience,
        source=source,
        publish_decision=publish_decision,
    )


def _can_publish_inner(
    findings: list[GrammarFinding],
    exceptions: list[GrammarException],
) -> PublishDecision:
    valid_reasons = {e.reason for e in exceptions if e.reason.strip()}
    excepted_keys: set[str] = set()
    for exc in exceptions:
        if exc.reason.strip():
            excepted_keys.add(f"{exc.rule_id}||{exc.detected_text}")

    has_critical = any(f.severity == "critical" for f in findings)
    has_major = any(f.severity == "major" for f in findings)

    critical_open = [
        f for f in findings
        if f.severity == "critical" and f"{f.rule_id}||{f.detected_text}" not in excepted_keys
    ]
    if critical_open:
        return PublishDecision(
            allowed=False,
            reason="Hallazgos críticos pendientes. Corrija antes de publicar.",
        )

    major_open = [
        f for f in findings
        if f.severity == "major" and f"{f.rule_id}||{f.detected_text}" not in excepted_keys
    ]
    if major_open:
        return PublishDecision(
            allowed=True,
            confirm_required=True,
            reason="Hallazgos mayores detectados. Requiere confirmación o justificación.",
        )

    # Si todos los críticos fueron exceptuados, requiere confirmación
    if has_critical:
        return PublishDecision(
            allowed=True,
            confirm_required=True,
            reason="Hallazgos críticos exceptuados. Requiere confirmación.",
        )

    # Si todos los mayores fueron exceptuados, publicar sin confirmación
    if has_major:
        return PublishDecision(allowed=True)

    return PublishDecision(allowed=True)


def can_publish(
    report: GrammarReport,
    exceptions: list[GrammarException] | None = None,
) -> PublishDecision:
    return _can_publish_inner(report.findings, exceptions or [])


def compile_report_text(
    report: GrammarReport,
    exceptions: list[GrammarException] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# Revisión canónica ARHIAX")
    lines.append("")
    lines.append(f"**Fecha:** {report.timestamp}")
    lines.append(f"**Audiencia:** {report.audience}")
    lines.append(f"**Fuente:** {report.source}")
    lines.append(f"**Score:** {report.score}/100")
    lines.append(f"**Hash:** {report.text_hash_sha256[:16]}...")
    pub = can_publish(report, exceptions)
    lines.append(
        f"**Estado de publicación:** "
        f"{'Bloqueado' if not pub.allowed else 'Requiere confirmación' if pub.confirm_required else 'Apto'}"
    )
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- Críticos: {report.critical}")
    lines.append(f"- Mayores: {report.major}")
    lines.append(f"- Menores: {report.minor}")
    lines.append(f"- Advertencias: {report.advisory}")
    lines.append("")
    if not report.findings:
        lines.append("Sin hallazgos.")
        return "\n".join(lines)

    lines.append("## Hallazgos")
    lines.append("")
    for f in report.findings:
        exc = next(
            (e for e in (exceptions or []) if e.rule_id == f.rule_id and e.detected_text == f.detected_text),
            None,
        )
        lines.append(f"### {f.rule_id}")
        lines.append("")
        lines.append(f"- **Severidad:** {f.severity.upper()}")
        lines.append(f"- **Texto detectado:** \"{f.detected_text}\"")
        lines.append(f"- **Sugerencia:** {f.suggestion or '—'}")
        lines.append(f"- **Racional:** {f.rationale}")
        lines.append(f"- **Estado:** {'Excepcionado — ' + exc.reason if exc else 'Pendiente'}")
        if exc:
            lines.append(f"- **Justificación:** {exc.reason}")
            lines.append(f"- **Revisor:** {exc.reviewer}")
        lines.append("")

    return "\n".join(lines)
