import { request } from '@/api/client'
import type { StandardDetail, StandardVersion } from '@/types/standard'

export function fetchStandard(id: number): Promise<StandardDetail> {
  return request<StandardDetail>(`/api/v1/standards/${id}`)
}

export function fetchStandardVersions(id: number): Promise<StandardVersion[]> {
  return request<StandardVersion[]>(`/api/v1/standards/${id}/versions`)
}
