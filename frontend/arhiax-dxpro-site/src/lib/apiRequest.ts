const API_BASE = import.meta.env.VITE_DXPRO_API_URL ?? 'http://127.0.0.1:8310'

export async function apiRequest<T>(path: string, init?: RequestInit & { signal?: AbortSignal }): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (init?.headers) {
    Object.assign(headers, init.headers)
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}
