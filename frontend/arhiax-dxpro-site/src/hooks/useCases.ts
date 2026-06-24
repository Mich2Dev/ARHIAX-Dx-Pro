import { useEffect, useState } from 'react'
import type { CaseRecord } from '../lib/types'
import { apiRequest } from '../lib/apiRequest'

export function useCases() {
  const [cases, setCases] = useState<CaseRecord[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null)
  const [error, setError] = useState('')

  async function loadCases() {
    setError('')
    try {
      const body = await apiRequest<{ cases: CaseRecord[] }>('/v1/cases')
      setCases(body.cases ?? [])
    } catch {
      setError('No se pudo conectar con Dx Pro Runtime.')
    }
  }

  async function loadCase(caseId = selectedCaseId) {
    if (!caseId) return
    setError('')
    try {
      const body = await apiRequest<CaseRecord>(`/v1/cases/${caseId}`)
      setSelectedCase(body)
      setSelectedCaseId(caseId)
    } catch {
      setError('No se pudo cargar el caso seleccionado.')
    }
  }

  useEffect(() => {
    const abort = new AbortController()
    apiRequest<{ cases: CaseRecord[] }>('/v1/cases', { signal: abort.signal })
      .then((body) => { setCases(body.cases ?? []) })
      .catch(() => {})
    return () => { abort.abort() }
  }, [])

  return { cases, selectedCaseId, selectedCase, error, loadCases, loadCase, setSelectedCaseId, setError }
}
