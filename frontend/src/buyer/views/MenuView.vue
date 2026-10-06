<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Packet3D from '../../shared/components/Packet3D.vue'
import PacketBuilder from '../../shared/components/PacketBuilder.vue'
import { dayLabel, inr } from '../../shared/format'
import { loadMenu, useMenu } from '../../shared/menu'
import { toast } from '../../shared/toast'
import { addToCart, cart, recent } from '../cart'

const { menu, product } = useMenu()
const HERO = { size: 'loaded', base: 'masala', toppings: ['onion', 'tomato', 'corn'], sauces: ['tandoori', 'periperi'], seasonings: ['chaat', 'chilli'], cheese: true }
const build = ref({ size: 'loaded', base: 'potato', toppings: ['onion', 'corn', 'coriander'], sauces: ['garlic', 'periperi'], seasonings: ['chaat', 'oregano'], cheese: true })
const qty = ref(1)
const packet = ref(null)

// Once the menu arrives, drop any default picks that are sold out today.
watch(() => menu.data, (d) => {
  if (!d) return
  const ok = (cat, code) => d.ingredients[cat]?.some((i) => i.code === code && i.available)
  const b = { ...build.value }
  const p = d.products.find((x) => x.code === b.size) || d.products[0]
  if (!p) return
  b.size = p.code
  b.cheese = p.cheese
  if (!ok('base', b.base)) b.base = d.ingredients.base.find((i) => i.available)?.code || b.base
  b.toppings = b.toppings.filter((c) => ok('topping', c)).slice(0, p.toppings)
  b.sauces = b.sauces.filter((c) => ok('sauce', c)).slice(0, p.sauces)
  b.seasonings = b.seasonings.filter((c) => ok('seasoning', c)).slice(0, p.seasonings)
  build.value = b
}, { immediate: true })

const current = computed(() => product(build.value.size))
const open = computed(() => menu.data?.shop.is_open)
const lineTotal = computed(() => (current.value?.price || 0) * qty.value)

