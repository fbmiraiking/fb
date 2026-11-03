import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { analyzeAndMatch } from '@/api/vision'
import type { AIConfig } from '@/types/ai'
import type { VisionMatchResponse } from '@/types/vision'

export type VisionVerifyState = 'idle' | 'analyzing' | 'done' | 'error'

export const useVisionVerifyStore = defineStore('visionVerify', () => {
  const file = ref<File | null>(null)
  const previewUrl = ref('')
  const state = ref<VisionVerifyState>('idle')
  const errorMessage = ref('')
  const result = ref<VisionMatchResponse | null>(null)

  const isAnalyzing = computed(() => state.value === 'analyzing')
  const hasResult = computed(() => result.value !== null)

  function releasePreview() {
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
    }
  }

  function setFile(next: File) {
    releasePreview()
    file.value = next
    previewUrl.value = URL.createObjectURL(next)
    result.value = null
    errorMessage.value = ''
    state.value = 'idle'
  }

  function clearFile() {
    releasePreview()
    file.value = null
    result.value = null
    errorMessage.value = ''
    state.value = 'idle'
  }

  function resetResult() {
    result.value = null
    errorMessage.value = ''
    state.value = 'idle'
  }

  async function analyze(config: AIConfig) {
    if (!file.value) {
      errorMessage.value = '请先选择一张商品图片'
      state.value = 'error'
      return
    }

    state.value = 'analyzing'
    errorMessage.value = ''
    result.value = null

    try {
      result.value = await analyzeAndMatch(file.value, config)
      state.value = 'done'
    } catch (caught) {
      state.value = 'error'
      errorMessage.value =
        caught instanceof ApiError ? caught.message : '图片核验失败，请稍后重试'
    }
  }

  function dispose() {
    releasePreview()
  }

  return {
    file,
    previewUrl,
    state,
    errorMessage,
    result,
    isAnalyzing,
    hasResult,
    setFile,
    clearFile,
    resetResult,
    analyze,
    dispose,
  }
})
