export type AIProvider = 'openai' | 'gemini' | 'anthropic' | 'openai_compatible'

export type AIStorageMode = 'session' | 'local'

export interface AIConfig {
  provider: AIProvider
  apiBaseUrl: string
  apiKey: string
  model: string
}

export interface AITestConnectionResponse {
  ok: boolean
  provider: AIProvider
  model: string
  message: string
  latencyMs: number
}
