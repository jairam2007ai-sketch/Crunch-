import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '../styles.css'
import PosView from '../shared/staff/PosView.vue'
import App from './App.vue'
import { staff } from './store'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: PosView },
    { path: '/queue', component: () => import('../shared/staff/QueueView.vue') },
    { path: '/refunds', component: () => import('./views/RefundsView.vue') },
    { path: '/stock', component: () => import('./views/StockView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

createApp(App).provide('staff', staff).use(router).mount('#app')
