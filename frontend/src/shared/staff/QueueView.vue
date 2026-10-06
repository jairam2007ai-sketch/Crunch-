<script setup>
// What to make next. New online orders arrive here with a beep.
import { computed, inject, onMounted, ref } from 'vue'
import OrderItems from '../components/OrderItems.vue'
import { METHOD, PAYMENT, ago, clock, inr } from '../format'
import { useMenu } from '../menu'
import { toast, toastError } from '../toast'
const { api, live, refreshActive, refreshToday } = inject('staff')

const { names } = useMenu()
const done = ref([])
const showDone = ref(false)
const cancelling = ref(null)
const reason = ref('')
const busyId = ref(null)

const COLUMNS = [
  { status: 'placed', title: 'New', empty: 'No new orders.', next: 'preparing', action: 'Start making' },
  { status: 'preparing', title: 'Making', empty: 'Nothing being made.', next: 'ready', action: 'Ready' },
  { status: 'ready', title: 'Ready to collect', empty: 'Nothing waiting.', next: 'completed', action: 'Collected' },
]
const byStatus = computed(() => Object.fromEntries(COLUMNS.map((c) => [c.status, live.active.filter((o) => o.status === c.status).slice().reverse()])))

async function loadDone() {
  try { done.value = await api.get('/api/orders?status=completed,cancelled') } catch (e) { toastError(e) }
}
onMounted(() => { refreshActive().catch(() => {}); loadDone() })

async function act(fn, id) {
  busyId.value = id
  try { await fn(); await refreshActive(); refreshToday().catch(() => {}); loadDone() } catch (e) { toastError(e) } finally { busyId.value = null }
}
const move = (o, status) => act(() => api.patch(`/api/orders/${o.id}/status`, { status }), o.id)
const pay = (o, method) => act(async () => { await api.post(`/api/orders/${o.id}/pay`, { method }); toast(`Order ${o.number} marked paid by ${METHOD[method]}.`) }, o.id)
function cancel(o) {
  act(async () => {
    await api.patch(`/api/orders/${o.id}/status`, { status: 'cancelled', reason: reason.value })
    toast(`Order ${o.number} cancelled.`)
    cancelling.value = null
    reason.value = ''
  }, o.id)
}
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-5">
    <div class="grid gap-5 lg:grid-cols-3">
      <section v-for="c in COLUMNS" :key="c.status" class="rounded-2xl bg-sunk p-3" :aria-labelledby="`col-${c.status}`">
        <h2 :id="`col-${c.status}`" class="m-0 mb-3 flex items-center gap-2 px-1 font-display text-xl font-extrabold">
          {{ c.title }} <span class="pill bg-white text-ink-2 tabular-nums">{{ byStatus[c.status].length }}</span>
        </h2>
        <p v-if="!byStatus[c.status].length" class="m-0 rounded-xl border-2 border-dashed border-line px-4 py-6 text-center text-ink-3">{{ c.empty }}</p>
        <ul class="m-0 grid list-none gap-3 p-0">
          <li v-for="o in byStatus[c.status]" :key="o.id" class="card p-4" :class="o.source === 'online' && o.status === 'placed' ? 'ring-2 ring-sky' : ''">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="m-0 font-display text-3xl font-extrabold leading-none">#{{ o.number }}</p>
                <p class="m-0 mt-1 text-sm text-ink-2">
                  <span class="pill mr-1" :class="o.source === 'online' ? 'bg-sky-soft text-sky' : 'bg-sunk text-ink-2'">{{ o.source === 'online' ? 'Online' : 'Counter' }}</span>
                  {{ clock(o.created_at) }} · {{ ago(o.created_at) }}
                </p>
              </div>
              <div class="text-right">
                <p class="m-0 font-display text-xl font-bold tabular-nums">{{ inr(o.total_amount) }}</p>
                <span class="pill" :class="PAYMENT[o.payment_status].cls">{{ PAYMENT[o.payment_status].label }}{{ o.payment_status === 'unpaid' && o.payment_method === 'upi' ? ' · UPI' : '' }}</span>
              </div>
            </div>
            <p v-if="o.customer_name" class="m-0 mt-2 font-semibold">{{ o.customer_name }}<span v-if="o.customer_phone" class="font-normal text-ink-2"> · {{ o.customer_phone }}</span></p>
            <div class="mt-3"><OrderItems :items="o.items" :names="names" :prices="false" /></div>
            <p v-if="o.note" class="m-0 mt-2 rounded-lg bg-amber-soft px-3 py-1.5 text-sm font-semibold text-amber">Note: {{ o.note }}</p>

            <div class="mt-3 flex flex-wrap items-center gap-2 pb-1">
              <button class="btn btn-dark btn-sm" type="button" :disabled="busyId === o.id" @click="move(o, c.next)">{{ c.action }}</button>
              <template v-if="o.payment_status === 'unpaid'">
                <button class="btn btn-light btn-sm" type="button" :disabled="busyId === o.id" @click="pay(o, 'cash')">Paid cash</button>
                <button class="btn btn-light btn-sm" type="button" :disabled="busyId === o.id" @click="pay(o, 'upi')">Paid UPI</button>
              </template>
              <button v-if="o.payment_status === 'unpaid' && cancelling !== o.id" class="ml-auto text-sm font-semibold text-chili underline" type="button" @click="cancelling = o.id">Cancel</button>
            </div>
            <form v-if="cancelling === o.id" class="mt-2 grid gap-2 rounded-xl bg-chili-soft p-3" @submit.prevent="cancel(o)">
              <label class="label m-0" :for="`why-${o.id}`">Why cancel order {{ o.number }}?</label>
              <input :id="`why-${o.id}`" v-model="reason" class="field" maxlength="200" placeholder="e.g. customer didn't come" />
              <div class="flex gap-2">
                <button class="btn btn-red btn-sm" type="submit">Cancel order</button>
                <button class="btn btn-light btn-sm" type="button" @click="cancelling = null">Keep it</button>
              </div>
            </form>
          </li>
        </ul>
      </section>
    </div>

    <section class="mt-6">
      <button class="btn btn-light btn-sm" type="button" :aria-expanded="showDone" @click="showDone = !showDone">
        {{ showDone ? 'Hide' : 'Show' }} finished today ({{ done.length }})
      </button>
      <ul v-if="showDone" class="card m-0 mt-3 list-none divide-y divide-line p-0">
        <li v-for="o in done" :key="o.id" class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 text-sm">
          <b class="w-12 font-display text-lg">#{{ o.number }}</b>
          <span class="w-20 text-ink-2">{{ clock(o.created_at) }}</span>
          <span class="pill" :class="o.status === 'cancelled' ? 'bg-chili-soft text-chili' : 'bg-sunk text-ink-2'">{{ o.status === 'cancelled' ? 'Cancelled' : 'Collected' }}</span>
          <span class="flex-1 text-ink-2">{{ o.items.map((i) => `${i.quantity}× ${i.product_name}`).join(', ') }}</span>
          <span class="font-semibold tabular-nums">{{ inr(o.total_amount) }}</span>
        </li>
        <li v-if="!done.length" class="px-4 py-3 text-ink-3">Nothing finished yet today.</li>
      </ul>
    </section>
  </main>
</template>
