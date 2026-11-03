export type StandardStatus = 'UPCOMING' | 'ACTIVE' | 'REPLACED' | 'ABOLISHED' | 'UNKNOWN'

export interface StandardDetail {
  id: number
  standard_no: string
  normalized_no: string
  standard_name: string
  standard_type: string | null
  status: StandardStatus
  publish_date: string | null
  effective_date: string | null
  expiry_date: string | null
  standard_year: number | null
  scope: string | null
  source: string | null
  source_url: string | null
  created_at: string
  updated_at: string
}

export interface StandardVersion {
  id: number
  standardNo: string
  standardName: string
  status: StandardStatus
  publishDate: string | null
  effectiveDate: string | null
  expiryDate: string | null
  standardYear: number | null
  isHistorical: boolean
  isCurrent: boolean
  isUpcoming: boolean
}
