<script setup>
// A password field with an eye button to show or hide what you typed.
import { computed, ref, useAttrs } from 'vue'

defineOptions({ inheritAttrs: false })
const model = defineModel({ type: String, default: '' })
defineProps({ id: { type: String, required: true } })
const attrs = useAttrs()
const inputAttrs = computed(() => {
  const { class: _c, style: _s, ...rest } = attrs
  return rest
})
const shown = ref(false)
</script>

<template>
  <div class="relative" :class="attrs.class" :style="attrs.style">
    <input :id="id" v-model="model" v-bind="inputAttrs" :type="shown ? 'text' : 'password'" class="field pr-12" />
    <button
      type="button"
      class="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-r-[10px] text-ink-2 hover:text-ink"
      :aria-label="shown ? 'Hide password' : 'Show password'"
      :aria-pressed="shown"
      :aria-controls="id"
      @click="shown = !shown"
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
        <circle cx="12" cy="12" r="3" />
        <path v-if="shown" d="M3 3l18 18" />
      </svg>
    </button>
  </div>
</template>
