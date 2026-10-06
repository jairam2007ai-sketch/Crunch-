<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import OrderItems from '../../shared/components/OrderItems.vue'
import { METHOD, PAYMENT, STATUS, clock, describe, inr, todayYmd } from '../../shared/format'
import { useMenu } from '../../shared/menu'
import { toast, toastError } from '../../shared/toast'
import { api } from '../store'

const { names } = useMenu()
const filters = reactive({ date: todayYmd(), status: '', source: '' })
const orders = ref([])
const loading = ref(false)
const selected = ref(null)
const refund = reactive({ amount: '', method: 'upi', reason: '' })

async function load() {
  loading.value = true
  try {
    const q = new URLSearchParams({ date: filters.date })
    if (filters.status) q.set('status', filters.status)
    if (filters.source) q.set('source', filters.source)
    orders.value = await api.get(`/api/orders?${q}`)
    if (selected.value) selected.value = orders.value.find((o) => o.id === selected.value.id) || null
  } catch (e) { toastError(e) } finally { loading.value = false }
}
onMounted(load)
watch(filters, load)

const totals = computed(() => {
  const live = orders.value.filter((o) => o.status !== 'cancelled')
  return { count: live.length, paid: live.filter((o) => o.payment_status !== 'unpaid').reduce((n, o) => n + o.total_amount, 0) }
})

function open(o) {
  selected.value = o
  refund.amount = String(o.total_amount - o.refunded_amount)
  refund.method = o.payment_method === 'cash' ? 'cash' : 'upi'
  refund.reason = ''
}
async function setStatus(o, status) {
  try { await api.patch(`/api/orders/${o.id}/status`, { status, reason: 'Changed by owner' }); toast(`Order ${o.number} is now ${STATUS[status].label.toLowerCase()}.`); load() } catch (e) { toastError(e) }
}
async function markPaid(o, method) {
  try { await api.post(`/api/orders/${o.id}/pay`, { method }); toast(`Order ${o.number} marked paid.`); load() } catch (e) { toastError(e) }
}
async function doRefund(o) {
  try {
    await api.post('/api/refunds', { order_id: o.id, amount: Number(refund.amount), method: refund.method, reason: refund.reason })
    toast(`Refunded ${inr(refund.amount)} on order ${o.number}.`)
    load()
  } catch (e) { toastError(e) }
}
</script>

