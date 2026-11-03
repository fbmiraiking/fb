import type { AIProvider, AIStorageMode } from '@/types/ai'

export interface AIProviderOption {
  value: AIProvider
  label: string
  defaultBaseUrl: string
  modelPlaceholder: string
  needsBaseUrl: boolean
  hint: string
}

export const AI_STORAGE_KEY = 'standard-lens.ai-config.v1'

export const AI_PROVIDER_OPTIONS: AIProviderOption[] = [
  {
    value: 'openai',
    label: 'OpenAI',
    defaultBaseUrl: 'https://api.openai.com/v1',
    modelPlaceholder: '例如 gpt-4o-mini',
    needsBaseUrl: false,
    hint: '官方接口，Base URL 留空即可使用默认地址。',
  },
  {
    value: 'gemini',
    label: 'Gemini',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    modelPlaceholder: '例如 gemini-2.0-flash',
    needsBaseUrl: false,
    hint: '使用 Google Generative Language API。',
  },
  {
    value: 'anthropic',
    label: 'Anthropic',
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    modelPlaceholder: '例如 claude-sonnet-5-5',
    needsBaseUrl: false,
    hint: '使用 Anthropic Messages API，也支持兼容网关的根路径 Base URL / Bearer Token。',
  },
  {
    value: 'openai_compatible',
    label: 'OpenAI Compatible',
    defaultBaseUrl: '',
    modelPlaceholder: '例如 qwen-vl-plus / llava',
    needsBaseUrl: true,
    hint: '填写完整的 /v1 兼容地址，例如 http://localhost:11434/v1。',
  },
]

export function getProviderOption(provider: AIProvider): AIProviderOption {
  return (
    AI_PROVIDER_OPTIONS.find((option) => option.value === provider) ??
    AI_PROVIDER_OPTIONS[0]
  )
}

export function isAIProvider(value: string): value is AIProvider {
  return AI_PROVIDER_OPTIONS.some((option) => option.value === value)
}

export function isAIStorageMode(value: string): value is AIStorageMode {
  return value === 'session' || value === 'local'
}

export function isKnownDefaultBaseUrl(value: string): boolean {
  return AI_PROVIDER_OPTIONS.some(
    (option) => option.defaultBaseUrl && option.defaultBaseUrl === value,
  )
}
