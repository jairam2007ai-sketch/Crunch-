<script setup>
import StockPanel from '../../shared/components/StockPanel.vue'
import { api, session } from '../store'
</script>

<template>
  <main class="mx-auto max-w-5xl px-4 py-5">
    <h1 class="m-0 mb-3 font-display text-3xl font-extrabold">Stock</h1>
    <StockPanel :api="api" :owner="session.state.user?.role === 'owner'" />
  </main>
</template>
