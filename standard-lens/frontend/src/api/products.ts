import { request } from '@/api/client'
import type { ProductSearchResponse, ProductStandardsResponse } from '@/types/product'

export function searchProducts(
  query: string,
  limit = 20,
  offset = 0,
): Promise<ProductSearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  })
  return request<ProductSearchResponse>(`/api/v1/products/search?${params.toString()}`)
}

export function fetchProductStandards(id: number): Promise<ProductStandardsResponse> {
  return request<ProductStandardsResponse>(`/api/v1/products/${id}/standards`)
}
