<script setup>
// Stock in portions. Sellers record deliveries and waste; the owner can also set an exact count.
import { computed, onMounted, reactive, ref } from 'vue'
import { toast, toastError } from '../toast'

const props = defineProps({
  api: { type: Object, required: true },
  owner: { type: Boolean, default: false },
})

const items = ref([])
const loading = ref(true)
const open = ref(null) // ingredient id with the form open
const form = reactive({ type: 'in', quantity: '', note: '' })
const busy = ref(false)

const CATS = [
  ['base', 'Chips'], ['topping', 'Toppings'], ['sauce', 'Sauces'], ['seasoning', 'Seasonings'], ['extra', 'Extras'], ['packaging', 'Packaging'],
]
const grouped = computed(() => CATS.map(([cat, label]) => ({ cat, label, rows: items.value.filter((i) => i.category === cat) })))
const lowCount = computed(() => items.value.filter((i) => i.low || (i.tracked && i.out)).length)

async function load() {
  try { items.value = await props.api.get('/api/inventory') } catch (e) { toastError(e) } finally { loading.value = false }
}
onMounted(load)

function start(item, type) {
  open.value = item.id
  form.type = type
  form.quantity = ''
  form.note = ''
}
async function save(item) {
  const q = Number(form.quantity)
  if (!(q >= 0) || form.quantity === '') { toast('Enter a number of portions.', 'error'); return }
  busy.value = true
  try {
    const updated = await props.api.post(`/api/inventory/${item.id}/adjust`, { type: form.type, quantity: q, note: form.note })
    items.value = items.value.map((i) => (i.id === item.id ? updated : i))
    open.value = null
    toast(`${item.name}: ${updated.stock} portions in stock.`)
  } catch (e) { toastError(e) } finally { busy.value = false }
}
const VERB = { in: 'Add delivery', waste: 'Record waste', count: 'Set exact count' }
</script>

<template>
  <div class="grid gap-5">
    <p class="m-0 max-w-[70ch] text-ink-2">
      Stock is counted in portions: one portion is what goes into one Regular packet. Loaded packets use 1.5 portions of chips.
      Counting starts for an item the first time you record a delivery.
      <strong v-if="lowCount" class="text-chili">{{ lowCount }} {{ lowCount === 1 ? 'item is' : 'items are' }} low.</strong>
    </p>
    <p v-if="loading" class="text-ink-2">Loading stock…</p>
    <section v-for="g in grouped" v-show="g.rows.length" :key="g.cat" class="card overflow-hidden">
      <h3 class="m-0 border-b border-line bg-sunk px-4 py-2 font-display text-lg font-bold">{{ g.label }}</h3>
      <ul class="m-0 list-none p-0">
        <li v-for="i in g.rows" :key="i.id" class="border-b border-line px-4 py-3 last:border-0">
          <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
            <div class="min-w-40 flex-1">
              <span class="font-semibold">{{ i.name }}</span>
              <span v-if="!i.active" class="pill ml-2 bg-sunk text-ink-2">Turned off</span>
            </div>
            <div class="w-36 tabular-nums">
              <template v-if="i.tracked">
                <span class="font-display text-xl font-bold">{{ i.stock }}</span>
                <span class="text-sm text-ink-2"> portions</span>
                <span v-if="i.out" class="pill ml-1 bg-chili-soft text-chili">Out</span>
                <span v-else-if="i.low" class="pill ml-1 bg-amber-soft text-amber">Low</span>
              </template>
              <span v-else class="text-sm text-ink-3">Not counted yet</span>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-light btn-sm" type="button" @click="start(i, 'in')">+ Delivery</button>
              <button class="btn btn-light btn-sm" type="button" :disabled="!i.tracked" @click="start(i, 'waste')">Waste</button>
              <button v-if="owner" class="btn btn-light btn-sm" type="button" @click="start(i, 'count')">Set count</button>
            </div>
          </div>
          <form v-if="open === i.id" class="mt-3 flex flex-wrap items-end gap-3 rounded-xl bg-sunk p-3" @submit.prevent="save(i)">
            <div>
              <label class="label" :for="`q-${i.id}`">{{ VERB[form.type] }} (portions)</label>
              <input :id="`q-${i.id}`" v-model="form.quantity" class="field w-36" type="number" min="0" step="0.5" inputmode="decimal" required />
            </div>
            <div class="min-w-48 flex-1">
              <label class="label" :for="`n-${i.id}`">Note (optional)</label>
              <input :id="`n-${i.id}`" v-model="form.note" class="field" maxlength="200" placeholder="e.g. from the wholesale market" />
            </div>
            <button class="btn btn-dark btn-sm" type="submit" :disabled="busy">Save</button>
            <button class="btn btn-light btn-sm" type="button" @click="open = null">Cancel</button>
          </form>
        </li>
      </ul>
    </section>
  </div>
</template>
