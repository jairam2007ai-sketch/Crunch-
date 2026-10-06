import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '../styles.css'
import App from './App.vue'
import { staff } from './store'
import DashboardView from './views/DashboardView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: DashboardView, meta: { title: 'Dashboard' } },
    { path: '/pos', component: () => import('../shared/staff/PosView.vue'), meta: { title: 'New order' } },
    { path: '/queue', component: () => import('../shared/staff/QueueView.vue'), meta: { title: 'Queue' } },
    { path: '/orders', component: () => import('./views/OrdersView.vue'), meta: { title: 'Orders' } },
    { path: '/refunds', component: () => import('./views/RefundsView.vue'), meta: { title: 'Refunds' } },
    { path: '/assistant', component: () => import('./views/AssistantView.vue'), meta: { title: 'AI assistant' } },
    { path: '/menu', component: () => import('./views/MenuView.vue'), meta: { title: 'Menu & prices' } },
    { path: '/stock', component: () => import('./views/StockView.vue'), meta: { title: 'Stock' } },
    { path: '/team', component: () => import('./views/TeamView.vue'), meta: { title: 'Team' } },
    { path: '/activity', component: () => import('./views/ActivityView.vue'), meta: { title: 'Activity' } },
    { path: '/settings', component: () => import('./views/SettingsView.vue'), meta: { title: 'Settings' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
router.afterEach((to) => { document.title = `${to.meta.title || 'Admin'} · Crunch Admin` })

createApp(App).provide('staff', staff).use(router).mount('#app')
