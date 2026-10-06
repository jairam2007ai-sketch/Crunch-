<script setup>
import { toasts } from '../toast'
</script>

<template>
  <div class="toast-stack" role="status" aria-live="polite">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.kind">{{ t.message }}</div>
  </div>
</template>
