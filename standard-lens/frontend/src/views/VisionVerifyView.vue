<script setup lang="ts">
import { computed, onBeforeUnmount, ref, type Component } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowLeft,
  Camera,
  CircleCheck,
  CircleHelp,
  FileText,
  FlaskConical,
  ImagePlus,
  Info,
  LoaderCircle,
  Ruler,
  ScanLine,
  ShieldAlert,
  Sparkles,
  Tag,
  Trash2,
  TriangleAlert,
} from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, statusMeta } from '@/lib/standard-status'
import { useAISettingsStore } from '@/stores/aiSettings'
import { useVisionVerifyStore } from '@/stores/visionVerify'
import type {
  RequirementCheckItem,
  RequirementCheckStatus,
  RequirementType,
} from '@/types/vision'

const aiStore = useAISettingsStore()
const store = useVisionVerifyStore()
const fileInput = ref<HTMLInputElement | null>(null)
const localError = ref('')
const year = new Date().getFullYear()

const MAX_IMAGE_BYTES = 10 * 1024 * 1024
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const requirementTypeMeta: Record<
  RequirementType,
  { label: string; icon: Component }
> = {
  VISUAL: { label: '外观 / 目视', icon: Camera },
  LABEL: { label: '标签 / 标识', icon: Tag },
  DOCUMENT: { label: '证书 / 文档', icon: FileText },
  LAB_TEST: { label: '实验室检测', icon: FlaskConical },
  MEASUREMENT: { label: '测量', icon: Ruler },
}

interface CheckMeta {
  icon: Component
  iconClass: string
  rowClass: string
}

const CHECK_META: Record<RequirementCheckStatus, CheckMeta> = {
  OBSERVED: {
    icon: CircleCheck,
    iconClass: 'text-emerald-600',
    rowClass: 'border-emerald-200 bg-emerald-50/50',
  },
  PARTIAL: {
    icon: CircleHelp,
    iconClass: 'text-amber-600',
    rowClass: 'border-amber-200 bg-amber-50/40',
  },
  NOT_OBSERVED: {
    icon: CircleHelp,
    iconClass: 'text-amber-600',
    rowClass: 'border-amber-200 bg-amber-50/40',
  },
  NEEDS_DOCUMENT: {
    icon: FileText,
    iconClass: 'text-sky-600',
    rowClass: 'border-sky-200 bg-sky-50/40',
  },
  NOT_POSSIBLE: {
    icon: FlaskConical,
    iconClass: 'text-muted-foreground',
    rowClass: 'border-border bg-muted/30',
  },
  CANNOT_VERIFY: {
    icon: Ruler,
    iconClass: 'text-muted-foreground',
    rowClass: 'border-border bg-muted/30',
  },
}

const canSubmit = computed(
  () =>
    Boolean(store.file) &&
    aiStore.isConfigured &&
    !store.isAnalyzing,
)

const verificationGroups = computed(
  () => store.result?.standardVerification ?? [],
)

const unmatchedNumbers = computed(
  () => store.result?.unmatchedVisibleStandardNumbers ?? [],
)

function checkMeta(status: RequirementCheckStatus): CheckMeta {
  return CHECK_META[status] ?? CHECK_META.CANNOT_VERIFY
}

function typeMeta(type: RequirementType) {
  return requirementTypeMeta[type] ?? requirementTypeMeta.VISUAL
}

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const selected = input.files?.[0]
  input.value = ''
  if (!selected) {
    return
  }
  localError.value = ''
  if (!ACCEPTED_TYPES.includes(selected.type)) {
    localError.value = '只支持 JPEG、PNG、WebP 图片，HEIC 暂不支持。'
    return
  }
  if (selected.size > MAX_IMAGE_BYTES) {
    localError.value = '图片超过 10MB，请压缩或重新拍照。'
    return
  }
  store.setFile(selected)
}

function submit() {
  localError.value = ''
  if (!store.file) {
    localError.value = '请先选择一张商品图片。'
    return
  }
  if (!aiStore.isConfigured) {
    localError.value = '请先在 AI 设置中填写 API Key 和模型。'
    return
  }
  const configError = aiStore.validate()
  if (configError) {
    localError.value = configError
    return
  }
  void store.analyze({
    provider: aiStore.provider,
    apiBaseUrl: aiStore.apiBaseUrl,
    apiKey: aiStore.apiKey,
    model: aiStore.model,
  })
}

function evidenceList(item: RequirementCheckItem): string[] {
  return item.evidence.slice(0, 5)
}

onBeforeUnmount(() => {
  store.dispose()
})
</script>

