import { useEffect, useState } from 'react'
import './App.css'

type CaseRecord = {
  case_id: string
  case_status?: string
  approval_status?: string
  engagement_id?: string
  client?: { legal_name?: string; name?: string }
  domain?: string
  files?: Array<{ target: string; path: string; size_bytes?: number }>
  trace_id?: string
}

type RunResult = {
  artifact?: {
    case_id?: string
    case_status?: string
    approval_status?: string
    files?: Array<{ target: string; path: string; size_bytes?: number }>
    stage_outcomes?: Record<string, { outcome?: string; artifact_type?: string }>
  }
  outcome?: string
  trace_id?: string
  reason?: string
}

const API_BASE = import.meta.env.VITE_DXPRO_API_URL ?? 'http://127.0.0.1:8000'

const samplePayload = {
  consent: { action: 'ingest_to_llm', consents: { T1: true, T3: true } },
  engagement_id: 'eng-dxpro-demo-001',
  client: { legal_name: 'Agencia Demo S.A.S.' },
  domain: 'customs agency innovation',
  roles: ['executive', 'operations', 'technology'],
  dimensions: ['strategy', 'process', 'technology'],
  responses: [
    { role: 'executive', dimension: 'strategy', item_id: 'strategy-1', score: 4 },
    { role: 'operations', dimension: 'strategy', item_id: 'strategy-1', score: 2 },
    { role: 'technology', dimension: 'strategy', item_id: 'strategy-1', score: 3 },
    { role: 'executive', dimension: 'process', item_id: 'process-1', score: 3 },
    { role: 'operations', dimension: 'process', item_id: 'process-1', score: 2 },
    { role: 'technology', dimension: 'process', item_id: 'process-1', score: 4 },
    { role: 'executive', dimension: 'technology', item_id: 'technology-1', score: 3 },
    { role: 'operations', dimension: 'technology', item_id: 'technology-1', score: 2 },
    { role: 'technology', dimension: 'technology', item_id: 'technology-1', score: 4 },
  ],
  response_matrix: [
    [4, 3, 3],
    [2, 2, 2],
    [3, 4, 4],
  ],
  diagnostic_hypotheses: [
    { id: 'DH1', statement: 'Technology traceability is a bottleneck.', prior: 0.55 },
  ],
  evidence_signals: [{ id: 'sig-1', hypothesis_ids: ['DH1'], likelihood_ratio: 1.6 }],
  hypothesis_pack: {
    hypothesis_pack_version: '1.0',
    engagement_id: 'eng-dxpro-demo-001',
    domain: 'customs agency innovation',
    hypotheses: [{ id: 'H1', statement: 'Reduce manual handoffs.' }],
  },
  grey_sources: [{ id: 'grey-1', title: 'Benchmark', content: 'Manual handoffs add delay.' }],
  bpmn_model: {
    nodes: [
      { id: 'start', type: 'start_event', name: 'Inicio' },
      { id: 't1', type: 'task', name: 'Validar pedido' },
      { id: 'end', type: 'end_event', name: 'Fin' },
    ],
    edges: [
      { source: 'start', target: 't1' },
      { source: 't1', target: 'end' },
    ],
  },
  targets: ['markdown', 'docx', 'pdf'],
}

