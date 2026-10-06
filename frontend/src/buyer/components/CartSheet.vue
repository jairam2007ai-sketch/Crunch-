<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { publicApi } from '../../shared/api'
import { describe, inr, todayYmd } from '../../shared/format'
import { toApiItem, useMenu } from '../../shared/menu'
import { storage } from '../../shared/session'
import { cart, cartCount, cartTotal, rememberOrder } from '../cart'

const router = useRouter()
const { menu, names, product } = useMenu()
const panel = ref(null)
const form = reactive({ name: storage.read('crunch.name') || '', phone: storage.read('crunch.phone') || '', payment: 'pay_at_cart', note: '' })
const error = ref('')
const busy = ref(false)

const acceptsUpi = computed(() => !!menu.data?.shop.accepts_upi)
const open = computed(() => menu.data?.shop.is_open !== false)

watch(() => cart.open, async (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) { error.value = ''; await nextTick(); panel.value?.focus() }
})

function remove(line) {
  const i = cart.lines.indexOf(line)
  if (i >= 0) cart.lines.splice(i, 1)
}

async function place() {
  error.value = ''
  if (!cart.lines.length) return
  busy.value = true
  try {
    const res = await publicApi.post('/api/orders/online', {
      customer_name: form.name, customer_phone: form.phone, payment_method: form.payment, note: form.note,
      items: cart.lines.map((l) => toApiItem(l.build, l.qty)),
    })
    storage.write('crunch.name', form.name.trim())
    storage.write('crunch.phone', form.phone.trim())
    rememberOrder({ token: res.tracking_token, number: res.number, total: res.total, date: todayYmd() })
    cart.lines.splice(0)
    form.note = ''
    cart.open = false
    router.push(`/order/${res.tracking_token}`)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="cart.open" class="fixed inset-0 z-50 flex justify-end bg-black/45" @click.self="cart.open = false" @keydown.esc="cart.open = false">
      <section ref="panel" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="cart-h"
               class="flex h-full w-full max-w-md flex-col overflow-y-auto bg-paper shadow-2xl outline-none">
        <header class="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-paper px-5 py-4">
          <h2 id="cart-h" class="m-0 font-display text-2xl font-extrabold">Your order</h2>
          <button class="btn btn-light btn-sm" type="button" @click="cart.open = false">Close</button>
        </header>

        <div v-if="!cart.lines.length" class="grid gap-3 px-5 py-10 text-center">
          <p class="m-0 font-hand text-2xl font-bold">Your packet is empty!</p>
          <p class="m-0 text-ink-2">Build a packet and tap Add to order.</p>
          <button class="btn btn-dark mx-auto" type="button" @click="cart.open = false">Build a packet</button>
        </div>

        <template v-else>
          <ul class="m-0 grid list-none gap-3 px-5 py-4">
            <li v-for="l in cart.lines" :key="l.id" class="card p-3">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <span class="pill" :class="l.build.size === 'loaded' ? 'bg-chili-soft text-chili' : 'bg-leaf-soft text-leaf'">{{ product(l.build.size)?.name || l.build.size }}</span>
                  <p class="m-0 mt-1 text-sm text-ink-2">{{ describe({ ...l.build, cheese: l.build.cheese ?? l.build.size === 'loaded' }, names) }}</p>
                </div>
                <span class="font-display text-lg font-bold tabular-nums">{{ inr(l.price * l.qty) }}</span>
              </div>
              <div class="mt-2 flex items-center gap-2">
                <button class="btn btn-light btn-sm w-9 px-0" type="button" aria-label="One less" @click="l.qty > 1 ? l.qty-- : remove(l)">−</button>
                <span class="w-6 text-center font-bold tabular-nums">{{ l.qty }}</span>
                <button class="btn btn-light btn-sm w-9 px-0" type="button" aria-label="One more" :disabled="l.qty >= 20" @click="l.qty++">+</button>
                <button class="ml-auto text-sm font-semibold text-chili underline" type="button" @click="remove(l)">Remove</button>
              </div>
            </li>
          </ul>

          <form class="mt-auto grid gap-3 border-t border-line bg-white px-5 py-5" @submit.prevent="place">
            <div class="flex items-baseline justify-between">
              <span class="font-semibold">{{ cartCount }} {{ cartCount === 1 ? 'packet' : 'packets' }}</span>
              <span class="font-display text-3xl font-extrabold tabular-nums">{{ inr(cartTotal) }}</span>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label" for="c-name">Your name</label>
                <input id="c-name" v-model="form.name" class="field" autocomplete="given-name" maxlength="40" required />
              </div>
              <div>
                <label class="label" for="c-phone">Mobile number</label>
                <input id="c-phone" v-model="form.phone" class="field" type="tel" inputmode="numeric" autocomplete="tel-national" maxlength="14" placeholder="10 digits" required />
              </div>
            </div>
            <fieldset class="m-0 grid gap-2 border-0 p-0">
              <legend class="label">How will you pay?</legend>
              <label class="key key-sm" :class="{ 'is-on': form.payment === 'pay_at_cart' }">
                <input v-model="form.payment" class="sr-only" type="radio" value="pay_at_cart" />
                <span><b>Pay at the cart</b><span class="block text-xs text-ink-3">Cash or UPI when you collect</span></span>
              </label>
              <label v-if="acceptsUpi" class="key key-sm" :class="{ 'is-on': form.payment === 'upi' }">
                <input v-model="form.payment" class="sr-only" type="radio" value="upi" />
                <span><b>Pay now by UPI</b><span class="block text-xs text-ink-3">GPay, PhonePe, Paytm…</span></span>
              </label>
            </fieldset>
            <div>
              <label class="label" for="c-note">Anything we should know? (optional)</label>
              <input id="c-note" v-model="form.note" class="field" maxlength="200" placeholder="e.g. less spicy" />
            </div>
            <p v-if="error" class="error-box m-0">{{ error }}</p>
            <button class="btn btn-dark btn-lg" type="submit" :disabled="busy || !open">
              {{ !open ? 'Online ordering is closed' : busy ? 'Placing your order…' : `Place order · ${inr(cartTotal)}` }}
            </button>
            <p class="m-0 text-center text-xs text-ink-3">We only use your number to find you when your packet is ready.</p>
          </form>
        </template>
      </section>
    </div>
  </Teleport>
</template>