<template>
  <div class="min-h-dvh bg-background">
    <div
      class="pointer-events-none fixed inset-x-0 top-0 -z-10 h-72 bg-gradient-to-b from-primary/10 via-primary/5 to-transparent"
      aria-hidden="true"
    />

    <header class="mx-auto flex w-full max-w-4xl items-center justify-between gap-3 px-5 pt-6">
      <RouterLink to="/" class="flex min-w-0 items-center gap-3">
        <div class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
          <ScanLine class="h-5 w-5" />
        </div>
        <div class="min-w-0">
          <p class="text-base font-semibold leading-tight">标准镜</p>
          <p class="text-xs text-muted-foreground">Standard Lens</p>
        </div>
      </RouterLink>
      <div class="flex shrink-0 items-center gap-1">
        <RouterLink
          to="/settings/ai"
          class="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Sparkles class="h-4 w-4" />
          AI 设置
        </RouterLink>
        <RouterLink
          to="/"
          class="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ArrowLeft class="h-4 w-4" />
          返回
        </RouterLink>
      </div>
    </header>

    <main class="mx-auto w-full max-w-4xl px-5 pb-16 pt-8">
      <section class="space-y-3">
        <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" class="border-primary/20 bg-primary/5 text-primary">
            <Camera class="mr-1 h-3 w-3" />
            图片辅助核验
          </Badge>
          <span>只核对照片中可见的信息</span>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">图片标准辅助核验</h1>
        <p class="max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          上传商品包装或标签照片，识别执行标准并核对标准库中的可观察要求。图片结果只用于辅助核对，不构成完整合规结论。
        </p>
      </section>

      <Card v-if="!aiStore.isConfigured" class="mt-6 border-amber-200 bg-amber-50/60">
        <CardContent class="flex items-start gap-3 px-5 py-4">
          <Info class="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div class="min-w-0 flex-1 space-y-1 text-sm">
            <p class="font-medium text-amber-900">尚未配置 AI Provider</p>
            <p class="text-xs leading-relaxed text-amber-900/80">
              图片识别使用你自己的多模态 AI Key。配置只保存在当前浏览器。
            </p>
          </div>
          <RouterLink
            to="/settings/ai"
            class="shrink-0 rounded-md border border-amber-300 bg-background px-3 py-1.5 text-xs font-medium text-amber-900 transition-colors hover:bg-amber-100"
          >
            去配置
          </RouterLink>
        </CardContent>
      </Card>

      <Card class="mt-6">
        <CardContent class="space-y-4 px-5 py-5">
          <div
            v-if="!store.previewUrl"
            class="rounded-2xl border-2 border-dashed border-border bg-muted/20 px-4 py-10 text-center"
          >
            <div class="mx-auto grid h-12 w-12 place-items-center rounded-full bg-background text-muted-foreground shadow-sm">
              <ImagePlus class="h-5 w-5" />
            </div>
            <p class="mt-3 text-sm font-medium">选择商品包装或标签照片</p>
            <p class="mt-1 text-xs text-muted-foreground">支持 JPEG / PNG / WebP，最大 10MB</p>
            <Button variant="outline" class="mt-4" @click="pickFile">
              <ImagePlus class="h-4 w-4" />
              选择图片
            </Button>
          </div>

          <div v-else class="relative overflow-hidden rounded-xl border bg-muted/30">
            <img
              :src="store.previewUrl"
              alt="待核验商品图片预览"
              class="max-h-[360px] w-full object-contain"
            />
            <button
              type="button"
              class="absolute right-2 top-2 grid h-9 w-9 place-items-center rounded-full bg-background/90 text-muted-foreground shadow-sm transition-colors hover:bg-background hover:text-foreground"
              aria-label="移除图片"
              @click="store.clearFile()"
            >
              <Trash2 class="h-4 w-4" />
            </button>
          </div>

          <input
            ref="fileInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            class="hidden"
            @change="onFileChange"
          />

          <div class="flex flex-wrap items-center gap-2">
            <Button variant="outline" @click="pickFile">
              <ImagePlus class="h-4 w-4" />
              {{ store.file ? '重新选择' : '选择图片' }}
            </Button>
            <Button :disabled="!canSubmit" @click="submit">
              <LoaderCircle v-if="store.isAnalyzing" class="h-4 w-4 animate-spin" />
              <ScanLine v-else class="h-4 w-4" />
              {{ store.isAnalyzing ? '识别与核验中…' : '开始识别并核验' }}
            </Button>
            <span v-if="store.file" class="text-xs text-muted-foreground">
              {{ store.file.name }} · {{ formatFileSize(store.file.size) }}
            </span>
          </div>

          <p class="text-xs leading-relaxed text-muted-foreground">
            图片只在内存中处理，不保存到服务器；AI 配置随本次请求发送，不写入数据库或日志。
          </p>

          <p v-if="localError" class="text-xs text-red-600" role="alert">{{ localError }}</p>
        </CardContent>
      </Card>

      <Card v-if="store.state === 'analyzing'" class="mt-6">
        <CardContent class="flex items-center gap-3 px-5 py-6 text-sm text-muted-foreground">
          <LoaderCircle class="h-5 w-5 animate-spin text-primary" />
          正在识别图片并查询标准库，请稍候…
        </CardContent>
      </Card>

      <Card v-else-if="store.state === 'error'" class="mt-6 border-red-200">
        <CardContent class="flex items-start gap-3 px-5 py-4">
          <TriangleAlert class="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-red-700">核验失败</p>
            <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ store.errorMessage }}</p>
          </div>
          <Button variant="outline" size="sm" :disabled="!canSubmit" @click="submit">
            重试
          </Button>
        </CardContent>
      </Card>

      <section v-if="store.state === 'done' && store.result" class="mt-8 space-y-4">
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="text-base">识别结果</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <p class="text-xs text-muted-foreground">商品</p>
                <p class="mt-0.5 font-medium">{{ store.result.imageAnalysis.product.name || '未识别' }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">类别</p>
                <p class="mt-0.5 font-medium">{{ store.result.imageAnalysis.product.categoryGuess || '未识别' }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">材质</p>
                <p class="mt-0.5">{{ store.result.imageAnalysis.materials.join('、') || '未识别' }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">生产厂家</p>
                <p class="mt-0.5">{{ store.result.imageAnalysis.manufacturer || '未识别' }}</p>
              </div>
            </div>

            <div v-if="store.result.imageAnalysis.visibleStandardNumbers.length">
              <p class="text-xs text-muted-foreground">图片中明确可见的标准号</p>
              <div class="mt-1.5 flex flex-wrap gap-1.5">
                <Badge
                  v-for="number in store.result.imageAnalysis.visibleStandardNumbers"
                  :key="number"
                  variant="secondary"
                  class="font-mono"
                >
                  {{ number }}
                </Badge>
              </div>
            </div>

            <details v-if="store.result.imageAnalysis.visibleText.length" class="text-xs">
              <summary class="cursor-pointer text-muted-foreground">查看识别到的标签文字</summary>
              <ul class="mt-2 space-y-1 rounded-lg bg-muted/40 p-3 leading-relaxed text-muted-foreground">
                <li v-for="(line, index) in store.result.imageAnalysis.visibleText" :key="index">
                  {{ line }}
                </li>
              </ul>
            </details>
          </CardContent>
        </Card>

        <Card v-if="unmatchedNumbers.length" class="border-amber-200 bg-amber-50/50">
          <CardContent class="flex items-start gap-3 px-5 py-4">
            <TriangleAlert class="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div class="min-w-0 text-sm">
              <p class="font-medium text-amber-900">有标准号未在标准库中找到</p>
              <p class="mt-1 text-xs leading-relaxed text-amber-900/80">
                {{ unmatchedNumbers.join('、') }}。系统不会根据相似编号补全或生成标准条目。
              </p>
            </div>
          </CardContent>
        </Card>

        <template v-if="verificationGroups.length">
          <Card
            v-for="group in verificationGroups"
            :key="group.standardId"
            class="overflow-hidden"
          >
            <CardHeader class="border-b bg-muted/20 pb-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">包装执行标准</Badge>
                    <Badge :class="statusMeta(group.status).badge">{{ group.statusLabel }}</Badge>
                  </div>
                  <CardTitle class="mt-2 break-all font-mono text-lg">{{ group.standardNo }}</CardTitle>
                  <p class="mt-1 text-sm text-muted-foreground">{{ group.standardName }}</p>
                </div>
                <RouterLink
                  :to="`/standards/${group.standardId}`"
                  class="shrink-0 text-xs text-primary underline-offset-4 hover:underline"
                >
                  查看标准详情
                </RouterLink>
              </div>
            </CardHeader>

            <CardContent class="space-y-4 px-5 py-5">
              <div class="grid gap-3 rounded-xl bg-muted/40 p-4 text-sm sm:grid-cols-2">
                <div>
                  <p class="text-xs text-muted-foreground">当前状态</p>
                  <p class="mt-0.5 font-medium">{{ group.statusLabel }}</p>
                </div>
                <div>
                  <p class="text-xs text-muted-foreground">实施日期</p>
                  <p class="mt-0.5">{{ formatDate(group.effectiveDate) }}</p>
                </div>
                <div v-if="group.replacementStandards.length" class="sm:col-span-2">
                  <p class="text-xs text-muted-foreground">当前替代标准</p>
                  <div class="mt-1 flex flex-wrap gap-1.5">
                    <RouterLink
                      v-for="standard in group.replacementStandards"
                      :key="standard.id"
                      :to="`/standards/${standard.id}`"
                      class="rounded-md border border-primary/20 bg-primary/5 px-2 py-1 font-mono text-xs text-primary transition-colors hover:bg-primary/10"
                    >
                      {{ standard.standardNo }}
                    </RouterLink>
                  </div>
                </div>
                <div v-else-if="group.latestCurrent.length" class="sm:col-span-2">
                  <p class="text-xs text-muted-foreground">最新现行标准</p>
                  <div class="mt-1 flex flex-wrap gap-1.5">
                    <RouterLink
                      v-for="standard in group.latestCurrent"
                      :key="standard.id"
                      :to="`/standards/${standard.id}`"
                      class="rounded-md border border-primary/20 bg-primary/5 px-2 py-1 font-mono text-xs text-primary transition-colors hover:bg-primary/10"
                    >
                      {{ standard.standardNo }}
                    </RouterLink>
                  </div>
                </div>
              </div>

              <p
                v-if="group.lifecycleNotice"
                class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900"
              >
                {{ group.lifecycleNotice }}
              </p>

              <div>
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <h2 class="text-sm font-semibold">图片可检查项</h2>
                  <span class="text-xs text-muted-foreground">{{ group.summary }}</span>
                </div>

                <p v-if="!group.requirements.length" class="mt-3 rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">
                  标准库暂未录入该标准的核验要求，无法逐项核验。
                </p>

                <ul v-else class="mt-3 space-y-2">
                  <li
                    v-for="item in group.requirements"
                    :key="item.requirementId"
                    class="rounded-xl border p-3"
                    :class="checkMeta(item.status).rowClass"
                  >
                    <div class="flex items-start gap-3">
                      <component
                        :is="checkMeta(item.status).icon"
                        class="mt-0.5 h-5 w-5 shrink-0"
                        :class="checkMeta(item.status).iconClass"
                      />
                      <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-center gap-1.5">
                          <Badge variant="outline" class="font-mono text-[10px]">{{ item.chapter }}</Badge>
                          <Badge variant="secondary" class="gap-1 text-[10px]">
                            <component :is="typeMeta(item.requirementType).icon" class="h-3 w-3" />
                            {{ typeMeta(item.requirementType).label }}
                          </Badge>
                          <span class="text-xs font-medium" :class="checkMeta(item.status).iconClass">
                            {{ item.statusLabel }}
                          </span>
                        </div>
                        <p class="mt-2 text-sm font-medium leading-relaxed">{{ item.requirementText }}</p>
                        <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ item.message }}</p>

                        <div v-if="evidenceList(item).length" class="mt-2 flex flex-wrap gap-1.5">
                          <span
                            v-for="evidence in evidenceList(item)"
                            :key="evidence"
                            class="rounded bg-background/80 px-1.5 py-0.5 text-[11px] text-muted-foreground ring-1 ring-border"
                          >
                            {{ evidence }}
                          </span>
                        </div>

                        <p class="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                          核验方式：{{ item.verificationMethod }}
                        </p>
                      </div>
                    </div>
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </template>

        <Card v-else>
          <CardContent class="flex flex-col items-center px-6 py-10 text-center">
            <div class="grid h-12 w-12 place-items-center rounded-full bg-muted text-muted-foreground">
              <ScanLine class="h-5 w-5" />
            </div>
            <h2 class="mt-4 text-base font-semibold">没有匹配到数据库中的标准</h2>
            <p class="mt-1 max-w-md text-sm leading-relaxed text-muted-foreground">
              图片中可能没有清晰的标准号，或该标准尚未同步到标准库。系统不会根据图片猜测标准编号。
            </p>
          </CardContent>
        </Card>

        <Card class="border-amber-300 bg-amber-50">
          <CardContent class="flex items-start gap-3 px-5 py-4">
            <ShieldAlert class="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div class="min-w-0 text-sm">
              <p class="font-medium text-amber-900">核验边界</p>
              <p class="mt-1 text-xs leading-relaxed text-amber-900/80">
                {{ store.result.verificationNotice }}
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <p class="mt-6 text-center text-xs leading-relaxed text-muted-foreground">
        图片分析只能辅助核对可见信息，不能替代实验检测、检测报告或合规认证。
      </p>
    </main>

    <footer
      class="mx-auto w-full max-w-4xl px-5 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-center text-xs text-muted-foreground"
    >
      <p>© {{ year }} Standard Lens</p>
    </footer>
  </div>
</template>
