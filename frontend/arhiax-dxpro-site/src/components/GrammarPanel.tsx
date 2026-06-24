import CanonicalGrammarPanel from './CanonicalGrammarPanel'
import type { GrammarReport, GrammarException } from '../lib/canonicalGrammar'

type Props = {
  caseText: string
  hasCase: boolean
  onReport: (r: GrammarReport | null) => void
  onExceptionsChange?: (exceptions: GrammarException[]) => void
}

export default function GrammarPanel({ caseText, hasCase, onReport }: Props) {
  return (
    <section className="workspace" id="grammar">
      <header className="topbar">
        <div>
          <p className="section-code">§ 06 · revisión canónica</p>
          <h1>Gramática</h1>
        </div>
      </header>
      <CanonicalGrammarPanel onReport={onReport} caseText={caseText} hasCase={hasCase} />
    </section>
  )
}
