<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { publicApi } from '../shared/api'
import LoginCard from '../shared/components/LoginCard.vue'
import ToastStack from '../shared/components/ToastStack.vue'
import { loadMenu } from '../shared/menu'
import { poll } from '../shared/toast'
import SetupCard from './components/SetupCard.vue'
import { badges, refreshBadges, session, staff } from './store'

const route = useRoute()
const signedIn = computed(() => !!session.state.token)
const navOpen = ref(false)
const setup = ref(null) // { needs_owner, can_setup_here } on a brand-new install
let stops = []

watch(signedIn, (v) => {
  stops.forEach((s) => s())
  stops = []
  staff.reset()
  if (!v) publicApi.get('/api/setup/status').then((s) => { setup.value = s }).catch(() => {})
  if (v) {
    setup.value = null
    loadMenu(true).catch(() => {})
    refreshBadges().catch(() => {})
    staff.refreshActive().catch(() => {})
    stops = [
      poll(() => refreshBadges().catch(() => {}), 30000),
      poll(() => staff.refreshActive().catch(() => {}), 5000), // new online orders beep here too
    ]
  }
}, { immediate: true })
onBeforeUnmount(() => stops.forEach((s) => s()))
watch(() => route.path, () => { navOpen.value = false })

const newOrders = computed(() => staff.live.active.filter((o) => o.status === 'placed').length)
const count = (key) => (key === 'newOrders' ? newOrders.value : badges[key])

const NAV = [
  { group: 'At the cart', items: [
    { to: '/pos', label: 'New order' },
    { to: '/queue', label: 'Queue', badge: 'newOrders' },
  ] },
  { group: 'Business', items: [
    { to: '/', label: 'Dashboard' },
    { to: '/orders', label: 'Orders' },
    { to: '/refunds', label: 'Refunds', badge: 'refunds' },
    { to: '/assistant', label: 'AI assistant' },
  ] },
  { group: 'Shop', items: [
    { to: '/menu', label: 'Menu & prices' },
    { to: '/stock', label: 'Stock', badge: 'lowStock' },
    { to: '/team', label: 'Team' },
    { to: '/activity', label: 'Activity' },
    { to: '/settings', label: 'Settings' },
  ] },
]
</script>

<template>
  <SetupCard v-if="!signedIn && setup?.needs_owner" :session="session" :allowed="setup.can_setup_here" />
  <LoginCard v-else-if="!signedIn" :session="session" title="Owner sign in" subtitle="The owner's account: everything in one place" />
  <div v-else class="min-h-dvh lg:grid lg:grid-cols-[232px_1fr]">
    <header class="sticky top-0 z-40 flex items-center justify-between bg-char px-4 py-2 text-[#FFF7DA] lg:hidden">
      <span class="mini-lock"><span class="a">Customize Your</span><span class="b">CRUNCH</span></span>
      <button class="btn btn-yellow btn-sm" type="button" :aria-expanded="navOpen" aria-controls="admin-nav" @click="navOpen = !navOpen">Menu</button>
    </header>
    <aside id="admin-nav" class="fixed inset-y-0 left-0 z-50 w-[232px] -translate-x-full overflow-y-auto bg-char text-[#FFF7DA] transition-transform lg:sticky lg:top-0 lg:h-dvh lg:translate-x-0"
           :class="{ 'translate-x-0': navOpen }">
      <div class="px-5 pb-4 pt-5">
        <span class="mini-lock"><span class="a">Customize Your</span><span class="b">CRUNCH</span></span>
        <p class="m-0 mt-2 text-xs font-bold uppercase tracking-widest text-turmeric">Owner</p>
      </div>
      <nav aria-label="Admin">
        <div v-for="g in NAV" :key="g.group" class="mb-4">
          <p class="m-0 px-5 pb-1 text-[11px] font-bold uppercase tracking-widest text-[#A79F8B]">{{ g.group }}</p>
          <RouterLink v-for="n in g.items" :key="n.to" :to="n.to" class="side-link">
            <span>{{ n.label }}</span>
            <span v-if="n.badge && count(n.badge)" class="rounded-full bg-chili px-2 text-xs font-bold text-white tabular-nums">{{ count(n.badge) }}</span>
          </RouterLink>
        </div>
      </nav>
      <div class="border-t border-white/10 px-5 py-4 text-sm">
        <p class="m-0 font-semibold">{{ session.state.user?.name }}</p>
        <p class="m-0 truncate text-xs text-[#A79F8B]">{{ session.state.user?.email }}</p>
        <button class="btn btn-light btn-sm mt-3" type="button" @click="session.logout()">Sign out</button>
      </div>
    </aside>
    <div v-if="navOpen" class="fixed inset-0 z-40 bg-black/40 lg:hidden" @click="navOpen = false" />
    <main class="min-w-0 px-4 py-6 sm:px-6 lg:px-8" style="--sticky-top: 1.5rem">
      <RouterView />
    </main>
  </div>
  <ToastStack />
</template>

<style scoped>
.side-link { display: flex; align-items: center; justify-content: space-between; gap: .5rem; margin: 0 .6rem; padding: .5rem .75rem; border-radius: 10px; color: #FFF7DA; font-weight: 600; text-decoration: none; }
.side-link:hover { background: rgba(255,255,255,.08); }
.side-link.router-link-exact-active { background: var(--color-turmeric); color: var(--color-char); box-shadow: 0 3px 0 #A67B00; }
</style>
