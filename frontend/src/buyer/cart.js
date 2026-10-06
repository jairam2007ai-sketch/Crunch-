import { computed, reactive, watch } from 'vue'
import { sameBuild } from '../shared/menu'
import { storage } from '../shared/session'

const CART_KEY = 'crunch.cart'
const RECENT_KEY = 'crunch.recent'

function readJSON(key, fallback) {
  try { return JSON.parse(storage.read(key) || 'null') ?? fallback } catch { return fallback }
}

export const cart = reactive({ lines: readJSON(CART_KEY, []), open: false })
export const recent = reactive(readJSON(RECENT_KEY, []))

watch(() => cart.lines, (v) => storage.write(CART_KEY, JSON.stringify(v)), { deep: true })
watch(recent, (v) => storage.write(RECENT_KEY, JSON.stringify(v.slice(0, 5))), { deep: true })

export const cartCount = computed(() => cart.lines.reduce((n, l) => n + l.qty, 0))
export const cartTotal = computed(() => cart.lines.reduce((n, l) => n + l.qty * l.price, 0))

export function addToCart(build, qty, price) {
  const same = cart.lines.find((l) => sameBuild(l.build, build))
  if (same) same.qty = Math.min(20, same.qty + qty)
  else cart.lines.push({ id: Date.now() + Math.random(), build: JSON.parse(JSON.stringify(build)), qty, price })
}

export function rememberOrder(o) {
  recent.unshift(o)
  recent.splice(5)
}
