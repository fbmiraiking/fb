export interface DatabaseHealth {
  status: 'ok' | 'down'
  latency_ms: number | null
  detail: string | null
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  service: string
  version: string
  environment: string
  database: DatabaseHealth
  checked_at: string
  latency_ms: number
}
