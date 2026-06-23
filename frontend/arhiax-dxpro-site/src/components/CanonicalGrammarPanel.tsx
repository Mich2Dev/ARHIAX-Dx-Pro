import { useState, useMemo } from 'react'
import { lintText, canPublish, compileReportText, type GrammarReport, type GrammarException } from '../lib/canonicalGrammar'
import type { GrammarAudience } from '../data/canonicalGrammarRules'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#c93a3a',
  major: '#b87333',
  minor: '#5b7f9a',
  advisory: '#6b8f71',
}

const SEVERITY_LABELS: Record<string, string> = {
  critical: 'Crítico',
  major: 'Mayor',
  minor: 'Menor',
  advisory: 'Advertencia',
}

type Props = {
  onReport?: (r: GrammarReport | null) => void
  caseText?: string
  hasCase?: boolean
}

export default function CanonicalGrammarPanel({ onReport, caseText, hasCase }: Props) {
  const [text, setText] = useState('')
  const [audience, setAudience] = useState<GrammarAudience>('client')
  const [report, setReport] = useState<GrammarReport | null>(null)
  const [copied, setCopied] = useState(false)
  const [exceptions, setExceptions] = useState<GrammarException[]>([])
  const [excRuleId, setExcRuleId] = useState('')
  const [excText, setExcText] = useState('')
  const [excReason, setExcReason] = useState('')

  const sampleTexts = [
    'Arhiax DxPro opera como herramienta de diagnóstico.',
    'El informe evalúa procesos, datos, y gobernanza.',
    'La aprobación todavía no está lista.',
    'La recomendación hace sentido para el cliente.',
    'Es importante mencionar que el custodio validó el desvelamiento en Enero.',
  ]

  function handleLint(targetText?: string) {
    const r = lintText(targetText ?? text, audience)
    setReport(r)
    setExceptions([])
    onReport?.(r)
  }

  function loadSample(sample: string) {
    setText(sample)
    setReport(null)
  }

  function loadCaseText() {
    if (caseText) {
      setText(caseText)
      handleLint(caseText)
    }
  }

  async function handleCopy() {
    if (!report) return
    const lines = compileReportText(report, exceptions.length > 0 ? exceptions : undefined, 'manual')
    try {
      await navigator.clipboard.writeText(lines)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard no disponible (HTTP o permisos)
    }
  }

  function addException() {
    if (!excReason.trim()) return
    const exc: GrammarException = {
      findingId: `${excRuleId}-${Date.now()}`,
      ruleId: excRuleId,
      detectedText: excText,
      reason: excReason.trim(),
      reviewer: 'Consultor Lider',
      createdAt: new Date().toISOString(),
    }
    setExceptions((prev) => [...prev, exc])
    setExcRuleId('')
    setExcText('')
    setExcReason('')
  }

  function removeException(ruleId: string, detectedText: string) {
    setExceptions((prev) => prev.filter((e) => !(e.ruleId === ruleId && e.detectedText === detectedText)))
  }

  const publishCheck = useMemo(
    () => (report ? canPublish(report, exceptions.length > 0 ? exceptions : undefined) : null),
    [report, exceptions],
  )

  const isExcepted = (ruleId: string, detectedText: string) =>
    exceptions.some((e) => e.ruleId === ruleId && e.detectedText === detectedText)

  return (
    <section className="grammar-section">
      <div className="command-band">
        <div className="command-copy">
          <p className="section-code">§ gramática canónica</p>
          <h2>Revisión canónica</h2>
          <p>
            ARHIAX Dx Pro no debe publicar como cliente final un texto que contradiga la voz canónica de ARHIAX.
            Pegue un fragmento de informe, microcopy o texto generado para validarlo contra la Gramática Canónica v1.0.
          </p>
        </div>
        <div className="actions">
          <button className="primary-action" onClick={() => handleLint()} disabled={!text.trim()} type="button">
            Revisar texto
          </button>
          <button className="secondary-action" onClick={() => void handleCopy()} disabled={!report} type="button">
            {copied ? 'Copiado' : 'Copiar reporte'}
          </button>
          {hasCase && (
            <button className="secondary-action" onClick={loadCaseText} disabled={!caseText} type="button">
              Revisar texto del expediente actual
            </button>
          )}
        </div>
      </div>

      <div className="grammar-input">
        <div className="grammar-input-toolbar">
          <span className="grammar-label">Audiencia</span>
          <select value={audience} onChange={(e) => setAudience(e.target.value as GrammarAudience)}>
            <option value="client">Cliente / Ejecutivo</option>
            <option value="internal">Interno / Técnico</option>
          </select>
          <span className="grammar-label">Muestras</span>
          <div className="grammar-samples">
            {sampleTexts.map((s, i) => (
              <button key={i} className="sample-chip" onClick={() => loadSample(s)} type="button">
                Muestra {i + 1}
              </button>
            ))}
          </div>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Pegue el texto por revisar..."
          spellCheck={false}
        />
      </div>

      {report && (
        <div className="grammar-results">
          <div className="grammar-scorebar">
            <div className={`grammar-score ${report.score >= 80 ? 'score-ok' : report.score >= 50 ? 'score-warn' : 'score-bad'}`}>
              <strong>{report.score}</strong>
              <span>/100</span>
            </div>
            <div className="grammar-counts">
              {report.critical > 0 && <span className="count critical">{report.critical} críticos</span>}
              {report.major > 0 && <span className="count major">{report.major} mayores</span>}
              {report.minor > 0 && <span className="count minor">{report.minor} menores</span>}
              {report.advisory > 0 && <span className="count advisory">{report.advisory} advertencias</span>}
              {report.total === 0 && <span className="count clean">Sin hallazgos</span>}
            </div>
            <div className="grammar-audit-info">
              <span>{new Date(report.timestamp).toLocaleTimeString()}</span>
              <span>{report.audience === 'client' ? 'Cliente' : 'Interno'}</span>
            </div>
          </div>

          {publishCheck && !publishCheck.allowed && (
            <div className="grammar-blocker">
              <strong>Publicación bloqueada.</strong> {publishCheck.reason}
            </div>
          )}
          {publishCheck && publishCheck.allowed && publishCheck.confirmRequired && (
            <div className="grammar-warning">
              <strong>Requiere confirmación.</strong> {publishCheck.reason}
            </div>
          )}
          {publishCheck && publishCheck.allowed && !publishCheck.confirmRequired && report.total > 0 && (
            <div className="grammar-clear">
              <strong>Texto apto para publicación.</strong> Hallazgos menores exentos.
            </div>
          )}
          {publishCheck && publishCheck.allowed && !publishCheck.confirmRequired && report.total === 0 && (
            <div className="grammar-clear">
              <strong>Texto apto para publicación.</strong> Sin restricciones canónicas.
            </div>
          )}

          {exceptions.length > 0 && (
            <div className="grammar-exceptions">
              <p className="section-code">excepciones registradas ({exceptions.length})</p>
              {exceptions.map((e) => (
                <div key={e.findingId} className="exception-row">
                  <span><strong>{e.ruleId}</strong> &ldquo;{e.detectedText}&rdquo;</span>
                  <span>{e.reason}</span>
                  <button onClick={() => removeException(e.ruleId, e.detectedText)} type="button">×</button>
                </div>
              ))}
            </div>
          )}

          {report.findings.length > 0 && (
            <div className="grammar-findings">
              <div className="grammar-findings-header">
                <span>Regla</span>
                <span>Severidad</span>
                <span>Texto detectado</span>
                <span>Sugerencia</span>
                <span>Acción</span>
              </div>
              {report.findings.map((f, i) => {
                const excepted = isExcepted(f.ruleId, f.detectedText)
                return (
                  <div key={i} className={`grammar-finding-row ${excepted ? 'excepted' : ''}`}>
                    <span className="finding-rule">
                      <strong>{f.ruleId}</strong>
                      <em>{f.block}</em>
                    </span>
                    <span className="finding-severity" style={{ color: SEVERITY_COLORS[f.severity] }}>
                      {SEVERITY_LABELS[f.severity]}
                    </span>
                    <span className="finding-text">&ldquo;{f.detectedText}&rdquo;</span>
                    <span className="finding-suggestion">{f.suggestion ?? '—'}</span>
                    <span className="finding-action">
                      {excepted ? (
                        <span className="excepted-badge">Excepcionado</span>
                      ) : (
                        (f.severity === 'critical' || f.severity === 'major') && (
                          <button
                            className="exception-btn"
                            onClick={() => { setExcRuleId(f.ruleId); setExcText(f.detectedText) }}
                            type="button"
                          >
                            Justificar
                          </button>
                        )
                      )}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {excRuleId && (
            <div className="grammar-exc-form">
              <p className="section-code">justificar excepción — {excRuleId}</p>
              <p className="exc-detected">&ldquo;{excText}&rdquo;</p>
              <textarea
                value={excReason}
                onChange={(e) => setExcReason(e.target.value)}
                placeholder="Escriba la razón por la cual este hallazgo debe exceptuarse..."
                spellCheck={false}
              />
              <div className="exc-actions">
                <button className="primary-action" onClick={addException} disabled={!excReason.trim()} type="button">
                  Registrar excepción
                </button>
                <button className="secondary-action" onClick={() => { setExcRuleId(''); setExcReason('') }} type="button">
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grammar-checklist">
        <p className="section-code">checklist final</p>
        <div className="checklist-items">
          <label><input type="checkbox" /> No hay caracteres rotos (mojibake)</label>
          <label><input type="checkbox" /> ARHIAX, Dx Pro y Governex Thinking escritos correctamente</label>
          <label><input type="checkbox" /> No hay coma de Oxford</label>
          <label><input type="checkbox" /> No hay calcos evidentes del inglés</label>
          <label><input type="checkbox" /> Meses y días en minúscula cuando corresponde</label>
          <label><input type="checkbox" /> El registro corresponde a la audiencia</label>
          <label><input type="checkbox" /> El texto no suena mecánico (falsa fluidez)</label>
          <label><input type="checkbox" /> No se mezclan términos internos con vocabulario de cliente</label>
          <label><input type="checkbox" /> El texto puede publicarse sin contradecir la voz ARHIAX</label>
        </div>
      </div>
    </section>
  )
}
