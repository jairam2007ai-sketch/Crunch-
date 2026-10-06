<script setup>
// Sellers ask for a refund; the owner approves it from the admin site.
import { onMounted, reactive, ref } from 'vue'
import OrderItems from '../../shared/components/OrderItems.vue'
import { PAYMENT, clock, dayLabel, inr, todayYmd } from '../../shared/format'
import { useMenu } from '../../shared/menu'
import { toast, toastError } from '../../shared/toast'
import { api } from '../store'

const { names } = useMenu()
const find = reactive({ number: '', date: todayYmd() })
const order = ref(null)
const refundable = ref(0)
const form = reactive({ amount: '', method: 'cash', reason: '' })
const list = ref([])
const busy = ref(false)
const error = ref('')

async function loadList() {
  try { list.value = await api.get('/api/refunds?limit=30') } catch (e) { toastError(e) }
}
onMounted(loadList)

async function lookup() {
  error.value = ''
  order.value = null
  try {
    const res = await api.get(`/api/orders?date=${find.date}&number=${Number(find.number)}`)
    if (!res.length) { error.value = `No order ${find.number} on ${dayLabel(find.date)}.`; return }
    order.value = res[0]
    refundable.value = (await api.get(`/api/refunds/refundable/${order.value.id}`)).refundable
    form.amount = String(refundable.value)
    form.method = order.value.payment_method === 'upi' ? 'upi' : 'cash'
  } catch (e) { error.value = e.message }
}

async function submit() {
  busy.value = true
  try {
    const r = await api.post('/api/refunds', { order_id: order.value.id, amount: Number(form.amount), method: form.method, reason: form.reason })
    toast(r.status === 'approved' ? `Refund of ${inr(r.amount)} done.` : `Refund of ${inr(r.amount)} sent to the owner for approval.`)
    order.value = null
    find.number = ''
    form.reason = ''
    loadList()
  } catch (e) { toastError(e) } finally { busy.value = false }
}
const STATUS = { pending: 'bg-amber-soft text-amber', approved: 'bg-leaf-soft text-leaf', rejected: 'bg-chili-soft text-chili' }
</script>

<template>
  <main class="mx-auto grid max-w-6xl items-start gap-5 px-4 py-5 lg:grid-cols-2">
    <section class="card p-5" aria-labelledby="rf-h">
      <h2 id="rf-h" class="m-0 font-display text-2xl font-extrabold">Ask for a refund</h2>
      <p class="m-0 mt-1 text-ink-2">Find the paid order first. The owner approves refunds before they count.</p>
      <form class="mt-4 flex flex-wrap items-end gap-3" @submit.prevent="lookup">
        <div>
          <label class="label" for="rf-num">Order number</label>
          <input id="rf-num" v-model="find.number" class="field w-28" type="number" min="1" inputmode="numeric" required />
        </div>
        <div>
          <label class="label" for="rf-date">Date</label>
          <input id="rf-date" v-model="find.date" class="field" type="date" required />
        </div>
        <button class="btn btn-dark btn-sm" type="submit">Find order</button>
      </form>
      <p v-if="error" class="error-box mt-3">{{ error }}</p>

      <div v-if="order" class="mt-5 rounded-xl border border-line p-4">
        <div class="flex items-start justify-between">
          <p class="m-0 font-display text-2xl font-extrabold">#{{ order.number }} <span class="text-base font-semibold text-ink-2">{{ clock(order.created_at) }}</span></p>
          <span class="pill" :class="PAYMENT[order.payment_status].cls">{{ PAYMENT[order.payment_status].label }}</span>
        </div>
        <div class="mt-2"><OrderItems :items="order.items" :names="names" /></div>
        <p class="m-0 mt-3 text-sm text-ink-2">Total {{ inr(order.total_amount) }} · up to <b class="text-ink">{{ inr(refundable) }}</b> can be refunded.</p>
        <form v-if="refundable > 0" class="mt-4 grid gap-3" @submit.prevent="submit">
          <div class="flex flex-wrap gap-3">
            <div>
              <label class="label" for="rf-amt">Amount (₹)</label>
              <input id="rf-amt" v-model="form.amount" class="field w-28" type="number" min="1" :max="refundable" required />
            </div>
            <div>
              <span class="label">Give back by</span>
              <div class="flex gap-2">
                <button class="key key-sm" type="button" :aria-pressed="form.method === 'cash'" @click="form.method = 'cash'">Cash</button>
                <button class="key key-sm" type="button" :aria-pressed="form.method === 'upi'" @click="form.method = 'upi'">UPI</button>
              </div>
            </div>
          </div>
          <div>
            <label class="label" for="rf-why">Reason</label>
            <input id="rf-why" v-model="form.reason" class="field" minlength="3" maxlength="200" required placeholder="e.g. wrong toppings, packet spilled" />
          </div>
          <button class="btn btn-red justify-self-start" type="submit" :disabled="busy">Send refund request</button>
        </form>
      </div>
    </section>

    <section class="card p-5" aria-labelledby="rl-h">
      <h2 id="rl-h" class="m-0 font-display text-2xl font-extrabold">Recent refunds</h2>
      <p v-if="!list.length" class="m-0 mt-3 text-ink-3">No refunds yet.</p>
      <ul class="m-0 mt-3 grid list-none gap-0 divide-y divide-line p-0">
        <li v-for="r in list" :key="r.id" class="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5">
          <b class="font-display text-lg">#{{ r.order_number }}</b>
          <span class="text-sm text-ink-2">{{ dayLabel(r.order_date) }}</span>
          <span class="flex-1 text-sm">{{ r.reason }}</span>
          <span class="font-semibold tabular-nums">{{ inr(r.amount) }}</span>
          <span class="pill capitalize" :class="STATUS[r.status]">{{ r.status }}</span>
        </li>
      </ul>
    </section>
  </main>
</template>
