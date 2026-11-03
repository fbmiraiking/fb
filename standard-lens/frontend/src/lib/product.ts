import type {
  ProductGroupKey,
  ProductRelationType,
  ReviewStatus,
} from '@/types/product'

interface RelationTypeMeta {
  label: string
  className: string
}

export const RELATION_TYPE_META: Record<ProductRelationType, RelationTypeMeta> = {
  DIRECT_APPLICABLE: {
    label: '直接适用',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  },
  SAFETY: {
    label: '安全',
    className: 'border-red-200 bg-red-50 text-red-700',
  },
  MATERIAL: {
    label: '材料',
    className: 'border-amber-200 bg-amber-50 text-amber-700',
  },
  LABELING: {
    label: '标签标识',
    className: 'border-blue-200 bg-blue-50 text-blue-700',
  },
  TEST_METHOD: {
    label: '检测方法',
    className: 'border-violet-200 bg-violet-50 text-violet-700',
  },
  PACKAGING: {
    label: '包装',
    className: 'border-cyan-200 bg-cyan-50 text-cyan-700',
  },
  GENERAL: {
    label: '通用',
    className: 'border-slate-200 bg-slate-50 text-slate-700',
  },
  POSSIBLE: {
    label: '可能相关',
    className: 'border-border bg-muted text-muted-foreground',
  },
}

export interface ProductGroupMeta {
  title: string
  description: string
  dot: string
  panel: string
}

export const PRODUCT_GROUP_META: Record<ProductGroupKey, ProductGroupMeta> = {
  current: {
    title: '当前现行',
    description: '当前有效、可直接参考的标准',
    dot: 'bg-emerald-500',
    panel: 'border-emerald-200',
  },
  upcoming: {
    title: '即将实施',
    description: '已发布、尚未生效的标准',
    dot: 'bg-blue-500',
    panel: 'border-blue-200',
  },
  historical: {
    title: '历史版本',
    description: '已被替代或废止的标准',
    dot: 'bg-amber-500',
    panel: 'border-amber-200',
  },
  related: {
    title: '相关标准',
    description: '可能相关或状态未知的标准',
    dot: 'bg-slate-400',
    panel: 'border-slate-200',
  },
}

export const PRODUCT_GROUP_KEYS: ProductGroupKey[] = [
  'current',
  'upcoming',
  'historical',
  'related',
]

export const REVIEW_STATUS_LABEL: Record<ReviewStatus, string | null> = {
  PENDING: '待审核',
  APPROVED: null,
  REJECTED: '已驳回',
}
