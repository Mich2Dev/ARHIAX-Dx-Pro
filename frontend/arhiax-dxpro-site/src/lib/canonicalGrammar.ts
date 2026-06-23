import { GRAMMAR_RULES, type GrammarSeverity, type GrammarAudience } from '../data/canonicalGrammarRules'

const SEVERITY_ORDER: Record<string, number> = { critical: 0, major: 1, minor: 2, advisory: 3 }

const AUDIENCE_ALIASES: Record<GrammarAudience, GrammarAudience[]> = {
  client: ['client', 'executive'],
  executive: ['executive', 'client'],
  internal: ['internal'],
  technical: ['technical', 'internal'],
}

export type GrammarFinding = {
  ruleId: string
  block: string
  severity: GrammarSeverity
  message: string
  detectedText: string
  suggestion?: string
  rationale: string
  index?: number
}

export type GrammarReport = {
  score: number
  critical: number
  major: number
  minor: number
  advisory: number
  total: number
  findings: GrammarFinding[]
  text: string
  timestamp: string
  audience: string
}

export type GrammarException = {
  findingId: string
  ruleId: string
  detectedText: string
  reason: string
  reviewer: string
  createdAt: string
}

export type CanonicalReviewState = {
  reviewed: boolean
  report?: GrammarReport
  source: 'manual' | 'case' | 'report'
  reviewedAt?: string
  exceptions?: GrammarException[]
}

function appliesToAudience(rule: { audience?: GrammarAudience[] }, audience: GrammarAudience): boolean {
  if (!rule.audience || rule.audience.length === 0) return true
  const aliases = AUDIENCE_ALIASES[audience] ?? [audience]
  return aliases.some((a) => rule.audience!.includes(a))
}

export function lintText(text: string, audience: GrammarAudience = 'client'): GrammarReport {
  const findings: GrammarFinding[] = []

  for (const rule of GRAMMAR_RULES) {
    if (!appliesToAudience(rule, audience)) continue

    const pattern = rule.pattern.flags.includes('g')
      ? rule.pattern
      : new RegExp(rule.pattern.source, rule.pattern.flags + 'g')
    const matches = text.matchAll(pattern)
    for (const match of matches) {
      const detectedText = match[0]
      if (detectedText.length > 200) continue

      findings.push({
        ruleId: rule.id,
        block: rule.block,
        severity: rule.severity,
        message: rule.title,
        detectedText,
        suggestion: rule.suggestion,
        rationale: rule.rationale,
        index: match.index ?? 0,
      })
    }
  }

  findings.sort(
    (a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4) ||
      (a.index ?? 0) - (b.index ?? 0),
  )

  const critical = findings.filter((f) => f.severity === 'critical').length
  const major = findings.filter((f) => f.severity === 'major').length
  const minor = findings.filter((f) => f.severity === 'minor').length
  const advisory = findings.filter((f) => f.severity === 'advisory').length
  const total = findings.length

  const score = Math.max(0, Math.min(100, Math.round(100 - (critical * 25 + major * 8 + minor * 3 + advisory * 1))))

  return {
    score,
    critical,
    major,
    minor,
    advisory,
    total,
    findings,
    text,
    timestamp: new Date().toISOString(),
    audience,
  }
}

export type PublishDecision = { allowed: boolean; reason?: string; confirmRequired?: boolean }

export function canPublish(report: GrammarReport, exceptions?: GrammarException[]): PublishDecision {
  const valid = (exceptions ?? []).filter((e) => e.reason.trim().length > 0)
  const critical = report.findings.filter(
    (f) => f.severity === 'critical' && !valid.find((e) => e.ruleId === f.ruleId && e.detectedText === f.detectedText),
  )
  if (critical.length > 0) {
    return { allowed: false, reason: 'Hallazgos críticos pendientes. Corrija antes de publicar.' }
  }
  const major = report.findings.filter(
    (f) => f.severity === 'major' && !valid.find((e) => e.ruleId === f.ruleId && e.detectedText === f.detectedText),
  )
  if (major.length > 0) {
    return { allowed: true, reason: 'Hallazgos mayores detectados. Requiere confirmación.', confirmRequired: true }
  }
  return { allowed: true }
}

export function compileReportText(report: GrammarReport, exceptions?: GrammarException[], source?: string): string {
  const lines: string[] = []
  lines.push('# Revisión canónica ARHIAX')
  lines.push('')
  lines.push(`**Fecha:** ${new Date(report.timestamp).toLocaleString()}`)
  lines.push(`**Audiencia:** ${report.audience}`)
  lines.push(`**Fuente:** ${source ?? 'manual'}`)
  lines.push(`**Score:** ${report.score}/100`)
  const pub = canPublish(report, exceptions)
  lines.push(`**Estado de publicación:** ${pub.allowed ? (pub.confirmRequired ? 'Requiere confirmación' : 'Apto') : 'Bloqueado'}`)
  lines.push('')
  lines.push('## Resumen')
  lines.push('')
  lines.push(`- Críticos: ${report.critical}`)
  lines.push(`- Mayores: ${report.major}`)
  lines.push(`- Menores: ${report.minor}`)
  lines.push(`- Advertencias: ${report.advisory}`)
  lines.push('')
  if (report.findings.length === 0) {
    lines.push('Sin hallazgos.')
    return lines.join('\n')
  }
  lines.push('## Hallazgos')
  lines.push('')
  for (const f of report.findings) {
    const exc = exceptions?.find((e) => e.ruleId === f.ruleId && e.detectedText === f.detectedText)
    lines.push(`### ${f.ruleId}`)
    lines.push('')
    lines.push(`- **Severidad:** ${f.severity.toUpperCase()}`)
    lines.push(`- **Texto detectado:** "${f.detectedText}"`)
    lines.push(`- **Sugerencia:** ${f.suggestion ?? '—'}`)
    lines.push(`- **Racional:** ${f.rationale}`)
    lines.push(`- **Estado:** ${exc ? `Excepcionado — ${exc.reason}` : 'Pendiente'}`)
    if (exc) {
      lines.push(`- **Justificación:** ${exc.reason}`)
      lines.push(`- **Revisor:** ${exc.reviewer}`)
    }
    lines.push('')
  }
  return lines.join('\n')
}
