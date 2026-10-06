<script setup>
// Columns from one baseline: ≤24px thick, 4px rounded tops, hover tooltip per column.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  bars: { type: Array, required: true }, // [{ key, label, value, title }]
  format: { type: Function, default: (v) => String(v) },
  height: { type: Number, default: 200 },
  caption: { type: String, default: '' },
  color: { type: String, default: '#A67B00' },
})
const box = ref(null)
const width = ref(500)
const hover = ref(null)
let ro = null
onMounted(() => { ro = new ResizeObserver(([e]) => { width.value = Math.max(260, Math.round(e.contentRect.width)) }); ro.observe(box.value) })
onBeforeUnmount(() => ro?.disconnect())

const PAD = { l: 34, r: 8, t: 14, b: 26 }
const geo = computed(() => {
  const n = props.bars.length, w = width.value, h = props.height
  const raw = Math.max(...props.bars.map((b) => b.value), 0)
  const step = raw <= 5 ? 1 : raw <= 10 ? 2 : raw <= 25 ? 5 : raw <= 50 ? 10 : 20
  const max = Math.max(step * 2, Math.ceil(raw / step) * step)
  const iw = w - PAD.l - PAD.r, ih = h - PAD.t - PAD.b
  const slot = iw / Math.max(1, n)
  const bw = Math.min(24, slot * 0.6)
  const y = (v) => PAD.t + ih - (v / max) * ih
  const ticks = []
  for (let v = 0; v <= max; v += step) ticks.push({ v, y: y(v) })
  const cols = props.bars.map((b, i) => {
    const cx = PAD.l + slot * i + slot / 2
    const top = y(b.value), base = y(0), hgt = base - top, r = Math.min(4, hgt)
    const x0 = cx - bw / 2, x1 = cx + bw / 2
    const d = hgt <= 0 ? '' : `M${x0},${base}V${top + r}Q${x0},${top} ${x0 + r},${top}H${x1 - r}Q${x1},${top} ${x1},${top + r}V${base}Z`
    return { ...b, cx, d, top, slotX: PAD.l + slot * i, slot }
  })
  const every = Math.ceil(n / Math.max(2, Math.floor(iw / 44)))
  return { w, h, ticks, cols, every }
})
</script>

<template>
  <figure class="m-0">
    <div ref="box" class="relative w-full" @pointerleave="hover = null">
      <svg :width="geo.w" :height="geo.h" class="block" role="img" :aria-label="caption">
        <line v-for="t in geo.ticks" :key="t.v" :x1="34" :x2="geo.w - 8" :y1="t.y" :y2="t.y" stroke="#ECE5D3" stroke-width="1" />
        <text v-for="t in geo.ticks" :key="'t' + t.v" :x="28" :y="t.y + 4" text-anchor="end" class="fill-ink-3 text-[11px] tabular-nums">{{ t.v }}</text>
        <g v-for="(c, i) in geo.cols" :key="c.key">
          <rect :x="c.slotX" :y="14" :width="c.slot" :height="geo.h - 40" fill="transparent" @pointerenter="hover = i" />
          <path v-if="c.d" :d="c.d" :fill="color" :fill-opacity="hover === null || hover === i ? 1 : 0.45" pointer-events="none" />
          <text v-if="i % geo.every === 0" :x="c.cx" :y="geo.h - 8" text-anchor="middle" class="fill-ink-3 text-[11px]">{{ c.label }}</text>
        </g>
      </svg>
      <div v-if="hover !== null" class="pointer-events-none absolute z-10 rounded-lg bg-char px-3 py-2 text-sm text-[#FFF7DA] shadow-lg"
           :style="{ left: Math.min(geo.cols[hover].cx + 10, geo.w - 150) + 'px', top: Math.max(0, geo.cols[hover].top - 50) + 'px' }">
        <div class="text-xs opacity-80">{{ bars[hover].title }}</div>
        <div class="font-semibold tabular-nums">{{ format(bars[hover].value) }}</div>
      </div>
    </div>
    <table class="sr-only">
      <caption>{{ caption }}</caption>
      <tr v-for="b in bars" :key="b.key"><th>{{ b.title }}</th><td>{{ format(b.value) }}</td></tr>
    </table>
  </figure>
</template>
