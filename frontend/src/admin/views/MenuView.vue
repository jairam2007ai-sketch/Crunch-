<script setup>
// Prices, cost per packet (for profit) and which ingredients are on today.
import { onMounted, reactive, ref } from 'vue'
import { inr } from '../../shared/format'
import { loadMenu } from '../../shared/menu'
import { toast, toastError } from '../../shared/toast'
import { api } from '../store'

const products = ref([])
const edits = reactive({})
const stock = ref([])

async function load() {
  try {
    products.value = await api.get('/api/products')
    products.value.forEach((p) => { edits[p.id] = { price: p.price, cost: p.cost } })
    stock.value = await api.get('/api/inventory')
  } catch (e) { toastError(e) }
}
onMounted(load)

async function saveProduct(p) {
  try {
    const e = edits[p.id]
    const updated = await api.patch(`/api/products/${p.id}`, { price: Number(e.price), cost: Number(e.cost) })
    Object.assign(p, updated)
    toast(`${p.name}: ${inr(updated.price)}, cost ${inr(updated.cost)}.`)
    loadMenu(true).catch(() => {})
  } catch (err) { toastError(err) }
}
async function toggleProduct(p) {
  try { Object.assign(p, await api.patch(`/api/products/${p.id}`, { is_active: !p.is_active })); loadMenu(true).catch(() => {}) } catch (e) { toastError(e) }
}
async function toggleIngredient(i) {
  try {
    const updated = await api.patch(`/api/ingredients/${i.id}`, { is_active: !i.active })
    Object.assign(i, updated)
    toast(updated.active ? `${i.name} is back on the menu.` : `${i.name} is off the menu.`)
    loadMenu(true).catch(() => {})
  } catch (e) { toastError(e) }
}
const CATS = [['base', 'Chips'], ['topping', 'Toppings'], ['sauce', 'Sauces'], ['seasoning', 'Seasonings'], ['extra', 'Extras']]
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="m-0 font-display text-3xl font-extrabold">Menu &amp; prices</h1>
    <p class="m-0 mb-5 text-ink-2">Prices change on the buyer site and the POS straight away. Cost per packet is only used to estimate profit; customers never see it.</p>

    <div class="grid gap-4 md:grid-cols-2">
      <form v-for="p in products" :key="p.id" class="card p-5" @submit.prevent="saveProduct(p)">
        <div class="flex items-center justify-between">
          <h2 class="m-0 font-display text-2xl font-extrabold uppercase" :class="p.code === 'loaded' ? 'text-chili' : 'text-leaf'">{{ p.name }}</h2>
          <label class="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" class="h-5 w-5 accent-[#1E6E3A]" :checked="p.is_active" @change="toggleProduct(p)" /> On the menu
          </label>
        </div>
        <p class="m-0 mt-1 text-sm text-ink-2">{{ p.description }}</p>
        <div class="mt-4 flex flex-wrap items-end gap-3">
          <div><label class="label" :for="`price-${p.id}`">Price (₹)</label><input :id="`price-${p.id}`" v-model="edits[p.id].price" class="field w-28" type="number" min="1" required /></div>
          <div><label class="label" :for="`cost-${p.id}`">Cost per packet (₹)</label><input :id="`cost-${p.id}`" v-model="edits[p.id].cost" class="field w-28" type="number" min="0" required /></div>
          <button class="btn btn-dark btn-sm mb-1" type="submit">Save</button>
        </div>
        <p v-if="Number(edits[p.id].cost) > 0" class="m-0 mt-3 text-sm text-ink-2">
          Margin {{ inr(edits[p.id].price - edits[p.id].cost) }} a packet ({{ Math.round(((edits[p.id].price - edits[p.id].cost) / edits[p.id].price) * 100) }}%).
        </p>
        <p v-else class="m-0 mt-3 text-sm text-amber">Add your cost (chips, toppings, sauce, packet) to see profit on the dashboard.</p>
      </form>
    </div>

    <h2 class="m-0 mb-2 mt-8 font-display text-2xl font-extrabold">Ingredients on today</h2>
    <p class="m-0 mb-4 text-ink-2">Turn something off when it runs out. Customers will see it as sold out.</p>
    <div class="grid gap-4 md:grid-cols-2">
      <section v-for="[cat, label] in CATS" :key="cat" class="card p-4">
        <h3 class="m-0 mb-2 font-display text-lg font-bold">{{ label }}</h3>
        <ul class="m-0 grid list-none gap-1 p-0">
          <li v-for="i in stock.filter((s) => s.category === cat)" :key="i.id" class="flex items-center justify-between gap-3 py-1">
            <span :class="i.active ? '' : 'text-ink-3 line-through'">{{ i.name }}</span>
            <button class="btn btn-sm" :class="i.active ? 'btn-light' : 'btn-yellow'" type="button" @click="toggleIngredient(i)">{{ i.active ? 'Turn off' : 'Turn on' }}</button>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
