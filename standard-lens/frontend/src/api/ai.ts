import { request } from '@/api/client'
import type { AIConfig, AITestConnectionResponse } from '@/types/ai'

export function testAIConnection(config: AIConfig): Promise<AITestConnectionResponse> {
  return request<AITestConnectionResponse>(
    '/api/v1/ai/test-connection',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider: config.provider,
        apiBaseUrl: config.apiBaseUrl.trim() || null,
        apiKey: config.apiKey,
        model: config.model.trim(),
      }),
    },
    30_000,
  )
}
