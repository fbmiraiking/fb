<script setup lang="ts">
import { RouterLink } from 'vue-router'
import {
  ArrowLeft,
  ChevronRight,
  LoaderCircle,
  Package,
  RefreshCw,
  Search,
  TriangleAlert,
} from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  PRODUCT_GROUP_KEYS,
  PRODUCT_GROUP_META,
  RELATION_TYPE_META,
} from '@/lib/product'
import { formatDate, statusMeta } from '@/lib/standard-status'
import { useProductsStore } from '@/stores/products'
import type { ProductSummary } from '@/types/product'

const store = useProductsStore()
const year = new Date().getFullYear()

function submitSearch() {
  void store.search(store.query)
}

function chooseProduct(product: ProductSummary) {
  void store.select(product)
}

function retryStandards() {
  void store.retryStandards()
}
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
          <Package class="h-5 w-5" />
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

    <main class="mx-auto w-full max-w-4xl px-5 pb-16 pt-8">
      <section class="space-y-3">
        <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" class="border-primary/20 bg-primary/5 text-primary">商品分类关联</Badge>
          <span>现行 / 即将实施 / 历史 / 相关</span>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">商品标准查询</h1>
        <p class="max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          输入商品名称或别名，查看该商品分类关联的标准。分类关联用于辅助查找，不构成产品合规结论。
        </p>
      </section>

      <form class="mt-6 flex items-stretch gap-2" @submit.prevent="submitSearch">
        <div class="relative min-w-0 flex-1">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            v-model="store.query"
            type="search"
            name="q"
            aria-label="商品名称或别名"
            placeholder="例如：奶瓶、塑料容器、纸尿裤"
            class="h-11 w-full rounded-lg border border-input bg-background pl-10 pr-3 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
          />
        </div>
        <Button type="submit" class="h-11 shrink-0 px-5" :disabled="store.isSearching">
          <LoaderCircle v-if="store.isSearching" class="h-4 w-4 animate-spin" />
          <Search v-else class="h-4 w-4" />
          搜索
        </Button>
      </form>

      <Card v-if="store.searchState === 'error'" class="mt-6">
        <CardContent class="flex items-start gap-3 px-5 py-5">
          <TriangleAlert class="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium">搜索失败</p>
            <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ store.searchError }}</p>
          </div>
          <Button variant="outline" size="sm" @click="submitSearch">
            <RefreshCw class="h-4 w-4" />
            重试
          </Button>
        </CardContent>
      </Card>

      <Card v-else-if="store.searchState === 'idle'" class="mt-6">
        <CardContent class="flex flex-col items-center px-6 py-14 text-center">
          <div class="grid h-12 w-12 place-items-center rounded-full bg-muted text-muted-foreground">
            <Search class="h-5 w-5" />
          </div>
          <h2 class="mt-4 text-base font-semibold">输入商品名称开始查询</h2>
          <p class="mt-1 max-w-sm text-sm leading-relaxed text-muted-foreground">
            可以搜索分类名称，也可以尝试商品别名，例如“婴儿奶瓶”。
          </p>
        </CardContent>
      </Card>

      <Card v-else-if="store.searchState === 'empty'" class="mt-6">
        <CardContent class="px-6 py-12 text-center">
          <p class="text-sm font-medium">没有匹配的商品分类</p>
          <p class="mt-1 text-xs text-muted-foreground">换一个名称或别名试试。</p>
        </CardContent>
      </Card>

      <section v-if="store.results.length" class="mt-8" aria-live="polite">
        <div class="flex items-end justify-between gap-3">
          <div>
            <h2 class="text-base font-semibold">搜索结果</h2>
            <p class="mt-1 text-xs text-muted-foreground">选择一个商品分类查看关联标准。</p>
          </div>
          <Badge variant="secondary">{{ store.total }} 个分类</Badge>
        </div>

        <ul class="mt-3 grid gap-2 sm:grid-cols-2">
          <li v-for="product in store.results" :key="product.id">
            <button
              type="button"
              :aria-pressed="store.selectedId === product.id"
              class="w-full rounded-xl border p-4 text-left transition-colors"
              :class="
                store.selectedId === product.id
                  ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                  : 'border-border bg-card hover:border-primary/30 hover:bg-accent/30'
              "
              @click="chooseProduct(product)"
            >
              <div class="flex items-start gap-3">
                <div class="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
                  <Package class="h-4 w-4" />
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center justify-between gap-2">
                    <p class="truncate text-sm font-semibold">{{ product.name }}</p>
                    <ChevronRight class="h-4 w-4 shrink-0 text-muted-foreground" />
                  </div>
                  <p v-if="product.description" class="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {{ product.description }}
                  </p>
                  <div v-if="product.aliases.length" class="mt-2 flex flex-wrap gap-1">
                    <Badge
                      v-for="alias in product.aliases.slice(0, 3)"
                      :key="alias"
                      variant="secondary"
                      class="font-normal"
                    >
                      {{ alias }}
                    </Badge>
                    <Badge v-if="product.aliases.length > 3" variant="outline" class="font-normal">
                      +{{ product.aliases.length - 3 }}
                    </Badge>
                  </div>
                </div>
              </div>
            </button>
          </li>
        </ul>
      </section>

      <template v-if="store.selected">
        <Card class="mt-8">
          <CardHeader class="pb-3">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <CardTitle class="text-lg">{{ store.selected.name }}</CardTitle>
                <p v-if="store.selected.description" class="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {{ store.selected.description }}
                </p>
              </div>
              <Badge v-if="store.selected.parentId" variant="outline">
                子分类
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div v-if="store.selected.aliases.length" class="flex flex-wrap items-center gap-1.5">
              <span class="text-xs text-muted-foreground">别名：</span>
              <Badge
                v-for="alias in store.selected.aliases"
                :key="alias"
                variant="secondary"
                class="font-normal"
              >
                {{ alias }}
              </Badge>
            </div>
            <p v-else class="text-xs text-muted-foreground">暂无别名</p>
          </CardContent>
        </Card>

        <Card v-if="store.isLoadingStandards" class="mt-4">
          <CardContent class="flex items-center justify-center gap-3 px-6 py-12 text-sm text-muted-foreground">
            <LoaderCircle class="h-5 w-5 animate-spin" />
            正在加载关联标准…
          </CardContent>
        </Card>

        <Card v-else-if="store.standardsState === 'error'" class="mt-4">
          <CardContent class="flex items-start gap-3 px-5 py-5">
            <TriangleAlert class="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium">标准加载失败</p>
              <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ store.standardsError }}</p>
            </div>
            <Button variant="outline" size="sm" @click="retryStandards">
              <RefreshCw class="h-4 w-4" />
              重试
            </Button>
          </CardContent>
        </Card>

        <section v-else-if="store.groups" class="mt-6 space-y-6" aria-live="polite">
          <div v-for="key in PRODUCT_GROUP_KEYS" :key="key">
            <div class="flex items-center justify-between gap-3">
              <div class="flex min-w-0 items-center gap-2">
                <span class="h-2 w-2 shrink-0 rounded-full" :class="PRODUCT_GROUP_META[key].dot" />
                <h2 class="text-base font-semibold">{{ PRODUCT_GROUP_META[key].title }}</h2>
                <Badge variant="secondary">{{ store.groups[key].length }}</Badge>
              </div>
            </div>
            <p class="mt-1 text-xs text-muted-foreground">{{ PRODUCT_GROUP_META[key].description }}</p>

            <div v-if="store.groups[key].length" class="mt-3 space-y-2">
              <RouterLink
                v-for="item in store.groups[key]"
                :key="`${key}-${item.id}`"
                :to="`/standards/${item.id}`"
                class="block rounded-xl border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/30"
              >
                <div class="flex items-start gap-3">
                  <div class="min-w-0 flex-1">
                    <p class="break-all font-mono text-xs font-semibold text-primary">{{ item.standardNo }}</p>
                    <p class="mt-1 text-sm font-medium leading-relaxed">{{ item.standardName }}</p>
                    <div class="mt-2 flex flex-wrap gap-1.5">
                      <Badge variant="outline" :class="statusMeta(item.status).badge">
                        {{ statusMeta(item.status).label }}
                      </Badge>
                      <Badge variant="outline" :class="RELATION_TYPE_META[item.relationType].className">
                        {{ RELATION_TYPE_META[item.relationType].label }}
                      </Badge>
                      <Badge
                        v-if="item.reviewStatus === 'PENDING'"
                        variant="outline"
                        class="border-amber-200 bg-amber-50 text-amber-700"
                      >
                        待审核
                      </Badge>
                    </div>
                    <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <span>生效：<span class="tabular-nums text-foreground">{{ formatDate(item.effectiveDate) }}</span></span>
                      <span v-if="item.expiryDate">
                        失效：<span class="tabular-nums text-foreground">{{ formatDate(item.expiryDate) }}</span>
                      </span>
                    </div>
                  </div>
                  <ChevronRight class="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                </div>
              </RouterLink>
            </div>
            <p
              v-else
              class="mt-3 rounded-xl border border-dashed px-4 py-5 text-center text-xs text-muted-foreground"
            >
              暂无标准
            </p>
          </div>
        </section>
      </template>

      <p class="mt-8 text-center text-xs leading-relaxed text-muted-foreground">
        分类与标准关联仅用于辅助查询，请以标准原文和检测机构结论为准。
      </p>
    </main>

    <footer
      class="mx-auto w-full max-w-4xl px-5 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-center text-xs text-muted-foreground"
    >
      <p>© {{ year }} Standard Lens</p>
    </footer>
  </div>
</template>
