import type { StandardStatus, StandardVersion } from '@/types/standard'

export interface StatusMeta {
  label: string
  badge: string
  dot: string
  panel: string
}

const STATUS_META: Record<StandardStatus, StatusMeta> = {
  ACTIVE: {
    label: '当前现行',
    badge: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    dot: 'bg-emerald-500 ring-emerald-100',
    panel: 'border-emerald-200',
  },
  UPCOMING: {
    label: '即将实施',
    badge: 'border-blue-200 bg-blue-50 text-blue-700',
    dot: 'bg-blue-500 ring-blue-100',
    panel: 'border-blue-200',
  },
  REPLACED: {
    label: '旧标准',
    badge: 'border-amber-200 bg-amber-50 text-amber-700',
    dot: 'bg-amber-500 ring-amber-100',
    panel: 'border-amber-200',
  },
  ABOLISHED: {
    label: '已废止',
    badge: 'border-red-200 bg-red-50 text-red-700',
    dot: 'bg-red-500 ring-red-100',
    panel: 'border-red-200',
  },
  UNKNOWN: {
    label: '状态未知',
    badge: 'border-border bg-muted text-muted-foreground',
    dot: 'bg-muted-foreground ring-muted',
    panel: 'border-border',
  },
}

export function statusMeta(status?: StandardStatus | null): StatusMeta {
  if (!status) {
    return STATUS_META.UNKNOWN
  }
  return STATUS_META[status] ?? STATUS_META.UNKNOWN
}

export function formatDate(value?: string | null): string {
  return value || '未提供'
}

export function formatVersionYear(version: StandardVersion): string {
  if (version.standardYear) {
    return `${version.standardYear} 年`
  }
  if (version.effectiveDate) {
    return `${version.effectiveDate.slice(0, 4)} 年`
  }
  if (version.publishDate) {
    return `${version.publishDate.slice(0, 4)} 年`
  }
  const match = version.standardNo.match(/(\d{4})$/)
  return match ? `${match[1]} 年` : '年份未知'
}
