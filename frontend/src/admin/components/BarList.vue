<script setup>
// Labelled horizontal bars: name on the left, thin bar, value at the tip.
import { computed } from 'vue'

const props = defineProps({
  rows: { type: Array, required: true }, // [{ key, name, value, color? }]
  format: { type: Function, default: (v) => String(v) },
  color: { type: String, default: '#A67B00' },
  limit: { type: Number, default: 5 },
  empty: { type: String, default: 'No data yet.' },
})
const top = computed(() => props.rows.slice(0, props.limit))
const max = computed(() => Math.max(1, ...top.value.map((r) => r.value)))
</script>

<template>
  <p v-if="!top.length" class="m-0 text-sm text-ink-3">{{ empty }}</p>
  <ul v-else class="m-0 grid list-none gap-2.5 p-0">
    <li v-for="r in top" :key="r.key" class="grid grid-cols-[minmax(6.5rem,8.5rem)_1fr] items-center gap-3 text-sm">
      <span class="truncate font-medium" :title="r.name">{{ r.name }}</span>
      <span class="flex items-center gap-2">
        <span class="h-3.5 shrink-0 rounded-r-[4px]" :style="{ width: `max(3px, calc((100% - 6.5rem) * ${r.value / max}))`, background: r.color || color }" />
        <span class="whitespace-nowrap tabular-nums text-ink-2">{{ format(r.value) }}</span>
      </span>
    </li>
  </ul>
</template>
