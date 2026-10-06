<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { dayLabel, inr } from '../../shared/format'
import { poll, toast, toastError } from '../../shared/toast'
import AreaChart from '../components/AreaChart.vue'
import BarList from '../components/BarList.vue'
import ColumnChart from '../components/ColumnChart.vue'
import { api, badges } from '../store'

const data = ref(null)
const error = ref('')
let stop = null

async function load() {
  try { data.value = await api.get('/api/dashboard/summary?days=14'); error.value = '' } catch (e) { error.value = e.message }
}
onMounted(() => { load(); stop = poll(load, 30000) })
onBeforeUnmount(() => stop?.())

const t = computed(() => data.value?.today)
const delta = computed(() => {
  const a = data.value?.today.revenue, b = data.value?.yesterday.revenue
  if (a == null || !b) return null
  return Math.round(((a - b) / b) * 100)
})
const meter = computed(() => {
  if (!data.value) return null
  const { min, max } = data.value.target
  const scale = Math.max(max * 1.4, t.value.packets, 1)
  return { min, max, scale, fill: Math.min(100, (t.value.packets / scale) * 100), lo: (min / scale) * 100, hi: (max / scale) * 100 }
})
const series = computed(() => (data.value?.series || []).map((d) => ({
  key: d.date, value: d.revenue, label: dayLabel(d.date, { day: 'numeric', month: 'short' }),
  title: dayLabel(d.date, { weekday: 'long', day: 'numeric', month: 'long' }), extra: `${d.orders} orders · ${d.packets} packets`,
})))
const hours = computed(() => {
  const h = data.value?.hourly || []
  const active = h.filter((x) => x.orders > 0).map((x) => x.hour)
  const from = Math.min(10, ...active), to = Math.max(22, ...active)
  const fmt = (x) => (x === 0 ? '12a' : x < 12 ? `${x}a` : x === 12 ? '12p' : `${x - 12}p`)
  return h.filter((x) => x.hour >= from && x.hour <= to).map((x) => ({
    key: x.hour, value: x.orders, label: fmt(x.hour), title: `${fmt(x.hour)}–${fmt((x.hour + 1) % 24)} · ${inr(x.revenue)}`,
  }))
})
const productRows = computed(() => {
  const bp = data.value?.last_7_days.by_product || {}
  return [['regular', 'Regular', '#1E6E3A'], ['loaded', 'Loaded', '#C2302A']].map(([k, name, color]) => ({
    key: k, name, color, value: bp[k]?.packets || 0, revenue: bp[k]?.revenue || 0,
  }))
})
const topRows = (cat) => (data.value?.top[cat] || []).map((r) => ({ key: r.code, name: r.name, value: r.count }))

async function toggleOpen() {
  try {
    const res = await api.post('/api/settings/open', { is_open: !data.value.is_open })
    data.value.is_open = res.is_open
    badges.isOpen = res.is_open
    toast(res.is_open ? 'Online ordering is open.' : 'Online ordering is closed.')
  } catch (e) { toastError(e) }
}
</script>

