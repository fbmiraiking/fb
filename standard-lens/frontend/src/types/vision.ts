import type { StandardStatus } from '@/types/standard'

export type RequirementType =
  | 'VISUAL'
  | 'LABEL'
  | 'DOCUMENT'
  | 'LAB_TEST'
  | 'MEASUREMENT'

export type RequirementCheckStatus =
  | 'OBSERVED'
  | 'PARTIAL'
  | 'NOT_OBSERVED'
  | 'NEEDS_DOCUMENT'
  | 'NOT_POSSIBLE'
  | 'CANNOT_VERIFY'

export interface VisionProduct {
  name: string
  categoryGuess: string
  confidence: number
}

export interface VisionAnalysis {
  product: VisionProduct
  materials: string[]
  usages: string[]
  visibleText: string[]
  visibleStandardNumbers: string[]
  productionDate: string | null
  manufacturer: string | null
}

export interface StandardMatchItem {
  id: number
  standardNo: string
  standardName: string
  status: StandardStatus
  statusLabel: string
  publishDate: string | null
  effectiveDate: string | null
  expiryDate: string | null
  relationType: string
  isHistorical: boolean
}

export interface DetectedStandardItem extends StandardMatchItem {
  replacedBy: StandardMatchItem[]
  latestCurrent: StandardMatchItem[]
  notice: string
}

export interface RelatedStandards {
  current: StandardMatchItem[]
  upcoming: StandardMatchItem[]
  historical: StandardMatchItem[]
  other: StandardMatchItem[]
}

export interface MatchedCategory {
  id: number
  name: string
  description: string | null
  parentId: number | null
  aliases: string[]
  score: number
  matchedTerms: string[]
}

export interface RequirementCheckItem {
  requirementId: number
  chapter: string
  requirementType: RequirementType
  requirementText: string
  verificationMethod: string
  status: RequirementCheckStatus
  statusLabel: string
  imageCheckable: boolean
  evidence: string[]
  message: string
}

export interface StandardVerification {
  standardId: number
  standardNo: string
  standardName: string
  status: StandardStatus
  statusLabel: string
  effectiveDate: string | null
  replacementStandards: StandardMatchItem[]
  latestCurrent: StandardMatchItem[]
  lifecycleNotice: string
  requirements: RequirementCheckItem[]
  observedCount: number
  partialCount: number
  notObservedCount: number
  externalCheckCount: number
  summary: string
}

export interface VisionMatchResponse {
  imageAnalysis: VisionAnalysis
  detectedStandards: DetectedStandardItem[]
  relatedStandards: RelatedStandards
  imageStored: boolean
  matchedCategories: MatchedCategory[]
  unmatchedVisibleStandardNumbers: string[]
  standardVerification: StandardVerification[]
  verificationNotice: string
}
