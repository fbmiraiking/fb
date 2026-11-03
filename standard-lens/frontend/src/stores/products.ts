import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { fetchProductStandards, searchProducts } from '@/api/products'
import type {
  ProductStandardsResponse,
  ProductSummary,
} from '@/types/product'

export type ProductLoadState = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

export const useProductsStore = defineStore('products', () => {
  const query = ref('')
  const searchState = ref<ProductLoadState>('idle')
  const results = ref<ProductSummary[]>([])
  const total = ref(0)
  const searchError = ref('')

  const selectedId = ref<number | null>(null)
  const selected = ref<ProductSummary | null>(null)
  const groups = ref<ProductStandardsResponse | null>(null)
  const standardsState = ref<ProductLoadState>('idle')
  const standardsError = ref('')

  let searchToken = 0
  let standardsToken = 0

  const isSearching = computed(() => searchState.value === 'loading')
  const isLoadingStandards = computed(() => standardsState.value === 'loading')

  function clearSelection() {
    standardsToken += 1
    selectedId.value = null
    selected.value = null
    groups.value = null
    standardsState.value = 'idle'
    standardsError.value = ''
  }

  function clearResults() {
    searchToken += 1
    results.value = []
    total.value = 0
    searchState.value = 'idle'
    searchError.value = ''
  }

  async function search(rawQuery: string) {
    const trimmed = rawQuery.trim()
    if (!trimmed) {
      clearResults()
      clearSelection()
      return
    }

    const token = ++searchToken
    searchState.value = 'loading'
    searchError.value = ''
    results.value = []
    total.value = 0
    clearSelection()

    try {
      const response = await searchProducts(trimmed)
      if (token !== searchToken) {
        return
      }
      results.value = response.items
      total.value = response.total
      searchState.value = response.items.length > 0 ? 'ready' : 'empty'

      if (response.items.length > 0) {
        await select(response.items[0])
      }
    } catch (error) {
      if (token !== searchToken) {
        return
      }
      searchState.value = 'error'
      searchError.value =
        error instanceof ApiError ? error.message : '搜索失败，请稍后重试'
    }
  }

  async function select(product: ProductSummary) {
    const token = ++standardsToken
    selectedId.value = product.id
    selected.value = product
    groups.value = null
    standardsState.value = 'loading'
    standardsError.value = ''

    try {
      const response = await fetchProductStandards(product.id)
      if (token !== standardsToken) {
        return
      }
      selected.value = response.product
      groups.value = response
      standardsState.value = 'ready'
    } catch (error) {
      if (token !== standardsToken) {
        return
      }
      standardsState.value = 'error'
      if (error instanceof ApiError) {
        standardsError.value =
          error.status === 404 ? '商品分类不存在' : error.message
      } else {
        standardsError.value = '标准加载失败，请稍后重试'
      }
    }
  }

  async function retryStandards() {
    if (selected.value) {
      await select(selected.value)
    }
  }

  function reset() {
    query.value = ''
    clearResults()
    clearSelection()
  }

  return {
    query,
    searchState,
    results,
    total,
    searchError,
    selectedId,
    selected,
    groups,
    standardsState,
    standardsError,
    isSearching,
    isLoadingStandards,
    search,
    select,
    retryStandards,
    reset,
  }
})
