import type { CaseRecord, RunResult } from '../lib/types'

type Props = {
  activeCase: CaseRecord | null
  result: RunResult | null
}

export default function DossierPanel({ activeCase, result }: Props) {
  const stageOutcomes = result?.artifact?.stage_outcomes ?? {}

  return (
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
  )
}
