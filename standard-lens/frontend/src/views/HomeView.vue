<script setup lang="ts">
import { computed, onMounted, type Component } from 'vue'
import { RouterLink } from 'vue-router'
import {
  AlertTriangle,
  Camera,
  CircleCheck,
  CircleDashed,
  CircleX,
  Database,
  LoaderCircle,
  RefreshCw,
  ScanSearch,
  Search,
  Sparkles,
} from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealthStore } from '@/stores/health'

const store = useHealthStore()

interface StatusPresentation {
  label: string
  title: string
  hint: string
  panel: string
  iconColor: string
  badge: string
  icon: Component
}

const statusPresentation = computed<StatusPresentation>(() => {
  switch (store.state) {
    case 'ok':
      return {
        label: '正常',
        title: '服务正常',
        hint: '前端、后端 API 与 MySQL 数据库均已连通。',
        panel: 'border-emerald-200 bg-emerald-50',
        iconColor: 'text-emerald-600',
        badge: 'border-emerald-200 bg-emerald-100 text-emerald-700',
        icon: CircleCheck,
      }
    case 'degraded':
      return {
        label: '降级',
        title: '服务已启动，数据库未连接',
        hint:
          store.data?.database.detail ||
          'API 可访问，但 MySQL 健康检查失败，请检查 backend/.env 中的数据库配置。',
        panel: 'border-amber-200 bg-amber-50',
        iconColor: 'text-amber-600',
        badge: 'border-amber-200 bg-amber-100 text-amber-700',
        icon: AlertTriangle,
      }
    case 'error':
      return {
        label: '离线',
        title: '无法连接后端服务',
        hint: `${store.errorMessage}。请确认后端已在 http://127.0.0.1:8000 启动。`,
        panel: 'border-red-200 bg-red-50',
        iconColor: 'text-red-600',
        badge: 'border-red-200 bg-red-100 text-red-700',
        icon: CircleX,
      }
    case 'loading':
      return {
        label: '检测中',
        title: '正在检测服务状态…',
        hint: '正在请求 /api/health，请稍候。',
        panel: 'border-blue-200 bg-blue-50',
        iconColor: 'animate-spin text-blue-600',
        badge: 'border-blue-200 bg-blue-100 text-blue-700',
        icon: LoaderCircle,
      }
    default:
      return {
        label: '待检测',
        title: '尚未检测',
        hint: '点击右上角刷新按钮发起健康检查。',
        panel: 'border-border bg-muted/40',
        iconColor: 'text-muted-foreground',
        badge: 'border-border bg-muted text-muted-foreground',
        icon: CircleDashed,
      }
  }
})

const databaseText = computed(() => {
  if (!store.data) {
    return '未知'
  }
  return store.data.database.status === 'ok' ? '已连接' : '未连接'
})

