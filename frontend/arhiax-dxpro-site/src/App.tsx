import { useMemo, useState } from 'react'
import './App.css'
import { useCases } from './hooks/useCases'
import { useDiagnosticRun } from './hooks/useDiagnosticRun'
import { apiRequest } from './lib/apiRequest'
import { canPublish, type GrammarReport, type GrammarException } from './lib/canonicalGrammar'
import DossierPanel from './components/DossierPanel'
import ApprovalPanel from './components/ApprovalPanel'
import ConfirmModal from './components/ConfirmModal'
import GrammarPanel from './components/GrammarPanel'

function buildCaseText(
  activeCase: ReturnType<typeof useCases>['selectedCase'],
  result: ReturnType<typeof useDiagnosticRun>['result'],
): string {
  const parts: string[] = []
  if (activeCase?.client?.legal_name) parts.push(`Cliente: ${activeCase.client.legal_name}`)
  if (activeCase?.client?.name) parts.push(`Cliente: ${activeCase.client.name}`)
  if (activeCase?.domain) parts.push(`Dominio: ${activeCase.domain}`)
  if (activeCase?.case_status) parts.push(`Estado del caso: ${activeCase.case_status}`)
  if (activeCase?.approval_status) parts.push(`Aprobación: ${activeCase.approval_status}`)
  const outcomes = result?.artifact?.stage_outcomes
  if (outcomes) {
    for (const [stage, info] of Object.entries(outcomes)) {
      if (info?.outcome) parts.push(`${stage}: ${info.outcome}`)
    }
  }
  const files = activeCase?.files ?? result?.artifact?.files ?? []
  for (const f of files) {
    parts.push(`Archivo: ${f.target} — ${f.path} (${f.size_bytes ?? 0} bytes)`)
  }
  return parts.join('\n')
}