function App() {
  const [cases, setCases] = useState<CaseRecord[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [payloadText, setPayloadText] = useState(JSON.stringify(samplePayload, null, 2))
  const [status, setStatus] = useState('ready')
  const [error, setError] = useState('')

  useEffect(() => {
    void loadCases()
  }, [])

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      ...init,
    })
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`)
    }
    return response.json() as Promise<T>
  }

  async function loadCases() {
    setError('')
    try {
      const body = await request<{ cases: CaseRecord[] }>('/v1/cases')
      setCases(body.cases ?? [])
    } catch (err) {
      setError(`No se pudo conectar con DxPro Runtime en ${API_BASE}.`)
    }
  }

  async function runCase() {
    setStatus('running')
    setError('')
    try {
      const payload = JSON.parse(payloadText)
      const body = await request<RunResult>('/v1/agents/cases/run', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setResult(body)
      const caseId = body.artifact?.case_id ?? ''
      setSelectedCaseId(caseId)
      await loadCases()
      if (caseId) {
        await loadCase(caseId)
      }
      setStatus('ready')
    } catch (err) {
      setStatus('ready')
      setError(err instanceof SyntaxError ? 'El JSON del caso no es válido.' : 'No se pudo ejecutar el caso.')
    }
  }

  async function loadCase(caseId = selectedCaseId) {
    if (!caseId) return
    setError('')
    try {
      const body = await request<CaseRecord>(`/v1/cases/${caseId}`)
      setSelectedCase(body)
      setSelectedCaseId(caseId)
    } catch {
      setError('No se pudo cargar el caso seleccionado.')
    }
  }

  async function approve(action: 'approve' | 'publish' | 'reject') {
    if (!selectedCaseId) return
    setStatus(action)
    setError('')
    try {
      await request('/v1/agents/cases/approval', {
        method: 'POST',
        body: JSON.stringify({
          consent: samplePayload.consent,
          case_id: selectedCaseId,
          action,
          reviewer: { name: 'Consultor Lider', role: 'engagement_manager' },
        }),
      })
      await loadCases()
      await loadCase(selectedCaseId)
      setStatus('ready')
    } catch {
      setStatus('ready')
      setError('La transición de aprobación no fue aceptada por el runtime.')
    }
  }

  const activeCase = selectedCase ?? cases[0]
  const files = activeCase?.files ?? result?.artifact?.files ?? []
  const stageOutcomes = result?.artifact?.stage_outcomes ?? {}

  return (
    <main className="dx-shell">
      <aside className="rail" aria-label="Navegación principal">
        <a className="brand" href="#workspace" aria-label="ARHIAX DxPro">
          <img src="/logo-sinergia.png" alt="Sinergia Consulting Group" />
          <span>
            <strong>ARHIAX</strong>
            <em>DxPro</em>
          </span>
        </a>
        <nav>
          <a href="#case-runner">Caso</a>
          <a href="#evidence">Evidencia</a>
          <a href="#approval">Aprobación</a>
          <a href="#exports">Entregables</a>
        </nav>
        <div className="rail-status">
          <span>Runtime</span>
          <strong>{status === 'ready' ? 'operativo' : status}</strong>
        </div>
      </aside>

      <section className="workspace" id="workspace">
        <header className="topbar">
          <div>
            <p className="section-code">§ 05 · consola operativa</p>
            <h1>ARHIAX DxPro</h1>
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
              DxPro toma el caso, corre la fusión diagnóstica, genera reporte, renderiza, exporta y
              deja el expediente en revisión.
            </p>
          </div>
          <div className="actions">
            <button className="primary-action" onClick={() => void runCase()} disabled={status !== 'ready'} type="button">
              Ejecutar caso
            </button>
            <button className="secondary-action" onClick={() => setPayloadText(JSON.stringify(samplePayload, null, 2))} type="button">
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

          <article className="panel dossier">
            <div className="panel-head">
              <span>Expediente</span>
              <strong>{activeCase?.case_id ?? result?.artifact?.case_id ?? 'sin caso'}</strong>
            </div>
            <dl className="facts">
              <div>
                <dt>Cliente</dt>
                <dd>{activeCase?.client?.legal_name ?? activeCase?.client?.name ?? 'Agencia Demo S.A.S.'}</dd>
              </div>
              <div>
                <dt>Estado</dt>
                <dd>{activeCase?.case_status ?? result?.artifact?.case_status ?? 'pendiente'}</dd>
              </div>
              <div>
                <dt>Aprobación</dt>
                <dd>{activeCase?.approval_status ?? result?.artifact?.approval_status ?? 'draft'}</dd>
              </div>
              <div>
                <dt>Trace</dt>
                <dd>{activeCase?.trace_id ?? result?.trace_id ?? 'no generado'}</dd>
              </div>
            </dl>

            <div className="stage-list" id="evidence">
              {['fusion', 'report', 'render', 'export'].map((stage) => (
                <div key={stage}>
                  <span>{stage}</span>
                  <strong>{stageOutcomes[stage]?.outcome ?? 'espera'}</strong>
                </div>
              ))}
            </div>
          </article>
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

          <article className="panel approval-panel" id="approval">
            <div className="panel-head">
              <span>HIL</span>
              <strong>control humano</strong>
            </div>
            <div className="approval-actions">
              <button onClick={() => void approve('approve')} disabled={!selectedCaseId} type="button">
                Aprobar
              </button>
              <button onClick={() => void approve('publish')} disabled={!selectedCaseId} type="button">
                Publicar
              </button>
              <button onClick={() => void approve('reject')} disabled={!selectedCaseId} type="button">
                Rechazar
              </button>
            </div>
          </article>

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
    </main>
  )
}

export default App