<template>
  <div class="mx-auto max-w-7xl">
    <h1 class="m-0 mb-4 font-display text-3xl font-extrabold">Orders</h1>
    <div class="mb-4 flex flex-wrap items-end gap-3">
      <div><label class="label" for="o-date">Date</label><input id="o-date" v-model="filters.date" class="field" type="date" /></div>
      <div>
        <label class="label" for="o-status">Status</label>
        <select id="o-status" v-model="filters.status" class="field">
          <option value="">All</option>
          <option v-for="(s, k) in STATUS" :key="k" :value="k">{{ s.label }}</option>
        </select>
      </div>
      <div>
        <label class="label" for="o-src">Where from</label>
        <select id="o-src" v-model="filters.source" class="field">
          <option value="">Both</option><option value="counter">Counter</option><option value="online">Online</option>
        </select>
      </div>
      <p class="m-0 ml-auto pb-2 text-sm text-ink-2 tabular-nums">{{ totals.count }} orders · {{ inr(totals.paid) }} paid</p>
    </div>

    <div class="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div class="card overflow-x-auto">
        <table class="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr class="border-b border-line text-left text-xs uppercase tracking-wider text-ink-3">
              <th class="px-4 py-3">No.</th><th class="px-2 py-3">Time</th><th class="px-2 py-3">From</th><th class="px-2 py-3">Packets</th>
              <th class="px-2 py-3 text-right">Total</th><th class="px-2 py-3">Payment</th><th class="px-2 py-3">Status</th><th class="px-4 py-3">By</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in orders" :key="o.id" class="cursor-pointer border-b border-line last:border-0 hover:bg-paper"
                :class="selected?.id === o.id ? 'bg-turmeric-soft' : ''" tabindex="0" @click="open(o)" @keydown.enter="open(o)">
              <td class="px-4 py-2.5 font-display text-base font-bold">{{ o.number }}</td>
              <td class="px-2 py-2.5 tabular-nums text-ink-2">{{ clock(o.created_at) }}</td>
              <td class="px-2 py-2.5"><span class="pill" :class="o.source === 'online' ? 'bg-sky-soft text-sky' : 'bg-sunk text-ink-2'">{{ o.source === 'online' ? 'Online' : 'Counter' }}</span></td>
              <td class="max-w-[260px] truncate px-2 py-2.5 text-ink-2" :title="o.items.map((i) => describe(i.selections, names)).join(' / ')">
                {{ o.items.map((i) => `${i.quantity}× ${i.product_name}`).join(', ') }}
              </td>
              <td class="px-2 py-2.5 text-right font-semibold tabular-nums">{{ inr(o.total_amount) }}</td>
              <td class="px-2 py-2.5"><span class="pill" :class="PAYMENT[o.payment_status].cls">{{ PAYMENT[o.payment_status].label }}</span> <span class="text-xs text-ink-3">{{ METHOD[o.payment_method] }}</span></td>
              <td class="px-2 py-2.5"><span class="pill" :class="STATUS[o.status].cls">{{ STATUS[o.status].label }}</span></td>
              <td class="px-4 py-2.5 text-ink-2">{{ o.created_by_name || o.customer_name || '—' }}</td>
            </tr>
            <tr v-if="!orders.length && !loading"><td colspan="8" class="px-4 py-8 text-center text-ink-3">No orders on this day.</td></tr>
          </tbody>
        </table>
      </div>

      <aside v-if="selected" class="card grid gap-4 p-5 xl:sticky xl:top-6" aria-label="Order details">
        <div class="flex items-start justify-between">
          <div>
            <p class="m-0 font-display text-4xl font-extrabold leading-none">#{{ selected.number }}</p>
            <p class="m-0 mt-1 text-sm text-ink-2">{{ clock(selected.created_at) }} · {{ selected.source === 'online' ? 'Online' : 'Counter' }}<template v-if="selected.created_by_name"> · {{ selected.created_by_name }}</template></p>
          </div>
          <button class="btn btn-light btn-sm" type="button" @click="selected = null">Close</button>
        </div>
        <p v-if="selected.customer_name" class="m-0"><b>{{ selected.customer_name }}</b> <span v-if="selected.customer_phone" class="text-ink-2">· {{ selected.customer_phone }}</span></p>
        <OrderItems :items="selected.items" :names="names" />
        <p v-if="selected.note" class="m-0 rounded-lg bg-amber-soft px-3 py-2 text-sm text-amber">Note: {{ selected.note }}</p>
        <p v-if="selected.cancel_reason" class="m-0 text-sm text-ink-2">Cancelled: {{ selected.cancel_reason }}</p>
        <div class="flex justify-between border-t border-line pt-3 font-semibold">
          <span>Total <span class="pill ml-1" :class="PAYMENT[selected.payment_status].cls">{{ PAYMENT[selected.payment_status].label }}</span></span>
          <span class="tabular-nums">{{ inr(selected.total_amount) }}</span>
        </div>
        <p v-if="selected.refunded_amount" class="m-0 text-sm text-chili">Refunded {{ inr(selected.refunded_amount) }}</p>

        <div v-if="['placed', 'preparing', 'ready'].includes(selected.status)" class="flex flex-wrap gap-2 pb-1">
          <button v-if="selected.status === 'placed'" class="btn btn-light btn-sm" @click="setStatus(selected, 'preparing')">Start making</button>
          <button v-if="selected.status !== 'ready'" class="btn btn-light btn-sm" @click="setStatus(selected, 'ready')">Ready</button>
          <button class="btn btn-light btn-sm" @click="setStatus(selected, 'completed')">Collected</button>
          <button v-if="selected.payment_status === 'unpaid'" class="btn btn-light btn-sm text-chili" @click="setStatus(selected, 'cancelled')">Cancel</button>
        </div>
        <div v-if="selected.payment_status === 'unpaid' && selected.status !== 'cancelled'" class="flex gap-2 pb-1">
          <button class="btn btn-green btn-sm" @click="markPaid(selected, 'cash')">Paid cash</button>
          <button class="btn btn-green btn-sm" @click="markPaid(selected, 'upi')">Paid UPI</button>
        </div>

        <form v-if="['paid', 'partially_refunded'].includes(selected.payment_status)" class="grid gap-2 rounded-xl bg-sunk p-3" @submit.prevent="doRefund(selected)">
          <p class="m-0 font-semibold">Refund this order</p>
          <div class="flex gap-2">
            <input v-model="refund.amount" class="field w-24" type="number" min="1" aria-label="Refund amount in rupees" required />
            <select v-model="refund.method" class="field w-28" aria-label="Refund method"><option value="upi">UPI</option><option value="cash">Cash</option></select>
          </div>
          <input v-model="refund.reason" class="field" minlength="3" maxlength="200" placeholder="Reason" aria-label="Refund reason" required />
          <button class="btn btn-red btn-sm justify-self-start" type="submit">Refund now</button>
        </form>
      </aside>
    </div>
  </div>
</template>
