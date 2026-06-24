export type CaseRecord = {
  case_id: string
  case_status?: string
  approval_status?: string
  engagement_id?: string
  client?: { legal_name?: string; name?: string }
  domain?: string
  files?: Array<{ target: string; path: string; size_bytes?: number }>
  trace_id?: string
}

export type RunResult = {
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
