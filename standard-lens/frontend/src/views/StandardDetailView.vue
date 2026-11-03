<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowLeft,
  CalendarDays,
  CircleCheck,
  CircleX,
  Clock3,
  ExternalLink,
  FileText,
  History,
  LoaderCircle,
  RefreshCw,
  ScanSearch,
  TriangleAlert,
} from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, formatVersionYear, statusMeta } from '@/lib/standard-status'
import { cn } from '@/lib/utils'
import { useStandardDetailStore } from '@/stores/standardDetail'

const route = useRoute()
const store = useStandardDetailStore()

const standardId = computed(() => Number(route.params.id))
const isValidId = computed(() => Number.isInteger(standardId.value) && standardId.value > 0)
const detailStatus = computed(() => statusMeta(store.standard?.status))
const canRetry = computed(() => isValidId.value && store.state === 'error')
const year = new Date().getFullYear()

function retry() {
  if (isValidId.value) {
    void store.load(standardId.value)
  }
}

watch(
  () => route.params.id,
  () => {
    if (isValidId.value) {
      void store.load(standardId.value)
    } else {
      store.reset()
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="min-h-dvh bg-background">
    <div
      class="pointer-events-none fixed inset-x-0 top-0 -z-10 h-72 bg-gradient-to-b from-primary/10 via-primary/5 to-transparent"
      aria-hidden="true"
    />

    <header class="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-5 pt-6">
      <RouterLink to="/" class="flex min-w-0 items-center gap-3">
        <div class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
          <ScanSearch class="h-5 w-5" />
        </div>
        <div class="min-w-0">
          <p class="text-base font-semibold leading-tight">标准镜</p>
          <p class="text-xs text-muted-foreground">Standard Lens</p>
        </div>
      </RouterLink>
      <RouterLink
        to="/"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <ArrowLeft class="h-4 w-4" />
        返回首页
      </RouterLink>
    </header>

    <main class="mx-auto w-full max-w-3xl px-5 pb-16 pt-8">
      <Card v-if="!isValidId" class="mt-4">
        <CardContent class="flex flex-col items-center px-6 py-14 text-center">
          <div class="grid h-12 w-12 place-items-center rounded-full bg-muted text-muted-foreground">
            <CircleX class="h-6 w-6" />
          </div>
          <h1 class="mt-4 text-lg font-semibold">标准 ID 无效</h1>
          <p class="mt-1 text-sm text-muted-foreground">请检查地址中的标准 ID。</p>
          <RouterLink
            to="/"
            class="mt-5 inline-flex h-10 items-center rounded-md border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-accent"
          >
            返回首页
          </RouterLink>
        </CardContent>
      </Card>

      <Card v-else-if="store.isLoading || store.state === 'idle'" class="mt-4">
        <CardContent class="flex items-center justify-center gap-3 px-6 py-16 text-sm text-muted-foreground">
          <LoaderCircle class="h-5 w-5 animate-spin" />
          正在加载标准详情…
        </CardContent>
      </Card>

      <Card v-else-if="store.state === 'error' || store.state === 'not-found'" class="mt-4">
        <CardContent class="flex flex-col items-center px-6 py-14 text-center">
          <div class="grid h-12 w-12 place-items-center rounded-full bg-muted text-muted-foreground">
            <CircleX v-if="store.isNotFound" class="h-6 w-6" />
            <TriangleAlert v-else class="h-6 w-6" />
          </div>
          <h1 class="mt-4 text-lg font-semibold">
            {{ store.isNotFound ? '未找到该标准' : '加载失败' }}
          </h1>
          <p class="mt-1 max-w-sm text-sm leading-relaxed text-muted-foreground">
            {{ store.errorMessage || '请稍后重试。' }}
          </p>
          <div class="mt-5 flex flex-wrap items-center justify-center gap-2">
            <Button v-if="canRetry" variant="outline" @click="retry">
              <RefreshCw class="h-4 w-4" />
              重试
            </Button>
            <RouterLink
              to="/"
              class="inline-flex h-10 items-center rounded-md border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-accent"
            >
              返回首页
            </RouterLink>
          </div>
        </CardContent>
      </Card>

      <template v-else-if="store.standard">
        <section class="space-y-4">
          <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" :class="detailStatus.badge">{{ detailStatus.label }}</Badge>
            <span>标准详情</span>
            <span v-if="store.standard.standard_type">· {{ store.standard.standard_type }}</span>
          </div>

          <div>
            <p class="font-mono text-sm font-medium text-primary">{{ store.standard.standard_no }}</p>
            <h1 class="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
              {{ store.standard.standard_name }}
            </h1>
          </div>

          <div class="flex flex-wrap items-center gap-3 text-sm">
            <a
              v-if="store.standard.source_url"
              :href="store.standard.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex h-9 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <ExternalLink class="h-4 w-4" />
              查看官方标准
            </a>
            <span v-if="store.standard.source" class="text-xs text-muted-foreground">
              来源：{{ store.standard.source }}
            </span>
          </div>
        </section>

        <Card class="mt-6">
          <CardHeader class="pb-3">
            <CardTitle class="text-base">标准信息</CardTitle>
          </CardHeader>
          <CardContent>
            <dl class="grid grid-cols-1 gap-px overflow-hidden rounded-xl border bg-border text-sm sm:grid-cols-2">
              <div class="bg-card px-4 py-3">
                <dt class="text-xs text-muted-foreground">标准号</dt>
                <dd class="mt-1 break-all font-mono font-medium">{{ store.standard.standard_no }}</dd>
              </div>
              <div class="bg-card px-4 py-3">
                <dt class="text-xs text-muted-foreground">状态</dt>
                <dd class="mt-1">
                  <Badge variant="outline" :class="detailStatus.badge">{{ detailStatus.label }}</Badge>
                </dd>
              </div>
              <div class="bg-card px-4 py-3">
                <dt class="text-xs text-muted-foreground">发布日期</dt>
                <dd class="mt-1 font-medium tabular-nums">{{ formatDate(store.standard.publish_date) }}</dd>
              </div>
              <div class="bg-card px-4 py-3">
                <dt class="text-xs text-muted-foreground">实施日期</dt>
                <dd class="mt-1 font-medium tabular-nums">{{ formatDate(store.standard.effective_date) }}</dd>
              </div>
              <div class="bg-card px-4 py-3">
                <dt class="text-xs text-muted-foreground">失效日期</dt>
                <dd class="mt-1 font-medium tabular-nums">{{ formatDate(store.standard.expiry_date) }}</dd>
              </div>
              <div class="bg-card px-4 py-3">
                <dt class="text-xs text-muted-foreground">标准年份</dt>
                <dd class="mt-1 font-medium tabular-nums">
                  {{ store.standard.standard_year ? `${store.standard.standard_year} 年` : '—' }}
                </dd>
              </div>
            </dl>

            <div v-if="store.standard.scope" class="mt-4 rounded-xl border bg-muted/30 p-4">
              <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <FileText class="h-3.5 w-3.5" />
                适用范围
              </div>
              <p class="mt-2 whitespace-pre-line text-sm leading-relaxed">{{ store.standard.scope }}</p>
            </div>
          </CardContent>
        </Card>

        <section class="mt-10">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold tracking-tight">版本时间轴</h2>
              <p class="mt-1 text-sm leading-relaxed text-muted-foreground">
                按标准年份 / 生效日期从新到旧排列，状态以标准数据为准。
              </p>
            </div>
            <Badge variant="secondary">{{ store.versions.length }} 个版本</Badge>
          </div>

          <div
            v-if="store.versionsError"
            class="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
          >
            <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
            <span>版本链加载失败：{{ store.versionsError }}</span>
          </div>

          <ol v-if="store.versions.length" class="mt-6">
            <li v-for="(version, index) in store.versions" :key="version.id" class="flex gap-3 sm:gap-4">
              <div class="flex w-4 shrink-0 flex-col items-center">
                <span
                  class="mt-2 h-3 w-3 shrink-0 rounded-full ring-4"
                  :class="statusMeta(version.status).dot"
                  aria-hidden="true"
                />
                <span
                  v-if="index < store.versions.length - 1"
                  class="mt-1 w-px flex-1 bg-border"
                  aria-hidden="true"
                />
              </div>

              <div class="min-w-0 flex-1 pb-6">
                <Card
                  class="overflow-hidden shadow-sm"
                  :class="
                    cn(
                      statusMeta(version.status).panel,
                      version.isCurrent ? 'ring-1 ring-primary/10' : '',
                    )
                  "
                >
                  <CardContent class="p-4 sm:p-5">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                      <div class="min-w-0">
                        <p class="text-xs font-medium text-muted-foreground">
                          {{ formatVersionYear(version) }}
                        </p>
                        <p class="mt-1 break-all font-mono text-sm font-semibold text-primary">
                          {{ version.standardNo }}
                        </p>
                        <h3 class="mt-1 text-sm font-medium leading-relaxed sm:text-base">
                          {{ version.standardName }}
                        </h3>
                      </div>
                      <Badge variant="outline" :class="statusMeta(version.status).badge">
                        {{ statusMeta(version.status).label }}
                      </Badge>
                    </div>

                    <dl class="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs">
                      <div class="flex items-center gap-1.5">
                        <CalendarDays class="h-3.5 w-3.5 text-muted-foreground" />
                        <dt class="text-muted-foreground">生效：</dt>
                        <dd class="font-medium tabular-nums">{{ formatDate(version.effectiveDate) }}</dd>
                      </div>
                      <div v-if="version.publishDate" class="flex items-center gap-1.5">
                        <dt class="text-muted-foreground">发布：</dt>
                        <dd class="tabular-nums">{{ formatDate(version.publishDate) }}</dd>
                      </div>
                      <div v-if="version.expiryDate" class="flex items-center gap-1.5">
                        <dt class="text-muted-foreground">失效：</dt>
                        <dd class="font-medium tabular-nums">{{ formatDate(version.expiryDate) }}</dd>
                      </div>
                    </dl>

                    <p
                      v-if="version.isHistorical"
                      class="mt-3 flex items-start gap-1.5 text-xs"
                      :class="version.status === 'ABOLISHED' ? 'text-red-700' : 'text-amber-700'"
                    >
                      <History class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      <span>
                        {{
                          version.status === 'ABOLISHED'
                            ? '已废止，不再作为现行标准'
                            : '旧标准，已被后续版本替代'
                        }}
                      </span>
                    </p>
                    <p
                      v-else-if="version.isCurrent"
                      class="mt-3 flex items-center gap-1.5 text-xs text-emerald-700"
                    >
                      <CircleCheck class="h-3.5 w-3.5" />
                      当前现行标准
                    </p>
                    <p
                      v-else-if="version.isUpcoming"
                      class="mt-3 flex items-center gap-1.5 text-xs text-blue-700"
                    >
                      <Clock3 class="h-3.5 w-3.5" />
                      已发布，尚未实施
                    </p>
                  </CardContent>
                </Card>
              </div>
            </li>
          </ol>

          <p
            v-else-if="!store.versionsError"
            class="mt-6 rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground"
          >
            暂无版本信息
          </p>
        </section>
      </template>

      <Card v-else class="mt-4">
        <CardContent class="px-6 py-14 text-center text-sm text-muted-foreground">
          没有可显示的标准数据。
        </CardContent>
      </Card>
    </main>

    <footer
      class="mx-auto w-full max-w-3xl px-5 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-center text-xs text-muted-foreground"
    >
      <p>版本状态以标准库数据为准，不以年份大小推断现行状态。</p>
      <p class="mt-1">© {{ year }} Standard Lens</p>
    </footer>
  </div>
</template>
