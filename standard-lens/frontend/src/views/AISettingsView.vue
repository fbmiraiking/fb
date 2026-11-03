<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowLeft,
  CircleCheck,
  Clock3,
  Eye,
  EyeOff,
  HardDrive,
  KeyRound,
  LoaderCircle,
  Save,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Trash2,
  TriangleAlert,
  Zap,
} from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AI_PROVIDER_OPTIONS, isAIProvider } from '@/lib/ai'
import { useAISettingsStore } from '@/stores/aiSettings'

const store = useAISettingsStore()
const showApiKey = ref(false)
const year = new Date().getFullYear()

function onProviderChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (isAIProvider(value)) {
    store.setProvider(value)
    store.clearFeedback()
  }
}

function testConnection() {
  void store.testConnection()
}

function saveConfig() {
  store.saveConfig()
}

function clearConfig() {
  store.clearConfig()
}
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
      <section class="space-y-3">
        <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" class="border-primary/20 bg-primary/5 text-primary">
            <Sparkles class="mr-1 h-3 w-3" />
            用户自备 Key
          </Badge>
          <span>默认保存在 sessionStorage</span>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">AI 设置</h1>
        <p class="max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          配置你自己的多模态 AI Provider。系统不提供固定 Key，API Key 不会保存到后端数据库，也不会写入后端日志。
        </p>
      </section>

      <Card class="mt-6 border-emerald-200/70 bg-emerald-50/40">
        <CardContent class="flex items-start gap-3 px-4 py-4 sm:px-5">
          <ShieldCheck class="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
          <div class="min-w-0 space-y-1 text-xs leading-relaxed text-emerald-900/80">
            <p class="font-medium text-emerald-900">Key 只保存在当前浏览器设备</p>
            <p>
              默认使用 sessionStorage，关闭标签页即清除；切换到 localStorage 会长期保留，公共电脑请谨慎使用。
              测试连接或后续图片识别时，配置会随 POST 请求发送到后端，后端仅在本次请求内使用并直接转发给 AI 服务。
            </p>
            <p>自定义 Base URL 会让后端向你填写的地址发起请求，请只使用可信服务。</p>
          </div>
        </CardContent>
      </Card>

      <Card class="mt-4">
        <CardHeader class="pb-3">
          <div class="flex items-center gap-2">
            <KeyRound class="h-4 w-4 text-muted-foreground" />
            <CardTitle class="text-base">Provider 配置</CardTitle>
          </div>
        </CardHeader>

        <CardContent class="space-y-5">
          <div class="space-y-1.5">
            <label for="ai-provider" class="text-sm font-medium">Provider</label>
            <select
              id="ai-provider"
              :value="store.provider"
              class="h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-ring/20"
              @change="onProviderChange"
            >
              <option v-for="option in AI_PROVIDER_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <p class="text-xs leading-relaxed text-muted-foreground">{{ store.providerOption.hint }}</p>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <label for="ai-base-url" class="text-sm font-medium">Base URL</label>
              <input
                id="ai-base-url"
                v-model="store.apiBaseUrl"
                type="url"
                spellcheck="false"
                autocomplete="off"
                :placeholder="
                  store.providerOption.defaultBaseUrl || 'https://your-provider.example/v1'
                "
                class="h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
                @input="store.clearFeedback()"
              />
              <p class="text-xs leading-relaxed text-muted-foreground">
                <template v-if="store.providerOption.needsBaseUrl">必填，需包含完整的 /v1 路径。</template>
                <template v-else>
                  留空使用默认地址
                  <span class="font-mono">{{ store.providerOption.defaultBaseUrl }}</span>
                </template>
              </p>
            </div>

            <div class="space-y-1.5">
              <label for="ai-model" class="text-sm font-medium">模型</label>
              <input
                id="ai-model"
                v-model="store.model"
                type="text"
                spellcheck="false"
                autocomplete="off"
                :placeholder="store.providerOption.modelPlaceholder"
                class="h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
                @input="store.clearFeedback()"
              />
              <p class="text-xs leading-relaxed text-muted-foreground">
                需要填写支持图片输入的多模态模型。
              </p>
            </div>
          </div>

          <div class="space-y-1.5">
            <label for="ai-api-key" class="text-sm font-medium">API Key</label>
            <div class="relative">
              <input
                id="ai-api-key"
                v-model="store.apiKey"
                :type="showApiKey ? 'text' : 'password'"
                name="aiApiKey"
                autocomplete="off"
                spellcheck="false"
                placeholder="输入你的 API Key"
                class="h-10 w-full rounded-md border border-input bg-background px-3 pr-11 font-mono text-sm shadow-sm outline-none transition-colors placeholder:font-sans placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
                @input="store.clearFeedback()"
              />
              <button
                type="button"
                class="absolute right-1 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                :aria-label="showApiKey ? '隐藏 API Key' : '显示 API Key'"
                @click="showApiKey = !showApiKey"
              >
                <EyeOff v-if="showApiKey" class="h-4 w-4" />
                <Eye v-else class="h-4 w-4" />
              </button>
            </div>
            <p class="text-xs leading-relaxed text-muted-foreground">
              输入框默认隐藏内容；Key 只发送到你选择的 AI Provider，不经过本系统数据库。
            </p>
          </div>

          <div class="space-y-2">
            <p class="text-sm font-medium">保存位置</p>
            <div class="grid gap-2 sm:grid-cols-2">
              <label
                class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors"
                :class="
                  store.storageMode === 'session'
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                    : 'border-border bg-background hover:bg-accent/30'
                "
              >
                <input
                  v-model="store.storageMode"
                  type="radio"
                  value="session"
                  class="mt-1 accent-primary"
                  @change="store.clearFeedback()"
                />
                <span class="min-w-0">
                  <span class="flex items-center gap-1.5 text-sm font-medium">
                    <Clock3 class="h-3.5 w-3.5" />
                    sessionStorage
                    <Badge variant="secondary" class="ml-1 text-[10px]">默认</Badge>
                  </span>
                  <span class="mt-1 block text-xs leading-relaxed text-muted-foreground">
                    仅当前标签页；关闭标签页后清除。
                  </span>
                </span>
              </label>

              <label
                class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors"
                :class="
                  store.storageMode === 'local'
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                    : 'border-border bg-background hover:bg-accent/30'
                "
              >
                <input
                  v-model="store.storageMode"
                  type="radio"
                  value="local"
                  class="mt-1 accent-primary"
                  @change="store.clearFeedback()"
                />
                <span class="min-w-0">
                  <span class="flex items-center gap-1.5 text-sm font-medium">
                    <HardDrive class="h-3.5 w-3.5" />
                    localStorage
                  </span>
                  <span class="mt-1 block text-xs leading-relaxed text-muted-foreground">
                    当前设备长期保留；公共电脑不建议使用。
                  </span>
                </span>
              </label>
            </div>
          </div>

          <p v-if="store.formError" class="text-xs text-red-600">{{ store.formError }}</p>
          <p v-if="store.savedMessage" class="text-xs text-emerald-700">{{ store.savedMessage }}</p>

          <div class="flex flex-wrap items-center gap-2">
            <Button variant="outline" :disabled="store.isTesting" @click="testConnection">
              <LoaderCircle v-if="store.isTesting" class="h-4 w-4 animate-spin" />
              <Zap v-else class="h-4 w-4" />
              {{ store.isTesting ? '测试中…' : '测试连接' }}
            </Button>
            <Button @click="saveConfig">
              <Save class="h-4 w-4" />
              保存配置
            </Button>
            <Button variant="ghost" class="text-muted-foreground" @click="clearConfig">
              <Trash2 class="h-4 w-4" />
              清除
            </Button>
          </div>
          <p class="text-xs leading-relaxed text-muted-foreground">
            测试连接不会自动保存；保存配置只写入浏览器，不发送到后端。测试连接会发送一次跨服务请求，可能产生少量费用。
          </p>

          <div
            v-if="store.testState === 'success'"
            class="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"
            role="status"
          >
            <CircleCheck class="mt-0.5 h-4 w-4 shrink-0" />
            <div class="min-w-0">
              <p class="font-medium">{{ store.testMessage }}</p>
              <p v-if="store.testResult" class="mt-0.5 text-xs">
                {{ store.testResult.model }} · {{ store.testResult.latencyMs }} ms
              </p>
            </div>
          </div>

          <div
            v-else-if="store.testState === 'error'"
            class="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"
            role="alert"
          >
            <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
            <p class="min-w-0 font-medium">{{ store.testMessage }}</p>
          </div>
        </CardContent>
      </Card>

      <p class="mt-6 text-center text-xs leading-relaxed text-muted-foreground">
        AI 识别结果仅用于辅助查找，不构成产品合规结论。请遵守所选 AI 服务的使用条款。
      </p>
    </main>

    <footer
      class="mx-auto w-full max-w-3xl px-5 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-center text-xs text-muted-foreground"
    >
      <p>© {{ year }} Standard Lens</p>
    </footer>
  </div>
</template>