function chooseSize(code) {
  const p = product(code)
  if (!p) return
  const b = build.value
  build.value = { ...b, size: code, cheese: p.cheese, toppings: b.toppings.slice(0, p.toppings), sauces: b.sauces.slice(0, p.sauces), seasonings: b.seasonings.slice(0, p.seasonings) }
  document.getElementById('build')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function add() {
  if (!current.value) return
  addToCart(build.value, qty.value, current.value.price)
  toast(`Added ${qty.value} × ${current.value.name} to your order.`)
  packet.value?.shake(false)
  qty.value = 1
}

const STEPS = [
  ['Choose your base', '4 chips to pick from'], ['Add toppings', '5 fresh options'], ['Pick a sauce', '3 options'],
  ['Add seasoning', '5 masalas'], ['We shake it', 'Our magic'], ['Collect it', 'In your packet'],
]
</script>

<template>
  <main class="pb-24 lg:pb-0">
    <!-- hero -->
    <section class="overflow-hidden bg-turmeric text-char">
      <div class="mx-auto grid max-w-6xl items-center gap-8 px-4 py-10 md:grid-cols-[1.2fr_.8fr] md:py-12">
        <div class="grid justify-items-start gap-4">
          <div class="lockup-wrap">
            <h1 class="lockup text-[clamp(54px,13vw,120px)]"><span class="top">Customize Your</span><span class="main">CRUNCH</span></h1>
          </div>
          <p class="m-0 -rotate-1 font-hand text-[clamp(24px,3.2vw,32px)] font-bold leading-tight">Small packet… Big happiness!</p>
          <p class="m-0 max-w-[34em] text-lg">Pick your chips, pile on fresh toppings, choose your sauce and masala. Order here, then collect it fresh at the cart.</p>
          <div class="flex flex-wrap gap-3">
            <a class="btn btn-dark" href="#build" @click.prevent="chooseSize(build.size)">Build your packet</a>
            <button class="btn btn-light" type="button" @click="cart.open = true">See your order</button>
          </div>
          <p class="m-0 flex items-center gap-2 text-sm font-semibold"><span class="veg" aria-hidden="true" />100% veg · Regular ₹49 · Loaded ₹69</p>
          <p v-if="menu.data && !open" class="m-0 rounded-xl bg-char px-4 py-3 font-semibold text-turmeric">
            We're not taking online orders right now. Come and see us at the cart!
          </p>
        </div>
        <div class="relative mx-auto w-full max-w-[300px] md:max-w-[380px]">
          <div class="absolute inset-x-0 bottom-[1%] top-[6%] rounded-full bg-[radial-gradient(circle_at_42%_34%,#3A3528,#1B1A17_62%)] shadow-[inset_0_-14px_30px_rgba(0,0,0,.55),0_26px_40px_-24px_rgba(0,0,0,.6)]" />
          <Packet3D class="relative" :build="HERO" spin="turn" floaters intro :seed="20241"
                    label="A Loaded packet of masala chips with onion, tomato, corn, tandoori mayo and peri-peri, in 3D" hint="Drag to turn the packet" />
          <p class="pointer-events-none absolute -right-1 top-[2%] z-10 m-0 flex h-24 w-24 rotate-12 flex-col items-center justify-center rounded-full bg-[radial-gradient(circle_at_38%_30%,#E0483F,#C2302A_60%)] font-hand text-base font-bold leading-tight text-white shadow-[0_5px_0_#7E1C17,0_14px_20px_-8px_rgba(0,0,0,.55)]" aria-hidden="true">
            <span>Fresh</span><span>Tasty</span><span>Affordable</span>
          </p>
        </div>
      </div>
    </section>

    <!-- menu -->
    <section class="mx-auto max-w-6xl px-4 py-12" aria-labelledby="menu-h">
      <div class="mb-7 flex flex-wrap items-center gap-x-5 gap-y-2">
        <div class="brush-wrap"><h2 id="menu-h" class="brush-label text-[clamp(28px,4vw,40px)]">Our menu</h2></div>
        <p class="m-0 font-hand text-xl font-bold text-ink-2">Only 2 options. Both pure veg.</p>
      </div>
      <p v-if="menu.error" class="error-box">{{ menu.error }} <button class="underline" @click="loadMenu(true)">Try again</button></p>
      <div v-if="menu.data" class="grid gap-5 sm:grid-cols-2">
        <article v-for="p in menu.data.products" :key="p.code" class="card flex flex-col transition-transform hover:-translate-y-1">
          <header class="flex items-center justify-between gap-3 rounded-t-[15px] px-5 py-4 text-white"
                  :class="p.code === 'loaded' ? 'bg-chili shadow-[inset_0_-4px_0_#7E1C17]' : 'bg-leaf shadow-[inset_0_-4px_0_#12441F]'">
            <h3 class="m-0 font-display text-3xl font-extrabold uppercase tracking-wider">{{ p.name }}</h3>
            <p class="m-0 -rotate-3 rounded-lg bg-turmeric px-3 pb-1 pt-2 font-display text-3xl font-extrabold leading-none text-char shadow-[0_5px_0_#A67B00]">{{ inr(p.price) }}</p>
          </header>
          <ul class="m-0 grid flex-1 list-none gap-2 px-5 py-4 text-[17px]">
            <li><b class="font-display text-xl" :class="p.code === 'loaded' ? 'text-chili' : 'text-leaf'">1</b>&nbsp; base of your choice <span class="text-sm text-ink-3">({{ p.code === 'loaded' ? 'larger portion' : 'regular portion' }})</span></li>
            <li><b class="font-display text-xl" :class="p.code === 'loaded' ? 'text-chili' : 'text-leaf'">{{ p.toppings }}</b>&nbsp; toppings</li>
            <li><b class="font-display text-xl" :class="p.code === 'loaded' ? 'text-chili' : 'text-leaf'">{{ p.sauces }}</b>&nbsp; {{ p.sauces === 1 ? 'sauce' : 'sauces' }}</li>
            <li><b class="font-display text-xl" :class="p.code === 'loaded' ? 'text-chili' : 'text-leaf'">{{ p.seasonings }}</b>&nbsp; {{ p.seasonings === 1 ? 'seasoning' : 'seasonings' }}</li>
            <li v-if="p.cheese"><b class="font-display text-xl text-chili">+</b>&nbsp; cheese on top</li>
          </ul>
          <footer class="flex flex-wrap items-center justify-between gap-3 px-5 pb-5">
            <span class="flex items-center gap-2 text-sm font-semibold text-ink-2"><span class="veg" aria-hidden="true" />Veg only</span>
            <button class="btn btn-dark" type="button" @click="chooseSize(p.code)">Build a {{ p.name }}</button>
          </footer>
        </article>
      </div>

      <div class="mt-9 rounded-2xl bg-sunk px-5 py-5">
        <h3 class="m-0 mb-3 font-hand text-xl font-bold">How it works</h3>
        <ol class="m-0 grid list-none grid-cols-2 gap-4 p-0 sm:grid-cols-3 lg:grid-cols-6">
          <li v-for="(s, i) in STEPS" :key="s[0]" class="flex items-center gap-2.5">
            <span class="num-coin" aria-hidden="true">{{ i + 1 }}</span>
            <span class="leading-tight"><b class="block">{{ s[0] }}</b><span class="text-sm text-ink-2">{{ s[1] }}</span></span>
          </li>
        </ol>
      </div>

      <div v-if="recent.length" class="card mt-6 p-5">
        <h3 class="m-0 mb-2 font-display text-xl font-bold">Your recent orders</h3>
        <ul class="m-0 grid list-none gap-1 p-0">
          <li v-for="o in recent" :key="o.token">
            <RouterLink :to="`/order/${o.token}`" class="font-semibold underline decoration-turmeric decoration-2 underline-offset-4">
              Order {{ o.number }} · {{ dayLabel(o.date) }} · {{ inr(o.total) }}
            </RouterLink>
          </li>
        </ul>
      </div>
    </section>

    <!-- builder -->
    <section id="build" class="scroll-mt-20 bg-sunk" aria-labelledby="build-h">
      <div class="mx-auto max-w-6xl px-4 py-12">
        <div class="mb-7">
          <div class="brush-wrap"><h2 id="build-h" class="brush-label text-[clamp(28px,4vw,40px)]">Build your crunch</h2></div>
        </div>
        <p v-if="!menu.data && !menu.error" class="text-ink-2">Loading the menu…</p>
        <div v-if="menu.data" class="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div class="order-2 lg:order-1">
            <PacketBuilder v-model="build" :menu="menu.data" />
          </div>
          <aside class="card order-1 mx-auto grid w-full max-w-md gap-4 p-4 lg:sticky lg:top-20 lg:order-2" aria-label="Your packet">
            <div class="mx-auto w-full max-w-[250px] overflow-hidden rounded-xl bg-[radial-gradient(ellipse_85%_65%_at_50%_32%,#fff,#FFF4CF_72%)] lg:max-w-none">
              <Packet3D ref="packet" :build="build" counter />
            </div>
            <div class="flex items-center justify-between">
              <span class="pill" :class="build.size === 'loaded' ? 'bg-chili-soft text-chili' : 'bg-leaf-soft text-leaf'">{{ current?.name }}</span>
              <span class="font-display text-3xl font-extrabold">{{ inr(current?.price) }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="label m-0">How many</span>
              <div class="flex items-center gap-2">
                <button class="btn btn-light btn-sm w-10 px-0" type="button" aria-label="One less" :disabled="qty <= 1" @click="qty--">−</button>
                <span class="w-6 text-center font-display text-xl font-bold tabular-nums" aria-live="polite">{{ qty }}</span>
                <button class="btn btn-light btn-sm w-10 px-0" type="button" aria-label="One more" :disabled="qty >= 20" @click="qty++">+</button>
              </div>
            </div>
            <div class="grid grid-cols-[auto_1fr] gap-3 pb-1">
              <button class="btn btn-yellow" type="button" @click="packet?.shake()">Shake it</button>
              <button class="btn btn-dark" type="button" :disabled="!open" @click="add">Add to order · {{ inr(lineTotal) }}</button>
            </div>
            <p v-if="!open" class="m-0 text-center text-sm text-ink-2">Online ordering is closed right now.</p>
          </aside>
        </div>
      </div>
    </section>

    <!-- phone: keep the add button in reach -->
    <div v-if="menu.data" class="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white/95 px-4 pb-[calc(10px+env(safe-area-inset-bottom))] pt-2.5 backdrop-blur lg:hidden">
      <div class="mx-auto flex max-w-md items-center gap-3">
        <div class="leading-tight">
          <div class="text-sm text-ink-2">{{ qty }} × {{ current?.name }}</div>
          <div class="font-display text-xl font-extrabold">{{ inr(lineTotal) }}</div>
        </div>
        <button class="btn btn-dark ml-auto" type="button" :disabled="!open" @click="add">Add to order</button>
      </div>
    </div>
  </main>
</template>