function App() {
  const { cases, selectedCaseId, selectedCase, loadCases, loadCase, setSelectedCaseId } = useCases()
  const { payloadText, setPayloadText, result, setResult, restoreSample } = useDiagnosticRun()
  const [tab, setTab] = useState<'workspace' | 'grammar'>('workspace')
  const [status, setStatus] = useState('ready')
  const [error, setError] = useState('')
  const [grammarReport, setGrammarReport] = useState<GrammarReport | null>(null)
  const [grammarExceptions, setGrammarExceptions] = useState<GrammarException[]>([])
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false)

  async function runCase() {
    setStatus('running')
    setError('')
    try {
      const payload = JSON.parse(payloadText)
      const body = await apiRequest<{ artifact?: { case_id?: string } }>('/v1/agents/cases/run', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setResult(body as never)
      const caseId = body.artifact?.case_id ?? ''
      setSelectedCaseId(caseId)
      await loadCases()
      if (caseId) {
        await loadCase(caseId)
      }
      setStatus('ready')
    } catch (e) {
      setStatus('ready')
      setError(e instanceof SyntaxError ? 'El JSON del caso no es válido.' : 'No se pudo ejecutar el caso.')
    }
  }

  async function approve(
    action: 'approve' | 'publish' | 'reject',
    options?: { grammarConfirmed?: boolean },
  ) {
    if (!selectedCaseId) return
    setStatus(action)
    setError('')
    try {
      if (action === 'publish') {
        await apiRequest(`/v1/cases/${selectedCaseId}/publish`, {
          method: 'POST',
          body: JSON.stringify({
            case_id: selectedCaseId,
            action: 'publish',
            grammar_confirmed: options?.grammarConfirmed ?? false,
            reviewer: { name: 'Consultor Lider', role: 'engagement_manager' },
          }),
        })
      } else {
        await apiRequest('/v1/agents/cases/approval', {
          method: 'POST',
          body: JSON.stringify({
            consent: { action: 'ingest_to_llm', consents: { T1: true, T3: true } },
            case_id: selectedCaseId,
            action,
            reviewer: { name: 'Consultor Lider', role: 'engagement_manager' },
          }),
        })
      }
      await loadCases()
      await loadCase(selectedCaseId)
      setStatus('ready')
    } catch {
      setStatus('ready')
      setError('La transición de aprobación no fue aceptada por el runtime.')
    }
  }

  function handlePublishClick() {
    if (!selectedCaseId) return
    if (!grammarReport) {
      setPublishConfirmOpen(true)
      return
    }
    const decision = canPublish(grammarReport, grammarExceptions.length > 0 ? grammarExceptions : undefined)
    if (!decision.allowed) return
    if (decision.confirmRequired) {
      setPublishConfirmOpen(true)
      return
    }
    void approve('publish')
  }

  function confirmPublish() {
    setPublishConfirmOpen(false)
    void approve('publish', { grammarConfirmed: true })
  }

  const activeCase = selectedCase ?? (cases.length > 0 ? cases[0] : null)
  const files = activeCase?.files ?? result?.artifact?.files ?? []

  const caseText = useMemo(() => buildCaseText(activeCase, result), [activeCase, result])
  const hasCase = !!(activeCase?.case_id ?? result?.artifact?.case_id)

  const publishDecision = grammarReport
    ? canPublish(grammarReport, grammarExceptions.length > 0 ? grammarExceptions : undefined)
    : null

  function publishTitle(): string {
    if (!grammarReport) return 'Sin revisión canónica — publique solo si está seguro.'
    if (!publishDecision?.allowed) return 'No se puede publicar. Hay hallazgos canónicos críticos pendientes.'
    if (publishDecision?.confirmRequired) return 'Este expediente tiene hallazgos canónicos mayores. Para publicar debe corregirlos o justificar la excepción.'
    return ''
  }

  function publishDisabled(): boolean {
    if (!selectedCaseId) return true
    if (!grammarReport) return false
    if (!publishDecision?.allowed) return true
    return false
  }

  function handleGrammarReport(r: GrammarReport | null) {
    setGrammarReport(r)
    setGrammarExceptions([])
  }

  return (
    <main className="dx-shell">
      <aside className="rail" aria-label="Navegación principal">
        <a className="brand" href="#workspace" aria-label="ARHIAX Dx Pro">
          <img src="/logo-sinergia.png" alt="Sinergia Consulting Group" />
          <span>
            <strong>ARHIAX</strong>
            <em>Dx Pro</em>
          </span>
        </a>
        <nav>
          <a href="#workspace" onClick={() => setTab('workspace')}>Caso</a>
          <a href="#evidence" onClick={() => setTab('workspace')}>Evidencia</a>
          <a href="#approval" onClick={() => setTab('workspace')}>Aprobación</a>
          <a href="#exports" onClick={() => setTab('workspace')}>Entregables</a>
          <a href="#grammar" onClick={() => setTab('grammar')} className={tab === 'grammar' ? 'active-tab' : ''}>Gramática</a>
        </nav>
        <div className="rail-status">
          <span>Runtime</span>
          <strong>{status === 'ready' ? 'operativo' : status}</strong>
        </div>
      </aside>

      {tab === 'grammar' && (
        <GrammarPanel caseText={caseText} hasCase={hasCase} onReport={handleGrammarReport} />
      )}

      {tab === 'workspace' && (
      <section className="workspace" id="workspace">
        <header className="topbar">
          <div>
            <p className="section-code">§ 05 · consola operativa</p>
            <h1>ARHIAX Dx Pro</h1>
          </div>
          <button className="icon-button" onClick={() => void loadCases()} title="Actualizar casos" type="button">
            ↻
          </button>
        </header>

        {error && <p className="notice">{error}</p>}

        <section className="command-band" id="case-runner">
          <div className="command-copy">
            <p className="section-code">§ caso diagnóstico</p>
            <h2>Ejecutar ciclo gobernado</h2>
            <p>
              Dx Pro toma el caso, corre la fusión diagnóstica, genera reporte, renderiza, exporta y
              deja el expediente en revisión.
            </p>
          </div>
          <div className="actions">
            <button className="primary-action" onClick={() => void runCase()} disabled={status !== 'ready'} type="button">
              Ejecutar caso
            </button>
            <button className="secondary-action" onClick={restoreSample} type="button">
              Restaurar muestra
            </button>
          </div>
        </section>

        <section className="grid two">
          <article className="panel payload-panel">
            <div className="panel-head">
              <span>Input</span>
              <strong>JSON</strong>
            </div>
            <textarea value={payloadText} onChange={(event) => setPayloadText(event.target.value)} spellCheck={false} />
          </article>

          <DossierPanel activeCase={activeCase} result={result} />
        </section>

        <section className="grid three">
          <article className="panel case-list">
            <div className="panel-head">
              <span>Casos</span>
              <strong>{cases.length}</strong>
            </div>
            <div className="case-items">
              {cases.length === 0 && <p className="empty">Aún no hay casos persistidos.</p>}
              {cases.map((item) => (
                <button key={item.case_id} onClick={() => void loadCase(item.case_id)} type="button">
                  <span>{item.case_id}</span>
                  <strong>{item.case_status ?? 'sin estado'}</strong>
                </button>
              ))}
            </div>
          </article>

          <ApprovalPanel
            selectedCaseId={selectedCaseId}
            grammarReport={grammarReport}
            grammarExceptions={grammarExceptions}
            disabled={publishDisabled()}
            publishTitle={publishTitle()}
            onApprove={() => void approve('approve')}
            onPublish={handlePublishClick}
            onReject={() => void approve('reject')}
          />

          <article className="panel exports-panel" id="exports">
            <div className="panel-head">
              <span>Entregables</span>
              <strong>{files.length}</strong>
            </div>
            <div className="file-list">
              {files.length === 0 && <p className="empty">Sin archivos exportados todavía.</p>}
              {files.map((file) => (
                <div key={`${file.target}-${file.path}`}>
                  <span>{file.target}</span>
                  <p title={file.path}>{file.path}</p>
                  <strong>{file.size_bytes ?? 0} bytes</strong>
                </div>
              ))}
            </div>
          </article>
        </section>
      </section>
      )}

      {publishConfirmOpen && (
        <ConfirmModal
          grammarReport={grammarReport}
          onConfirm={confirmPublish}
          onCancel={() => setPublishConfirmOpen(false)}
        />
      )}
    </main>
  )
}

export default App
