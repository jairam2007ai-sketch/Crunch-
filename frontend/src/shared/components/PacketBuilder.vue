<script setup>
// Pick a size, a base, toppings, sauces and seasoning. Used by the buyer site and the seller POS.
import { computed } from 'vue'
import { GROUPS } from '../menu'
import { inr } from '../format'

const props = defineProps({
  modelValue: { type: Object, required: true },
  menu: { type: Object, required: true }, // { products, ingredients }
  compact: { type: Boolean, default: false },
  showSize: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue'])

const product = computed(() => props.menu.products.find((p) => p.code === props.modelValue.size) || props.menu.products[0])

function limit(group) {
  return group.limitKey ? product.value?.[group.limitKey] ?? 0 : 1
}
function chosen(group, code) {
  const v = props.modelValue
  return group.key === 'base' ? v.base === code : v[group.key].includes(code)
}
function pick(group, code) {
  const v = { ...props.modelValue, toppings: [...props.modelValue.toppings], sauces: [...props.modelValue.sauces], seasonings: [...props.modelValue.seasonings] }
  if (group.key === 'base') v.base = code
  else {
    const arr = v[group.key]
    const i = arr.indexOf(code)
    if (i >= 0) arr.splice(i, 1)
    else {
      arr.push(code)
      if (arr.length > limit(group)) arr.shift() // at the limit, the oldest pick makes room
    }
  }
  emit('update:modelValue', v)
}
function setSize(code) {
  const p = props.menu.products.find((x) => x.code === code)
  if (!p) return
  const v = props.modelValue
  emit('update:modelValue', {
    ...v, size: code, cheese: p.cheese,
    toppings: v.toppings.slice(0, p.toppings), sauces: v.sauces.slice(0, p.sauces), seasonings: v.seasonings.slice(0, p.seasonings),
  })
}
const swClass = { base: 'sw-base', topping: '', sauce: 'sw-sauce', seasoning: 'sw-seasoning' }
</script>

<template>
  <div class="grid" :class="compact ? 'gap-4' : 'gap-6'">
    <div v-if="showSize" class="grid grid-cols-2 gap-3" role="group" aria-label="Packet size">
      <button
        v-for="p in menu.products" :key="p.code" type="button"
        class="key justify-between"
        :class="[compact ? 'key-sm' : '', p.code === 'loaded' ? 'is-loaded' : 'is-regular']"
        :aria-pressed="modelValue.size === p.code" @click="setSize(p.code)"
      >
        <span class="flex flex-col leading-tight">
          <span class="font-display text-lg font-extrabold uppercase tracking-wide">{{ p.name }}</span>
          <span v-if="!compact" class="text-xs text-ink-3">{{ p.toppings }} toppings · {{ p.sauces }} {{ p.sauces === 1 ? 'sauce' : 'sauces' }} · {{ p.seasonings }} {{ p.seasonings === 1 ? 'masala' : 'masalas' }}{{ p.cheese ? ' · cheese' : '' }}</span>
        </span>
        <span class="font-display text-2xl font-extrabold">{{ inr(p.price) }}</span>
      </button>
    </div>

    <section v-for="(g, gi) in GROUPS" :key="g.key" class="grid" :class="compact ? 'gap-2' : 'gap-3'" :aria-labelledby="`grp-${g.key}`">
      <div class="flex flex-wrap items-center gap-2.5">
        <span v-if="!compact" class="num-coin" aria-hidden="true">{{ gi + 1 }}</span>
        <h3 :id="`grp-${g.key}`" class="m-0 font-display font-bold" :class="compact ? 'text-base' : 'text-xl'">{{ g.title }}</h3>
        <span class="ml-auto pill tabular-nums"
              :class="(g.key === 'base' ? 1 : modelValue[g.key].length) === limit(g) ? 'bg-char text-turmeric' : 'bg-sunk text-ink-2'">
          {{ g.key === 'base' ? 'Pick 1' : `${modelValue[g.key].length} of ${limit(g)}` }}
        </span>
      </div>
      <div class="grid gap-2.5" :class="compact ? 'grid-cols-[repeat(auto-fill,minmax(128px,1fr))]' : 'grid-cols-[repeat(auto-fill,minmax(150px,1fr))]'">
        <button
          v-for="ing in menu.ingredients[g.cat]" :key="ing.code" type="button"
          class="key" :class="compact ? 'key-sm' : ''"
          :aria-pressed="chosen(g, ing.code)" :disabled="!ing.available && !chosen(g, ing.code)"
          @click="pick(g, ing.code)"
        >
          <span class="sw" :class="swClass[g.cat]" :style="{ '--c': ing.color }" aria-hidden="true" />
          <span class="flex min-w-0 flex-col leading-tight">
            <span class="font-semibold">{{ ing.name }}</span>
            <span v-if="!ing.available" class="text-xs font-semibold text-chili">Sold out</span>
            <span v-else-if="ing.note && !compact" class="text-xs text-ink-3">{{ ing.note }}</span>
          </span>
        </button>
      </div>
      <p v-if="g.key === 'seasonings' && product?.cheese" class="m-0 flex items-center gap-2 text-sm text-ink-2">
        <span class="inline-block h-1.5 w-3.5 rounded bg-[#FFE27D] ring-1 ring-[#D9AE36]" aria-hidden="true" />
        {{ product.name }} also gets grated cheese on top.
      </p>
    </section>
  </div>
</template>

<style scoped>
.key.is-regular[aria-pressed="true"] { background: var(--color-leaf); color: #fff; border-color: #12441F; }
.key.is-loaded[aria-pressed="true"] { background: var(--color-chili); color: #fff; border-color: #7E1C17; }
.key.is-regular[aria-pressed="true"] .text-ink-3, .key.is-loaded[aria-pressed="true"] .text-ink-3 { color: rgba(255,255,255,.85); }
</style>
