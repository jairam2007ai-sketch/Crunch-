<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { publicApi } from '../shared/api'
import LoginCard from '../shared/components/LoginCard.vue'
import ToastStack from '../shared/components/ToastStack.vue'
import { inr } from '../shared/format'
import { loadMenu } from '../shared/menu'
import { poll, toast, toastError } from '../shared/toast'
import { api, live, refreshActive, refreshToday, session } from './store'

const signedIn = computed(() => !!session.state.token)
const toggling = ref(false)
const freshInstall = ref(false)
let stops = []
publicApi.get('/api/setup/status').then((s) => { freshInstall.value = s.needs_owner }).catch(() => {})

function start() {
  loadMenu(true).catch(() => {})
  refreshActive().catch(() => {})
  refreshToday().catch(() => {})
  stops = [poll(() => refreshActive().catch(() => {}), 5000), poll(() => refreshToday().catch(() => {}), 30000)]
}
function stop() { stops.forEach((s) => s()); stops = []; live.loaded = false }
watch(signedIn, (v) => (v ? start() : stop()), { immediate: true })
onBeforeUnmount(stop)

const newCount = computed(() => live.active.filter((o) => o.status === 'placed').length)
const s = computed(() => live.today?.summary)

async function toggleOpen() {
  toggling.value = true
  try {
    const res = await api.post('/api/settings/open', { is_open: !live.today?.is_open })
    live.today.is_open = res.is_open
    toast(res.is_open ? 'Online ordering is open.' : 'Online ordering is closed.')
  } catch (e) { toastError(e) } finally { toggling.value = false }
}

const NAV = [
  { to: '/', label: 'New order' },
  { to: '/queue', label: 'Queue' },
  { to: '/refunds', label: 'Refunds' },
  { to: '/stock', label: 'Stock' },
]
</script>

<template>
  <LoginCard v-if="!signedIn" :session="session" title="Seller sign in" subtitle="For the team at the cart"
             :notice="freshInstall ? 'No accounts exist yet. The owner needs to open the admin site (/admin/) first, then add sellers on the Team page.' : ''" />
  <template v-else>
    <header class="sticky top-0 z-40 bg-char text-[#FFF7DA] shadow-[0_10px_20px_-12px_rgba(0,0,0,.6)]">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
        <span class="mini-lock" aria-label="Crunch seller"><span class="a">Customize Your</span><span class="b">CRUNCH</span></span>
        <span class="pill bg-leaf text-white">Seller</span>
        <nav class="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto" aria-label="Seller screens">
          <RouterLink v-for="n in NAV" :key="n.to" :to="n.to" class="nav-link">
            {{ n.label }}
            <span v-if="n.to === '/queue' && newCount" class="ml-1 rounded-full bg-chili px-1.5 text-xs text-white tabular-nums">{{ newCount }}</span>
          </RouterLink>
        </nav>
        <div class="ml-auto flex items-center gap-2">
          <button v-if="live.today" class="btn btn-sm" :class="live.today.is_open ? 'btn-green' : 'btn-red'" type="button" :disabled="toggling" @click="toggleOpen"
                  :title="live.today.is_open ? 'Tap to stop online orders' : 'Tap to start taking online orders'">
            Online: {{ live.today.is_open ? 'Open' : 'Closed' }}
          </button>
          <span class="hidden text-sm md:inline">{{ session.state.user?.name }}</span>
          <button class="btn btn-light btn-sm" type="button" @click="session.logout()">Sign out</button>
        </div>
      </div>
    </header>
    <div v-if="s" class="border-b border-line bg-turmeric-soft">
      <p class="mx-auto m-0 flex max-w-7xl flex-wrap gap-x-6 gap-y-1 px-4 py-2 text-sm tabular-nums">
        <span><b>Today:</b> {{ s.packets }} packets · {{ inr(s.revenue) }} collected</span>
        <span>Cash {{ inr(s.by_payment.cash) }} · UPI {{ inr(s.by_payment.upi) }}</span>
        <span v-if="s.unpaid_orders" class="font-semibold text-amber">{{ s.unpaid_orders }} unpaid ({{ inr(s.unpaid_amount) }})</span>
        <span class="text-ink-2">Goal {{ live.today.target.min }}–{{ live.today.target.max }} packets</span>
      </p>
    </div>
    <RouterView />
  </template>
  <ToastStack />
</template>

<style scoped>
.nav-link { padding: .35rem .8rem; border-radius: 999px; font-weight: 600; font-size: .95rem; color: #FFF7DA; text-decoration: none; white-space: nowrap; }
.nav-link:hover { background: rgba(255,255,255,.1); }
.nav-link.router-link-exact-active { background: var(--color-turmeric); color: var(--color-char); }
</style>
