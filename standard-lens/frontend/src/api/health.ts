import { request } from '@/api/client'
import type { HealthResponse } from '@/types/api'

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health')
}
