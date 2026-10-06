import { computed, reactive } from 'vue'
import { publicApi } from './api'

const state = reactive({ data: null, loading: false, error: '' })
let inflight = null

export function loadMenu(force = false) {
  if (state.data && !force) return Promise.resolve(state.data)
  if (inflight && !force) return inflight
  state.loading = true
  inflight = publicApi.get('/api/menu')
    .then((d) => { state.data = d; state.error = ''; return d })
    .catch((e) => { state.error = e.message; throw e })
    .finally(() => { state.loading = false; inflight = null })
  return inflight
}

export function useMenu() {
  const names = computed(() => {
    const out = {}
    for (const [cat, list] of Object.entries(state.data?.ingredients || {})) {
      out[cat] = Object.fromEntries(list.map((i) => [i.code, i.name]))
    }
    return out
  })
  const product = (code) => state.data?.products.find((p) => p.code === code)
  return { menu: state, names, product, loadMenu }
}

export const GROUPS = [
  { key: 'base', cat: 'base', title: 'Choose your base', limitKey: null },
  { key: 'toppings', cat: 'topping', title: 'Add toppings', limitKey: 'toppings' },
  { key: 'sauces', cat: 'sauce', title: 'Pick your sauce', limitKey: 'sauces' },
  { key: 'seasonings', cat: 'seasoning', title: 'Add seasoning', limitKey: 'seasonings' },
]

export function toApiItem(b, qty = 1) {
  return { product_code: b.size, quantity: qty, base: b.base, toppings: b.toppings, sauces: b.sauces, seasonings: b.seasonings }
}

export function sameBuild(a, b) {
  return JSON.stringify([a.size, a.base, a.toppings, a.sauces, a.seasonings]) ===
    JSON.stringify([b.size, b.base, b.toppings, b.sauces, b.seasonings])
}
