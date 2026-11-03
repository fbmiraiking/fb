import { request } from '@/api/client'
import type { AIConfig } from '@/types/ai'
import type { VisionMatchResponse } from '@/types/vision'

export function analyzeAndMatch(
  image: File,
  config: AIConfig,
): Promise<VisionMatchResponse> {
  const form = new FormData()
  form.append('image', image)
  form.append('provider', config.provider)
  if (config.apiBaseUrl.trim()) {
    form.append('apiBaseUrl', config.apiBaseUrl.trim())
  }
  form.append('apiKey', config.apiKey)
  form.append('model', config.model.trim())

  return request<VisionMatchResponse>(
    '/api/v1/vision/analyze-and-match',
    {
      method: 'POST',
      body: form,
    },
    120_000,
  )
}
