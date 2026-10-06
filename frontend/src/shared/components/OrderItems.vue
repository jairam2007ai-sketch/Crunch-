<script setup>
import { describe, inr } from '../format'

defineProps({
  items: { type: Array, required: true },
  names: { type: Object, default: () => ({}) },
  prices: { type: Boolean, default: true },
})
</script>

<template>
  <ul class="m-0 grid list-none gap-2 p-0">
    <li v-for="it in items" :key="it.id" class="grid grid-cols-[auto_1fr_auto] items-baseline gap-x-2">
      <span class="font-display font-bold tabular-nums">{{ it.quantity }}×</span>
      <span>
        <span class="pill mr-1.5" :class="it.product_code === 'loaded' ? 'bg-chili-soft text-chili' : 'bg-leaf-soft text-leaf'">{{ it.product_name }}</span>
        <span class="text-ink-2">{{ describe(it.selections, names) }}</span>
      </span>
      <span v-if="prices" class="tabular-nums text-ink-2">{{ inr(it.total) }}</span>
    </li>
  </ul>
</template>
