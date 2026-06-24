import type { GrammarReport } from '../lib/canonicalGrammar'

type Props = {
  grammarReport: GrammarReport | null
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmModal({ grammarReport, onConfirm, onCancel }: Props) {
  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Confirmar publicación</h3>
        <p>
          {grammarReport
            ? 'Este expediente tiene hallazgos canónicos que requieren confirmación. ¿Está seguro de publicar?'
            : 'No se ha ejecutado una revisión canónica de este expediente. ¿Desea publicar de todas formas?'}
        </p>
        <div className="modal-actions">
          <button className="primary-action" onClick={onConfirm} type="button">
            Sí, publicar
          </button>
          <button className="secondary-action" onClick={onCancel} type="button">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
