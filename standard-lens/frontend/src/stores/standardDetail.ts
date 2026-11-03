import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { fetchStandard, fetchStandardVersions } from '@/api/standards'
import type { StandardDetail, StandardVersion } from '@/types/standard'

export type StandardDetailState = 'idle' | 'loading' | 'ready' | 'not-found' | 'error'

export const useStandardDetailStore = defineStore('standardDetail', () => {
  const state = ref<StandardDetailState>('idle')
  const standard = ref<StandardDetail | null>(null)
  const versions = ref<StandardVersion[]>([])
  const errorMessage = ref('')
  const versionsError = ref('')
  let loadToken = 0

  const isLoading = computed(() => state.value === 'loading')
  const isNotFound = computed(() => state.value === 'not-found')

  async function load(id: number) {
    const token = ++loadToken
    state.value = 'loading'
    standard.value = null
    versions.value = []
    errorMessage.value = ''
    versionsError.value = ''

    const [detailResult, versionsResult] = await Promise.allSettled([
      fetchStandard(id),
      fetchStandardVersions(id),
    ])

    if (token !== loadToken) {
      return
    }

    if (detailResult.status === 'rejected') {
      if (detailResult.reason instanceof ApiError && detailResult.reason.status === 404) {
        state.value = 'not-found'
        errorMessage.value = '未找到该标准，请检查链接是否正确。'
      } else {
        state.value = 'error'
        errorMessage.value =
          detailResult.reason instanceof Error ? detailResult.reason.message : '加载标准详情失败'
      }
      return
    }

    standard.value = detailResult.value

    if (versionsResult.status === 'fulfilled') {
      versions.value = versionsResult.value
    } else {
      versionsError.value =
        versionsResult.reason instanceof Error ? versionsResult.reason.message : '版本链加载失败'
    }

    state.value = 'ready'
  }

  function reset() {
    loadToken += 1
    state.value = 'idle'
    standard.value = null
    versions.value = []
    errorMessage.value = ''
    versionsError.value = ''
  }

  return {
    state,
    standard,
    versions,
    errorMessage,
    versionsError,
    isLoading,
    isNotFound,
    load,
    reset,
  }
})
