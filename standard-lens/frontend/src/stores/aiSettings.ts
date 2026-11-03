import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { testAIConnection } from '@/api/ai'
import {
  AI_STORAGE_KEY,
  getProviderOption,
  isAIProvider,
  isKnownDefaultBaseUrl,
} from '@/lib/ai'
import type { AIConfig, AIProvider, AIStorageMode, AITestConnectionResponse } from '@/types/ai'

export type AITestState = 'idle' | 'testing' | 'success' | 'error'

function defaultBaseUrl(provider: AIProvider): string {
  return getProviderOption(provider).defaultBaseUrl
}

function readStorage(mode: AIStorageMode): AIConfig | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    const storage = mode === 'session' ? window.sessionStorage : window.localStorage
    const raw = storage.getItem(AI_STORAGE_KEY)
    if (!raw) {
      return null
    }
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') {
      return null
    }
    const record = parsed as Record<string, unknown>
    if (typeof record.provider !== 'string' || !isAIProvider(record.provider)) {
      return null
    }
    if (typeof record.apiBaseUrl !== 'string') {
      return null
    }
    if (typeof record.apiKey !== 'string' || !record.apiKey.trim()) {
      return null
    }
    if (typeof record.model !== 'string' || !record.model.trim()) {
      return null
    }
    return {
      provider: record.provider,
      apiBaseUrl: record.apiBaseUrl,
      apiKey: record.apiKey,
      model: record.model,
    }
  } catch {
    return null
  }
}

export const useAISettingsStore = defineStore('aiSettings', () => {
  const provider = ref<AIProvider>('openai')
  const apiBaseUrl = ref(defaultBaseUrl('openai'))
  const apiKey = ref('')
  const model = ref('')
  const storageMode = ref<AIStorageMode>('session')

  const hasStoredConfig = ref(false)
  const loadedFrom = ref<AIStorageMode | null>(null)
  const formError = ref('')
  const savedMessage = ref('')

  const testState = ref<AITestState>('idle')
  const testResult = ref<AITestConnectionResponse | null>(null)
  const testMessage = ref('')

  const providerOption = computed(() => getProviderOption(provider.value))
  const isTesting = computed(() => testState.value === 'testing')
  const isConfigured = computed(
    () =>
      Boolean(apiKey.value.trim()) &&
      Boolean(model.value.trim()) &&
      (!providerOption.value.needsBaseUrl || Boolean(apiBaseUrl.value.trim())),
  )

  const sessionConfig = readStorage('session')
  const localConfig = readStorage('local')
  const initialConfig = sessionConfig ?? localConfig

  if (initialConfig) {
    provider.value = initialConfig.provider
    apiBaseUrl.value = initialConfig.apiBaseUrl
    apiKey.value = initialConfig.apiKey
    model.value = initialConfig.model
    storageMode.value = sessionConfig ? 'session' : 'local'
    loadedFrom.value = storageMode.value
    hasStoredConfig.value = true
  }

  function validate(): string | null {
    if (!isAIProvider(provider.value)) {
      return '请选择 AI Provider'
    }
    if (!apiKey.value.trim()) {
      return '请填写 API Key'
    }
    if (!model.value.trim()) {
      return '请填写模型名称'
    }

    const base = apiBaseUrl.value.trim()
    if (providerOption.value.needsBaseUrl && !base) {
      return 'OpenAI Compatible 必须填写 Base URL'
    }
    if (base) {
      try {
        const parsed = new URL(base)
        if (!['http:', 'https:'].includes(parsed.protocol)) {
          return 'Base URL 必须是 http(s) 地址'
        }
        if (parsed.username || parsed.password || parsed.search || parsed.hash) {
          return 'Base URL 不能包含用户名、密码、查询参数或片段'
        }
      } catch {
        return 'Base URL 格式不正确'
      }
    }

    return null
  }

  function currentConfig(): AIConfig {
    return {
      provider: provider.value,
      apiBaseUrl: apiBaseUrl.value.trim().replace(/\/+$/, ''),
      apiKey: apiKey.value.trim(),
      model: model.value.trim(),
    }
  }

  function clearFeedback() {
    formError.value = ''
    testState.value = 'idle'
    testResult.value = null
    testMessage.value = ''
    savedMessage.value = ''
  }

  function setProvider(nextProvider: AIProvider) {
    const currentBase = apiBaseUrl.value.trim()
    const replaceBase = !currentBase || isKnownDefaultBaseUrl(currentBase)
    provider.value = nextProvider
    if (replaceBase) {
      apiBaseUrl.value = defaultBaseUrl(nextProvider)
    }
  }

  function saveConfig(): boolean {
    const error = validate()
    formError.value = error ?? ''
    if (error) {
      return false
    }

    const config = currentConfig()
    try {
      const target =
        storageMode.value === 'session' ? window.sessionStorage : window.localStorage
      const other =
        storageMode.value === 'session' ? window.localStorage : window.sessionStorage
      target.setItem(AI_STORAGE_KEY, JSON.stringify(config))
      other.removeItem(AI_STORAGE_KEY)
    } catch {
      formError.value = '浏览器存储不可用，请检查隐私设置'
      return false
    }

    hasStoredConfig.value = true
    loadedFrom.value = storageMode.value
    savedMessage.value =
      storageMode.value === 'session'
        ? '已保存到当前标签页，关闭标签页后自动清除'
        : '已保存到当前设备，浏览器会保留'
    return true
  }

  function clearConfig() {
    let storageFailed = false
    try {
      window.sessionStorage.removeItem(AI_STORAGE_KEY)
      window.localStorage.removeItem(AI_STORAGE_KEY)
    } catch {
      storageFailed = true
    }

    provider.value = 'openai'
    apiBaseUrl.value = defaultBaseUrl('openai')
    apiKey.value = ''
    model.value = ''
    storageMode.value = 'session'
    hasStoredConfig.value = false
    loadedFrom.value = null
    testState.value = 'idle'
    testResult.value = null
    testMessage.value = ''
    formError.value = storageFailed ? '浏览器存储不可用，请检查隐私设置' : ''
    savedMessage.value = storageFailed ? '' : '浏览器中的 AI 配置已清除'
  }

  async function testConnection() {
    const error = validate()
    formError.value = error ?? ''
    if (error) {
      return
    }

    testState.value = 'testing'
    testResult.value = null
    testMessage.value = ''
    savedMessage.value = ''

    try {
      const result = await testAIConnection(currentConfig())
      testResult.value = result
      testState.value = result.ok ? 'success' : 'error'
      testMessage.value = result.message
    } catch (caught) {
      testState.value = 'error'
      testMessage.value =
        caught instanceof ApiError ? caught.message : '测试连接失败，请稍后重试'
    }
  }

  return {
    provider,
    apiBaseUrl,
    apiKey,
    model,
    storageMode,
    hasStoredConfig,
    loadedFrom,
    formError,
    savedMessage,
    testState,
    testResult,
    testMessage,
    providerOption,
    isTesting,
    isConfigured,
    validate,
    clearFeedback,
    setProvider,
    saveConfig,
    clearConfig,
    testConnection,
  }
})
