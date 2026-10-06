<script setup>
// Who did what: every sign-in, order change, refund, price and stock change.
import { onMounted, ref, watch } from 'vue'
import { inr } from '../../shared/format'
import { toastError } from '../../shared/toast'
import { api } from '../store'

const rows = ref([])
const filter = ref('')
const more = ref(true)

const FILTERS = [['', 'Everything'], ['order', 'Orders'], ['refund', 'Refunds'], ['stock', 'Stock'], ['product', 'Prices'], ['user', 'Team'], ['auth', 'Sign-ins'], ['ai', 'Assistant actions'], ['settings', 'Settings'], ['shop', 'Open / close']]

async function load(append = false) {
  try {
    const q = new URLSearchParams({ limit: '100' })
    if (filter.value) q.set('action', filter.value)
    if (append && rows.value.length) q.set('before_id', String(rows.value[rows.value.length - 1].id))
    const page = await api.get(`/api/audit-logs?${q}`)
    rows.value = append ? [...rows.value, ...page] : page
    more.value = page.length === 100
  } catch (e) { toastError(e) }
}
onMounted(() => load())
watch(filter, () => load())

function describeRow(r) {
  const n = r.new || {}, o = r.old || {}
  switch (r.action) {
    case 'auth.login': return 'Signed in'
    case 'order.create': return `Order ${n.number} created, ${inr(n.total)} (${n.source})`
    case 'order.status': return `Order moved from ${o.status} to ${n.status}${n.reason ? ` (${n.reason})` : ''}`
    case 'order.paid': return `Marked paid by ${String(n.method).toUpperCase()}, ${inr(n.amount)}`
    case 'refund.request': return `Asked for ${inr(n.amount)} refund on order ${n.order}: ${n.reason}`
    case 'refund.approve': return `Approved ${inr(n.amount)} refund on order ${n.order}`
    case 'refund.reject': return `Rejected refund on order ${n.order}`
    case 'shop.open': return 'Opened online ordering'
    case 'shop.close': return 'Closed online ordering'
    case 'ai.action': return `Assistant action confirmed: ${n.result}`
    default:
      if (r.action.startsWith('stock.')) return `Stock ${r.action.slice(6)}: ${o.stock ?? '?'} → ${n.stock} portions${n.note ? ` (${n.note})` : ''}`
      return `${r.action} ${r.entity_type} ${r.entity_id}: ${Object.entries(n).map(([k, v]) => `${k} → ${v}`).join(', ')}`
  }
}
const when = (iso) => new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="m-0 font-display text-3xl font-extrabold">Activity</h1>
    <p class="m-0 mb-4 text-ink-2">A record of every change, so you always know who did what.</p>
    <div class="mb-4 flex flex-wrap gap-2" role="group" aria-label="Show">
      <button v-for="[k, label] in FILTERS" :key="k" class="key key-sm" type="button" :aria-pressed="filter === k" @click="filter = k">{{ label }}</button>
    </div>
    <ul class="card m-0 list-none divide-y divide-line p-0">
      <li v-for="r in rows" :key="r.id" class="grid gap-x-4 gap-y-0.5 px-4 py-3 text-sm sm:grid-cols-[150px_120px_1fr]">
        <span class="tabular-nums text-ink-3">{{ when(r.created_at) }}</span>
        <span class="font-semibold">{{ r.user || 'Customer' }}</span>
        <span>{{ describeRow(r) }}</span>
      </li>
      <li v-if="!rows.length" class="px-4 py-6 text-center text-ink-3">Nothing here yet.</li>
    </ul>
    <button v-if="more && rows.length" class="btn btn-light btn-sm mt-4" type="button" @click="load(true)">Show older</button>
  </div>
</template>
