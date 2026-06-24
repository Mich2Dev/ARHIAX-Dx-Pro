import { useState } from 'react'
import type { RunResult } from '../lib/types'

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

export function useDiagnosticRun() {
  const [payloadText, setPayloadText] = useState(JSON.stringify(samplePayload, null, 2))
  const [result, setResult] = useState<RunResult | null>(null)

  function restoreSample() {
    setPayloadText(JSON.stringify(samplePayload, null, 2))
  }

  return { payloadText, setPayloadText, result, setResult, restoreSample }
}
