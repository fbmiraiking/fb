import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/settings/ai',
      name: 'ai-settings',
      component: () => import('@/views/AISettingsView.vue'),
    },
    {
      path: '/products',
      name: 'product-search',
      component: () => import('@/views/ProductSearchView.vue'),
    },
    {
      path: '/standards/:id(\\d+)',
      name: 'standard-detail',
      component: () => import('@/views/StandardDetailView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
