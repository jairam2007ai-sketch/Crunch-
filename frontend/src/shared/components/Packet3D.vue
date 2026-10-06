<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  build: { type: Object, required: true },
  spin: { type: String, default: 'sway' },     // 'turn' = slow full turns, 'sway' = rocks around the front
  counter: { type: Boolean, default: false },  // steel counter under the packet
  floaters: { type: Boolean, default: false },
  intro: { type: Boolean, default: false },    // fill the packet in on first show
  seed: { type: Number, default: 777 },
  label: { type: String, default: 'Your packet in 3D. Drag to turn it.' },
  hint: { type: String, default: 'Drag to turn' },
})

const host = ref(null)
const fallback = ref(false)
let gl = null

onMounted(async () => {
  try {
    const { createPacket3D } = await import('../packet3d.js') // three.js loads only where a packet is shown
    if (!host.value) return
    gl = createPacket3D(host.value, { spin: props.spin, counter: props.counter, floaters: props.floaters, seed: props.seed, label: props.label })
  } catch {
    gl = null
  }
  if (!gl) { fallback.value = true; return }
  gl.setBuild(props.build, props.intro)
  document.fonts?.ready.then(() => gl?.repaint())
})

watch(() => props.build, (b) => gl?.setBuild(b, true), { deep: true })
onBeforeUnmount(() => { gl?.dispose(); gl = null })

defineExpose({ shake: (reseed = true) => gl?.shake(reseed) })
</script>

<template>
  <div ref="host" class="packet3d">
    <div v-if="fallback" class="fallback" role="img" :aria-label="label">
      <div class="heap" />
      <div class="pouch"><span class="t">Customize Your</span><span class="m">CRUNCH</span></div>
    </div>
    <p v-else class="hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.fallback { aspect-ratio: 4 / 5; display: grid; place-items: end center; padding-bottom: 8%; }
.heap { width: 62%; height: 18%; margin-bottom: -6%; border-radius: 50% 50% 10% 10%; background: radial-gradient(circle at 30% 60%, #E5853A 0 12%, transparent 13%), radial-gradient(circle at 60% 40%, #A9467C 0 6%, transparent 7%), radial-gradient(circle at 70% 70%, #F7CF40 0 7%, transparent 8%), #F0C75E; z-index: 0; }
.pouch { position: relative; width: 66%; height: 62%; border-radius: 10% 10% 16% 16%; background: linear-gradient(90deg, #DDA40A, #F8CC2C 35%, #F5C218 60%, #D69C08); display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 20px 30px -18px rgba(0,0,0,.5); }
.t { font-family: var(--font-hand); color: #fff; background: #1B1A17; padding: 4px 10px 0; font-size: 14px; font-weight: 700; }
.m { font-family: var(--font-display); color: #F5C211; background: #1B1A17; padding: 0 10px 4px; font-size: 30px; font-weight: 800; line-height: 1; }
</style>
