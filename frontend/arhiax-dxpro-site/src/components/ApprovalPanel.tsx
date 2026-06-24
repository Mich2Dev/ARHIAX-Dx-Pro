import { canPublish, type GrammarReport, type GrammarException } from '../lib/canonicalGrammar'

type Props = {
  selectedCaseId: string
  grammarReport: GrammarReport | null
  grammarExceptions: GrammarException[]
  disabled: boolean
  publishTitle: string
  onApprove: () => void
  onPublish: () => void
  onReject: () => void
}

export default function ApprovalPanel({
  selectedCaseId,
  grammarReport,
  grammarExceptions,
  disabled,
  publishTitle,
  onApprove,
  onPublish,
  onReject,
}: Props) {
  const publishDecision = grammarReport
    ? canPublish(grammarReport, grammarExceptions.length > 0 ? grammarExceptions : undefined)
    : null

  return (
    <article className="panel approval-panel" id="approval">
      <div className="panel-head">
        <span>HIL</span>
        <strong>control humano</strong>
      </div>
      <div className="canonical-status">
        {!grammarReport && <span className="status-tag status-unreviewed">Sin revisión canónica</span>}
        {grammarReport && publishDecision?.allowed && !publishDecision.confirmRequired && (
          <span className="status-tag status-clean">Apto para publicación</span>
        )}
        {grammarReport && publishDecision?.allowed && publishDecision.confirmRequired && (
          <span className="status-tag status-warn">Hallazgos mayores</span>
        )}
        {grammarReport && publishDecision && !publishDecision.allowed && (
          <span className="status-tag status-blocked">Bloqueado por hallazgos críticos</span>
        )}
        {grammarReport && grammarExceptions.length > 0 && (
          <span className="status-tag status-excepted">{grammarExceptions.length} excepción(es) registrada(s)</span>
        )}
      </div>
      <div className="approval-actions">
        <button onClick={onApprove} disabled={!selectedCaseId} type="button">
          Aprobar
        </button>
        <button
          onClick={onPublish}
          disabled={disabled}
          title={publishTitle}
          type="button"
        >
          Publicar
        </button>
        <button onClick={onReject} disabled={!selectedCaseId} type="button">
          Rechazar
        </button>
      </div>
    </article>
  )
}
