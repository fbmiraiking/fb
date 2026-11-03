import type { StandardStatus } from '@/types/standard'

export type ProductRelationType =
  | 'DIRECT_APPLICABLE'
  | 'MATERIAL'
  | 'SAFETY'
  | 'LABELING'
  | 'TEST_METHOD'
  | 'PACKAGING'
  | 'GENERAL'
  | 'POSSIBLE'

export type ReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export type ProductGroupKey = 'current' | 'upcoming' | 'historical' | 'related'

export interface ProductSummary {
  id: number
  name: string
  description: string | null
  parentId: number | null
  aliases: string[]
}

export interface ProductSearchResponse {
  query: string
  total: number
  limit: number
  offset: number
  items: ProductSummary[]
}

export interface ProductStandard {
  id: number
  standardNo: string
  standardName: string
  status: StandardStatus
  effectiveDate: string | null
  expiryDate: string | null
  relationType: ProductRelationType
  reviewStatus: ReviewStatus
}

export interface ProductStandardsResponse {
  product: ProductSummary
  current: ProductStandard[]
  upcoming: ProductStandard[]
  historical: ProductStandard[]
  related: ProductStandard[]
}
