<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { publicApi } from '../../shared/api'
import OrderItems from '../../shared/components/OrderItems.vue'
import { clock, dayLabel, inr } from '../../shared/format'
import { useMenu } from '../../shared/menu'
import { poll, toastError } from '../../shared/toast'

const props = defineProps({ token: { type: String, required: true } })
const { names } = useMenu()
const order = ref(null)
const error = ref('')
const confirmCancel = ref(false)
let stop = null

const STEPS = [
  { key: 'placed', label: 'Order received' },
  { key: 'preparing', label: 'Making it' },
  { key: 'ready', label: 'Ready to collect' },
  { key: 'completed', label: 'Collected' },
]
const stepIndex = computed(() => STEPS.findIndex((s) => s.key === order.value?.status))

async function load() {
  try {
    order.value = await publicApi.get(`/api/track/${props.token}`)
    error.value = ''
    if (!order.value.active && stop) { stop(); stop = null }
  } catch (e) {
    error.value = e.message
  }
}
onMounted(() => { load(); stop = poll(load, 5000) })
onBeforeUnmount(() => stop?.())
watch(() => props.token, load)

async function cancel() {
  try {
    await publicApi.post(`/api/track/${props.token}/cancel`)
    confirmCancel.value = false
    await load()
  } catch (e) { toastError(e) }
}
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-8">
    <p v-if="error && !order" class="error-box">{{ error }}</p>
    <p v-else-if="!order" class="text-ink-2">Finding your order…</p>

    <template v-if="order">
      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-end justify-between gap-3 bg-char px-6 py-5 text-[#FFF7DA]">
          <div>
            <p class="m-0 text-sm font-semibold uppercase tracking-widest text-turmeric">Your order number</p>
            <p class="m-0 font-display text-6xl font-extrabold leading-none text-turmeric">{{ order.number }}</p>
          </div>
          <p class="m-0 text-right text-sm">{{ order.customer_name }}<br />{{ dayLabel(order.business_date) }} · {{ clock(order.created_at) }}</p>
        </div>

        <div class="px-6 py-6">
          <p v-if="order.status === 'cancelled'" class="error-box m-0 text-base">This order was cancelled.</p>
          <template v-else>
            <p class="m-0 font-hand text-2xl font-bold" aria-live="polite">
              <template v-if="order.status === 'placed'">Got it! We'll start on it shortly.</template>
              <template v-else-if="order.status === 'preparing'">We're making your packet right now.</template>
              <template v-else-if="order.status === 'ready'">Your packet is ready! Come and collect it.</template>
              <template v-else>Enjoy your crunch!</template>
            </p>
            <p v-if="order.active && order.status !== 'ready'" class="m-0 mt-1 text-ink-2">
              {{ order.ahead === 0 ? "You're next in line." : `${order.ahead} ${order.ahead === 1 ? 'order' : 'orders'} ahead of you.` }}
              This page updates by itself.
            </p>
            <ol class="m-0 mt-5 grid list-none grid-cols-4 gap-2 p-0" aria-label="Order progress">
              <li v-for="(s, i) in STEPS" :key="s.key" class="grid gap-1.5">
                <span class="h-2.5 rounded-full" :class="i <= stepIndex ? (s.key === 'ready' || i < stepIndex ? 'bg-leaf' : 'bg-turmeric') : 'bg-sunk'" />
                <span class="text-xs font-semibold sm:text-sm" :class="i <= stepIndex ? 'text-ink' : 'text-ink-3'">{{ s.label }}</span>
              </li>
            </ol>
          </template>
        </div>
      </section>

      <section v-if="order.status !== 'cancelled' && order.payment_status === 'unpaid'" class="card mt-5 p-6">
        <template v-if="order.payment_method === 'upi'">
          <h2 class="m-0 font-display text-xl font-bold">Pay {{ inr(order.total_amount) }} by UPI</h2>
          <p class="m-0 mt-1 text-ink-2">Tap the button on your phone to open your UPI app. Show the payment screen when you collect.</p>
          <a v-if="order.upi_link" class="btn btn-green mt-4" :href="order.upi_link">Pay {{ inr(order.total_amount) }} now</a>
          <p class="m-0 mt-3 text-sm text-ink-2">Or pay to UPI ID <b class="select-all text-ink">{{ order.upi_id }}</b> ({{ order.upi_name }}).</p>
        </template>
        <template v-else>
          <h2 class="m-0 font-display text-xl font-bold">Pay {{ inr(order.total_amount) }} when you collect</h2>
          <p class="m-0 mt-1 text-ink-2">Cash or UPI at the cart, whichever you like.</p>
        </template>
      </section>
      <p v-else-if="order.payment_status === 'paid'" class="mt-5 rounded-xl bg-leaf-soft px-4 py-3 font-semibold text-leaf">Paid {{ inr(order.total_amount) }}. Thank you!</p>

      <section class="card mt-5 p-6">
        <h2 class="m-0 mb-3 font-display text-xl font-bold">What you ordered</h2>
        <OrderItems :items="order.items" :names="names" />
        <p class="m-0 mt-3 flex justify-between border-t border-line pt-3 font-semibold"><span>Total</span><span class="tabular-nums">{{ inr(order.total_amount) }}</span></p>
        <p v-if="order.pickup_note" class="m-0 mt-3 text-sm text-ink-2">{{ order.pickup_note }}</p>
      </section>

      <div class="mt-5 flex flex-wrap items-center gap-3">
        <RouterLink to="/" class="btn btn-light">Order another packet</RouterLink>
        <template v-if="order.can_cancel">
          <button v-if="!confirmCancel" class="btn btn-light text-chili" type="button" @click="confirmCancel = true">Cancel order</button>
          <template v-else>
            <span class="font-semibold">Cancel order {{ order.number }}?</span>
            <button class="btn btn-red btn-sm" type="button" @click="cancel">Yes, cancel it</button>
            <button class="btn btn-light btn-sm" type="button" @click="confirmCancel = false">Keep it</button>
          </template>
        </template>
      </div>
      <p class="mt-4 text-sm text-ink-3">Keep this page open, or bookmark it, to check on your order.</p>
    </template>
  </main>
</template>
