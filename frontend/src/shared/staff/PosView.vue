<script setup>
// Counter sale: build packets, take cash or UPI, and the order joins the queue as "Making".
import { computed, inject, ref } from 'vue'
import PacketBuilder from '../components/PacketBuilder.vue'
import { describe, inr } from '../format'
import { sameBuild, toApiItem, useMenu } from '../menu'
import { toast, toastError } from '../toast'
const { api, refreshActive, refreshToday } = inject('staff')

const { menu, names, product } = useMenu()
const blank = () => ({ size: 'regular', base: menu.data?.ingredients.base.find((i) => i.available)?.code || 'potato', toppings: [], sauces: [], seasonings: [], cheese: false })
const build = ref(blank())
const qty = ref(1)
const lines = ref([])
const last = ref(null)
const payment = ref('cash')
const received = ref('')
const upiRef = ref('')
const customer = ref('')
const notPaid = ref(false)
const busy = ref(false)

const current = computed(() => product(build.value.size))
const total = computed(() => lines.value.reduce((n, l) => n + l.price * l.qty, 0))
const change = computed(() => {
  const r = Number(received.value)
  return received.value !== '' && r >= total.value ? r - total.value : null
})
const short = computed(() => received.value !== '' && Number(received.value) < total.value)

function addLine(b = build.value, q = qty.value) {
  const p = product(b.size)
  if (!p) return
  const copy = JSON.parse(JSON.stringify({ ...b, cheese: p.cheese }))
  const same = lines.value.find((l) => sameBuild(l.build, copy))
  if (same) same.qty = Math.min(20, same.qty + q)
  else lines.value.push({ id: Date.now() + Math.random(), build: copy, qty: q, price: p.price })
  last.value = copy
  qty.value = 1
}
function clearPicks() { build.value = { ...blank(), size: build.value.size, cheese: build.value.cheese } }
function remove(l) { lines.value = lines.value.filter((x) => x !== l) }

async function complete() {
  if (!lines.value.length) return
  busy.value = true
  try {
    const order = await api.post('/api/orders', {
      items: lines.value.map((l) => toApiItem(l.build, l.qty)),
      payment_method: payment.value, paid: !notPaid.value,
      customer_name: customer.value, upi_reference: payment.value === 'upi' ? upiRef.value : '',
    })
    const msg = `Order ${order.number} saved · ${inr(order.total_amount)}`
    toast(change.value ? `${msg}. Give back ${inr(change.value)} change.` : msg)
    lines.value = []
    received.value = ''
    upiRef.value = ''
    customer.value = ''
    notPaid.value = false
    refreshActive().catch(() => {})
    refreshToday().catch(() => {})
  } catch (e) { toastError(e) } finally { busy.value = false }
}
</script>

