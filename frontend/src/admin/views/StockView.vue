<script setup>
import StockPanel from '../../shared/components/StockPanel.vue'
import { api } from '../store'
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="m-0 mb-3 font-display text-3xl font-extrabold">Stock</h1>
    <StockPanel :api="api" owner />
  </div>
</template>
