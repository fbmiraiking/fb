import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { fetchHealth } from '@/api/health'
import type { HealthResponse } from '@/types/api'

export type HealthState = 'idle' | 'loading' | 'ok' | 'degraded' | 'error'

export const useHealthStore = defineStore('health', () => {
  const state = ref<HealthState>('idle')
  const data = ref<HealthResponse | null>(null)
  const errorMessage = ref('')
  const latencyMs = ref<number | null>(null)
  const checkedAt = ref<Date | null>(null)

  const isLoading = computed(() => state.value === 'loading')

  async function check() {
    if (state.value === 'loading') {
      return
    }

    state.value = 'loading'
    errorMessage.value = ''
    const startedAt = performance.now()

    try {
      const response = await fetchHealth()
      data.value = response
      latencyMs.value = Math.round(performance.now() - startedAt)
      state.value = response.status === 'ok' ? 'ok' : 'degraded'
    } catch (error) {
      data.value = null
      latencyMs.value = null
      state.value = 'error'
      errorMessage.value = error instanceof ApiError ? error.message : '未知错误，请查看浏览器控制台'
    } finally {
      checkedAt.value = new Date()
    }
  }

  return {
    state,
    data,
    errorMessage,
    latencyMs,
    checkedAt,
    isLoading,
    check,
  }
})
