import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '../styles.css'
import App from './App.vue'
import MenuView from './views/MenuView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: MenuView },
    { path: '/order/:token', component: () => import('./views/TrackView.vue'), props: true },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

createApp(App).use(router).mount('#app')