const lastCheckedText = computed(() => {
  if (!store.checkedAt) {
    return '—'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(store.checkedAt)
})

const year = new Date().getFullYear()

const roadmap = [
  {
    title: '标准数据同步',
    description: '管理员全量初始化 + 每日增量同步，带限速、重试与同步日志。',
    badge: '已接入',
    ready: true,
    icon: Database,
  },
  {
    title: '商品分类查询',
    description: '按商品名称或别名搜索，查看现行、即将实施、历史与相关标准。',
    badge: '已接入',
    ready: true,
    icon: Search,
  },
  {
    title: 'AI Provider 配置',
    description: '用户自备 Key，支持多家 Provider、自定义 Base URL、本地存储与连接测试。',
    badge: '已接入',
    ready: true,
    icon: Sparkles,
  },
  {
    title: 'AI 图片识别',
    description: '识别接口已接入；前端上传与结果展示页面待开发。',
    badge: '接口就绪',
    ready: true,
    icon: Camera,
  },
]

onMounted(() => {
  void store.check()
})
</script>

<template>
  <div class="min-h-dvh bg-background">
    <div
      class="pointer-events-none fixed inset-x-0 top-0 -z-10 h-72 bg-gradient-to-b from-primary/10 via-primary/5 to-transparent"
      aria-hidden="true"
    />

    <header class="mx-auto flex w-full max-w-3xl items-center justify-between px-5 pt-6">
      <div class="flex items-center gap-3">
        <div class="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
          <ScanSearch class="h-5 w-5" />
        </div>
        <div>
          <p class="text-base font-semibold leading-tight">标准镜</p>
          <p class="text-xs text-muted-foreground">Standard Lens</p>
        </div>
      </div>
      <div class="flex items-center gap-1 sm:gap-2">
        <RouterLink
          to="/products"
          aria-label="商品查询"
          class="inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Search class="h-4 w-4" />
          <span class="hidden sm:inline">商品查询</span>
        </RouterLink>
        <RouterLink
          to="/settings/ai"
          aria-label="AI 设置"
          class="inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Sparkles class="h-4 w-4" />
          <span class="hidden sm:inline">AI 设置</span>
        </RouterLink>
        <Badge variant="outline" class="bg-background/70 text-[11px] backdrop-blur">Phase 7</Badge>
      </div>
    </header>

    <main class="mx-auto w-full max-w-3xl px-5 pb-16 pt-8">
      <section class="space-y-3">
        <h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">商品标准查询与 AI 图片识别</h1>
        <p class="text-sm leading-relaxed text-muted-foreground sm:text-base">
          标准同步、版本链、商品查询与 AI 设置已接入；图片识别接口已就绪，上传页面待开发。
        </p>
      </section>

      <Card class="mt-8 overflow-hidden border-border/70 shadow-sm">
        <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
          <div class="space-y-1">
            <CardTitle class="text-base">服务状态</CardTitle>
            <CardDescription>前端与后端 API 的连通性检查</CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            :disabled="store.isLoading"
            aria-label="刷新服务状态"
            @click="store.check()"
          >
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': store.isLoading }" />
            <span class="hidden sm:inline">刷新</span>
          </Button>
        </CardHeader>

        <CardContent class="space-y-6">
          <div
            class="flex items-start gap-3 rounded-xl border p-4 transition-colors"
            :class="statusPresentation.panel"
            role="status"
            aria-live="polite"
          >
            <component
              :is="statusPresentation.icon"
              class="mt-0.5 h-5 w-5 shrink-0"
              :class="statusPresentation.iconColor"
            />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold">{{ statusPresentation.title }}</p>
              <p class="mt-1 break-words text-xs leading-relaxed text-muted-foreground">
                {{ statusPresentation.hint }}
              </p>
            </div>
            <Badge variant="outline" :class="statusPresentation.badge">
              {{ statusPresentation.label }}
            </Badge>
          </div>

          <dl class="grid grid-cols-1 gap-px overflow-hidden rounded-xl border bg-border text-sm sm:grid-cols-2">
            <div class="bg-card px-4 py-3">
              <dt class="text-xs text-muted-foreground">API 版本</dt>
              <dd class="mt-1 font-medium tabular-nums">{{ store.data?.version ?? '—' }}</dd>
            </div>
            <div class="bg-card px-4 py-3">
              <dt class="text-xs text-muted-foreground">运行环境</dt>
              <dd class="mt-1 font-medium">{{ store.data?.environment ?? '—' }}</dd>
            </div>
            <div class="bg-card px-4 py-3">
              <dt class="text-xs text-muted-foreground">MySQL</dt>
              <dd class="mt-1 flex items-center gap-2 font-medium">
                <span
                  class="h-1.5 w-1.5 rounded-full"
                  :class="
                    store.data?.database.status === 'ok'
                      ? 'bg-emerald-500'
                      : store.data?.database.status === 'down'
                        ? 'bg-red-500'
                        : 'bg-muted-foreground'
                  "
                />
                {{ databaseText }}
              </dd>
            </div>
            <div class="bg-card px-4 py-3">
              <dt class="text-xs text-muted-foreground">数据库耗时</dt>
              <dd class="mt-1 font-medium tabular-nums">
                {{ store.data?.database.latency_ms != null ? `${store.data.database.latency_ms} ms` : '—' }}
              </dd>
            </div>
          </dl>
        </CardContent>

        <CardFooter
          class="flex flex-wrap items-center justify-between gap-2 border-t bg-muted/40 px-6 py-3 text-xs text-muted-foreground"
        >
          <span>最近检测：{{ lastCheckedText }}</span>
          <span v-if="store.latencyMs !== null" class="tabular-nums">往返耗时 {{ store.latencyMs }} ms</span>
        </CardFooter>
      </Card>

      <section class="mt-10">
        <h2 class="text-sm font-semibold">功能状态</h2>
        <ul class="mt-3 space-y-2">
          <li
            v-for="item in roadmap"
            :key="item.title"
            class="flex items-start gap-3 rounded-xl border bg-card p-4"
          >
            <div class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
              <component :is="item.icon" class="h-4 w-4" />
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium">{{ item.title }}</p>
              <p class="mt-0.5 text-xs leading-relaxed text-muted-foreground">{{ item.description }}</p>
            </div>
            <Badge :variant="item.ready ? 'default' : 'secondary'" class="ml-auto shrink-0">
              {{ item.badge }}
            </Badge>
          </li>
        </ul>
      </section>
    </main>

    <footer class="mx-auto w-full max-w-3xl px-5 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-center text-xs text-muted-foreground">
      <p>识别结果仅用于标准版本核对，不构成产品合规结论。</p>
      <p class="mt-1">© {{ year }} Standard Lens</p>
    </footer>
  </div>
</template>