<template>
  <main class="mx-auto grid max-w-7xl items-start gap-5 px-4 py-5 lg:grid-cols-[minmax(0,1fr)_400px]">
    <section class="card p-4 sm:p-5" aria-label="Build a packet">
      <p v-if="!menu.data" class="text-ink-2">Loading the menu…</p>
      <template v-else>
        <PacketBuilder v-model="build" :menu="menu.data" compact />
        <div class="mt-5 flex flex-wrap items-center gap-3 border-t border-dashed border-line pt-4 pb-1">
          <div class="flex items-center gap-2">
            <button class="btn btn-light btn-sm w-10 px-0" type="button" aria-label="One less" :disabled="qty <= 1" @click="qty--">−</button>
            <span class="w-7 text-center font-display text-xl font-bold tabular-nums">{{ qty }}</span>
            <button class="btn btn-light btn-sm w-10 px-0" type="button" aria-label="One more" :disabled="qty >= 20" @click="qty++">+</button>
          </div>
          <button class="btn btn-dark" type="button" @click="addLine()">Add {{ qty }} {{ current?.name }} · {{ inr((current?.price || 0) * qty) }}</button>
          <button v-if="last" class="btn btn-light" type="button" @click="addLine(last, 1)">Repeat last packet</button>
          <button class="ml-auto text-sm font-semibold text-ink-2 underline" type="button" @click="clearPicks">Clear picks</button>
        </div>
      </template>
    </section>

    <aside class="card grid gap-4 p-4 sm:p-5 lg:sticky lg:top-[var(--sticky-top,6rem)]" aria-labelledby="order-h">
      <div class="flex items-baseline justify-between">
        <h2 id="order-h" class="m-0 font-display text-2xl font-extrabold">This order</h2>
        <button v-if="lines.length" class="text-sm font-semibold text-chili underline" type="button" @click="lines = []">Clear</button>
      </div>
      <p v-if="!lines.length" class="m-0 rounded-xl bg-sunk p-4 text-ink-2">Pick a size and ingredients, then tap <b>Add</b>. Add as many packets as the customer wants.</p>
      <ul v-else class="m-0 grid max-h-[40vh] list-none gap-2 overflow-y-auto p-0">
        <li v-for="l in lines" :key="l.id" class="rounded-xl border border-line p-2.5">
          <div class="flex items-start justify-between gap-2">
            <p class="m-0 text-sm">
              <span class="pill mr-1" :class="l.build.size === 'loaded' ? 'bg-chili-soft text-chili' : 'bg-leaf-soft text-leaf'">{{ product(l.build.size)?.name }}</span>
              <span class="text-ink-2">{{ describe(l.build, names) }}</span>
            </p>
            <span class="font-bold tabular-nums">{{ inr(l.price * l.qty) }}</span>
          </div>
          <div class="mt-1.5 flex items-center gap-2">
            <button class="btn btn-light btn-sm h-8 min-h-8 w-8 px-0" type="button" aria-label="One less" @click="l.qty > 1 ? l.qty-- : remove(l)">−</button>
            <span class="w-5 text-center font-semibold tabular-nums">{{ l.qty }}</span>
            <button class="btn btn-light btn-sm h-8 min-h-8 w-8 px-0" type="button" aria-label="One more" @click="l.qty++">+</button>
          </div>
        </li>
      </ul>

      <div class="flex items-baseline justify-between border-t border-line pt-3">
        <span class="font-semibold">Total</span>
        <span class="font-display text-4xl font-extrabold tabular-nums">{{ inr(total) }}</span>
      </div>

      <div class="grid grid-cols-2 gap-2.5" role="group" aria-label="Payment method">
        <button class="key key-sm justify-center" type="button" :aria-pressed="payment === 'cash'" @click="payment = 'cash'"><b>Cash</b></button>
        <button class="key key-sm justify-center" type="button" :aria-pressed="payment === 'upi'" @click="payment = 'upi'"><b>UPI</b></button>
      </div>

      <div v-if="payment === 'cash' && !notPaid">
        <label class="label" for="cash-in">Cash received</label>
        <div class="flex flex-wrap gap-2">
          <input id="cash-in" v-model="received" class="field w-28" type="number" inputmode="numeric" min="0" placeholder="₹" />
          <button v-for="amt in [total, 50, 100, 200, 500].filter((a, i, arr) => a >= total && a > 0 && arr.indexOf(a) === i)" :key="amt"
                  class="btn btn-light btn-sm" type="button" @click="received = String(amt)">{{ amt === total ? 'Exact' : inr(amt) }}</button>
        </div>
        <p v-if="change !== null" class="m-0 mt-2 text-lg font-bold text-leaf">Give back {{ inr(change) }}</p>
        <p v-else-if="short" class="m-0 mt-2 font-semibold text-chili">That's {{ inr(total - Number(received)) }} short.</p>
      </div>
      <div v-else-if="payment === 'upi' && !notPaid">
        <label class="label" for="upi-ref">UPI reference (optional)</label>
        <input id="upi-ref" v-model="upiRef" class="field" maxlength="60" placeholder="Last 4–6 digits" />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label" for="cust">Customer name (optional)</label>
          <input id="cust" v-model="customer" class="field" maxlength="40" />
        </div>
        <label class="mt-6 flex items-center gap-2 text-sm font-semibold">
          <input v-model="notPaid" type="checkbox" class="h-5 w-5 accent-[#1E6E3A]" /> Not paid yet
        </label>
      </div>

      <button class="btn btn-green btn-lg" type="button" :disabled="!lines.length || busy" @click="complete">
        {{ busy ? 'Saving…' : `Complete order · ${inr(total)}` }}
      </button>
    </aside>
  </main>
</template>