<template>
  <div class="mx-auto max-w-7xl">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="eyebrow m-0">Dashboard</p>
        <h1 class="m-0 font-display text-3xl font-extrabold">{{ data ? dayLabel(data.date, { weekday: 'long', day: 'numeric', month: 'long' }) : 'Today' }}</h1>
      </div>
      <div v-if="data" class="flex flex-wrap gap-2 pb-1">
        <button class="btn btn-sm" :class="data.is_open ? 'btn-green' : 'btn-red'" type="button" @click="toggleOpen">
          Online ordering: {{ data.is_open ? 'Open' : 'Closed' }}
        </button>
        <RouterLink to="/assistant" class="btn btn-dark btn-sm">Ask the assistant</RouterLink>
      </div>
    </div>
    <p v-if="error" class="error-box">{{ error }}</p>
    <p v-if="!data && !error" class="text-ink-2">Loading today's numbers…</p>

    <template v-if="data">
      <!-- summary first -->
      <section class="card grid gap-6 p-5 md:grid-cols-[minmax(0,1.1fr)_minmax(0,2fr)]" aria-label="Today">
        <div>
          <p class="m-0 text-sm font-semibold text-ink-2">Sales collected today</p>
          <p class="m-0 font-display text-6xl font-extrabold leading-none">{{ inr(t.revenue) }}</p>
          <p v-if="delta !== null" class="m-0 mt-2 text-sm font-semibold" :class="delta >= 0 ? 'text-leaf' : 'text-chili'">
            {{ delta >= 0 ? '▲' : '▼' }} {{ Math.abs(delta) }}% vs yesterday ({{ inr(data.yesterday.revenue) }})
          </p>
          <p v-else class="m-0 mt-2 text-sm text-ink-3">No sales yesterday to compare with.</p>
          <div v-if="meter" class="mt-5">
            <div class="flex justify-between text-sm"><span class="font-semibold">{{ t.packets }} packets</span><span class="text-ink-2">Goal {{ meter.min }}–{{ meter.max }}</span></div>
            <div class="relative mt-1.5 h-3 overflow-hidden rounded-full bg-[#F2E3B0]" role="meter" :aria-valuenow="t.packets" aria-valuemin="0" :aria-valuemax="meter.scale" aria-label="Packets sold against today's goal">
              <span class="absolute inset-y-0 bg-[#E8D08A]" :style="{ left: meter.lo + '%', width: meter.hi - meter.lo + '%' }" />
              <span class="absolute inset-y-0 left-0 rounded-full bg-turmeric-deep" :style="{ width: meter.fill + '%' }" />
            </div>
          </div>
        </div>
        <dl class="m-0 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          <div><dt class="text-sm text-ink-2">Orders</dt><dd class="m-0 font-display text-2xl font-bold">{{ t.orders }}</dd><dd class="m-0 text-xs text-ink-3">{{ t.online_orders }} online · {{ t.counter_orders }} counter</dd></div>
          <div><dt class="text-sm text-ink-2">Cash</dt><dd class="m-0 font-display text-2xl font-bold">{{ inr(t.by_payment.cash) }}</dd></div>
          <div><dt class="text-sm text-ink-2">UPI</dt><dd class="m-0 font-display text-2xl font-bold">{{ inr(t.by_payment.upi) }}</dd></div>
          <div><dt class="text-sm text-ink-2">Refunds</dt><dd class="m-0 font-display text-2xl font-bold">{{ inr(t.refunds) }}</dd><dd class="m-0 text-xs text-ink-3">Net {{ inr(t.net_sales) }}</dd></div>
          <div><dt class="text-sm text-ink-2">Average order</dt><dd class="m-0 font-display text-2xl font-bold">{{ inr(t.avg_order) }}</dd></div>
          <div>
            <dt class="text-sm text-ink-2">Profit (estimate)</dt>
            <dd v-if="t.profit !== null" class="m-0 font-display text-2xl font-bold">{{ inr(t.profit) }}</dd>
            <dd v-else class="m-0 text-sm"><RouterLink to="/menu" class="font-semibold underline decoration-turmeric decoration-2">Set cost per packet</RouterLink> to see it</dd>
          </div>
        </dl>
      </section>

      <!-- what needs attention -->
      <section v-if="data.pending_refunds || t.unpaid_orders || data.low_stock.length" class="mt-4 grid gap-3 md:grid-cols-3" aria-label="Needs attention">
        <RouterLink v-if="data.pending_refunds" to="/refunds" class="card flex items-center gap-3 border-l-4 border-l-chili p-4 no-underline">
          <span class="pill bg-chili-soft text-chili">Action</span>
          <span><b>{{ data.pending_refunds }}</b> {{ data.pending_refunds === 1 ? 'refund needs' : 'refunds need' }} your approval</span>
        </RouterLink>
        <div v-if="t.unpaid_orders" class="card flex items-center gap-3 border-l-4 border-l-amber p-4">
          <span class="pill bg-amber-soft text-amber">Unpaid</span>
          <span><b>{{ t.unpaid_orders }}</b> {{ t.unpaid_orders === 1 ? 'order' : 'orders' }}, {{ inr(t.unpaid_amount) }} still to collect</span>
        </div>
        <RouterLink v-if="data.low_stock.length" to="/stock" class="card flex items-center gap-3 border-l-4 border-l-amber p-4 no-underline">
          <span class="pill bg-amber-soft text-amber">Low stock</span>
          <span>{{ data.low_stock.map((i) => i.name).join(', ') }}</span>
        </RouterLink>
      </section>

      <div class="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section class="card p-5" aria-labelledby="sales-h">
          <h2 id="sales-h" class="m-0 font-display text-xl font-bold">Sales collected, last 14 days</h2>
          <p class="m-0 mb-3 text-sm text-ink-2">Paid orders only. Hover a day for its orders.</p>
          <AreaChart :points="series" :format="inr" caption="Sales collected per day for the last 14 days" />
        </section>
        <section class="card p-5" aria-labelledby="hour-h">
          <h2 id="hour-h" class="m-0 font-display text-xl font-bold">Orders by hour today</h2>
          <p class="m-0 mb-3 text-sm text-ink-2">When the cart is busiest.</p>
          <ColumnChart :bars="hours" :format="(v) => `${v} ${v === 1 ? 'order' : 'orders'}`" caption="Orders per hour today" />
        </section>
      </div>

      <div class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <section class="card p-5" aria-labelledby="size-h">
          <h2 id="size-h" class="m-0 font-display text-xl font-bold">Regular vs Loaded</h2>
          <p class="m-0 mb-4 text-sm text-ink-2">Packets sold, last 7 days</p>
          <BarList :rows="productRows" :format="(v) => `${v} packets`" />
          <p class="m-0 mt-3 flex flex-wrap gap-x-4 text-xs text-ink-2">
            <span v-for="r in productRows" :key="r.key" class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm" :style="{ background: r.color }" />{{ r.name }} · {{ inr(r.revenue) }}</span>
          </p>
        </section>
        <section class="card p-5" aria-labelledby="top-h">
          <h2 id="top-h" class="m-0 font-display text-xl font-bold">Top toppings</h2>
          <p class="m-0 mb-4 text-sm text-ink-2">Times chosen, last 7 days</p>
          <BarList :rows="topRows('topping')" empty="No orders this week yet." />
        </section>
        <section class="card p-5" aria-labelledby="base-h">
          <h2 id="base-h" class="m-0 font-display text-xl font-bold">Top chips</h2>
          <p class="m-0 mb-4 text-sm text-ink-2">Times chosen, last 7 days</p>
          <BarList :rows="topRows('base')" empty="No orders this week yet." />
        </section>
        <section class="card p-5" aria-labelledby="sauce-h">
          <h2 id="sauce-h" class="m-0 font-display text-xl font-bold">Top sauces</h2>
          <p class="m-0 mb-4 text-sm text-ink-2">Times chosen, last 7 days</p>
          <BarList :rows="topRows('sauce')" empty="No orders this week yet." />
        </section>
        <section class="card p-5" aria-labelledby="mas-h">
          <h2 id="mas-h" class="m-0 font-display text-xl font-bold">Top masalas</h2>
          <p class="m-0 mb-4 text-sm text-ink-2">Times chosen, last 7 days</p>
          <BarList :rows="topRows('seasoning')" empty="No orders this week yet." />
        </section>
        <section class="card p-5" aria-labelledby="wk-h">
          <h2 id="wk-h" class="m-0 font-display text-xl font-bold">Last 7 days</h2>
          <dl class="m-0 mt-3 grid gap-2 text-sm">
            <div class="flex justify-between"><dt class="text-ink-2">Sales collected</dt><dd class="m-0 font-semibold tabular-nums">{{ inr(data.last_7_days.revenue) }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-2">Orders</dt><dd class="m-0 font-semibold tabular-nums">{{ data.last_7_days.orders }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-2">Packets</dt><dd class="m-0 font-semibold tabular-nums">{{ data.last_7_days.packets }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-2">Refunds</dt><dd class="m-0 font-semibold tabular-nums">{{ inr(data.last_7_days.refunds) }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-2">Profit (estimate)</dt><dd class="m-0 font-semibold tabular-nums">{{ data.last_7_days.profit === null ? 'Set costs' : inr(data.last_7_days.profit) }}</dd></div>
          </dl>
        </section>
      </div>
    </template>
  </div>
</template>
