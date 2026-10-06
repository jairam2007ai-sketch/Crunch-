<script setup>
// One series over time: 2px line, faint area wash, endpoint dot + label, crosshair tooltip.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  points: { type: Array, required: true }, // [{ key, label, value, title }]
  format: { type: Function, default: (v) => String(v) },
  height: { type: Number, default: 240 },
  caption: { type: String, default: '' },
})

const box = ref(null)
const width = ref(600)
const hover = ref(null)
let ro = null
onMounted(() => {
  ro = new ResizeObserver(([e]) => { width.value = Math.max(280, Math.round(e.contentRect.width)) })
  ro.observe(box.value)
})
onBeforeUnmount(() => ro?.disconnect())

const PAD = { l: 56, r: 56, t: 16, b: 30 }
// A clean tick step (1, 2, 2.5 or 5 × a power of ten) giving about four gridlines.
function niceStep(v) {
  if (v <= 0) return 25
  const p = 10 ** Math.floor(Math.log10(v))
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p
  return 10 * p
}
const geo = computed(() => {
  const n = props.points.length
  const raw = Math.max(...props.points.map((p) => p.value), 0) * 1.05
  const step = niceStep(raw / 4)
  const max = Math.max(step, Math.ceil(raw / step) * step)
  const w = width.value, h = props.height
  const iw = w - PAD.l - PAD.r, ih = h - PAD.t - PAD.b
  const x = (i) => PAD.l + (n <= 1 ? iw / 2 : (i * iw) / (n - 1))
  const y = (v) => PAD.t + ih - (v / max) * ih
  const pts = props.points.map((p, i) => [x(i), y(p.value)])
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('')
  const area = `${line}L${x(n - 1).toFixed(1)},${y(0)}L${x(0).toFixed(1)},${y(0)}Z`
  const ticks = []
  for (let v = 0; v <= max + 1e-9; v += step) ticks.push({ v, y: y(v) })
  const every = Math.ceil(n / Math.max(2, Math.floor(iw / 70)))
  const xlabels = props.points.map((p, i) => ({ i, x: x(i), label: p.label })).filter((d) => (n - 1 - d.i) % every === 0)
  return { w, h, x, y, pts, line, area, ticks, xlabels, slot: n > 1 ? iw / (n - 1) : iw }
})

function onMove(e) {
  const r = box.value.getBoundingClientRect()
  const px = e.clientX - r.left
  const g = geo.value
  let best = 0, d = Infinity
  g.pts.forEach((p, i) => { const dd = Math.abs(p[0] - px); if (dd < d) { d = dd; best = i } })
  hover.value = best
}
const last = computed(() => geo.value.pts[geo.value.pts.length - 1])
</script>

<template>
  <figure class="m-0">
    <div ref="box" class="relative w-full" @pointermove="onMove" @pointerleave="hover = null">
      <svg :width="geo.w" :height="geo.h" class="block" role="img" :aria-label="caption">
        <g>
          <line v-for="t in geo.ticks" :key="t.v" :x1="56" :x2="geo.w - 56" :y1="t.y" :y2="t.y" stroke="#ECE5D3" stroke-width="1" />
          <text v-for="t in geo.ticks" :key="'l' + t.v" :x="48" :y="t.y + 4" text-anchor="end" class="fill-ink-3 text-[11px] tabular-nums">{{ format(t.v) }}</text>
        </g>
        <path :d="geo.area" fill="#A67B00" fill-opacity="0.1" />
        <path :d="geo.line" fill="none" stroke="#A67B00" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        <text v-for="l in geo.xlabels" :key="l.i" :x="l.x" :y="geo.h - 8" text-anchor="middle" class="fill-ink-3 text-[11px]">{{ l.label }}</text>
        <template v-if="last">
          <circle :cx="last[0]" :cy="last[1]" r="5" fill="#A67B00" stroke="#fff" stroke-width="2" />
          <text :x="last[0] + 9" :y="last[1] + 4" class="fill-ink text-[12px] font-semibold tabular-nums">{{ format(points[points.length - 1].value) }}</text>
        </template>
        <template v-if="hover !== null">
          <line :x1="geo.pts[hover][0]" :x2="geo.pts[hover][0]" :y1="16" :y2="geo.h - 30" stroke="#7A7260" stroke-width="1" />
          <circle :cx="geo.pts[hover][0]" :cy="geo.pts[hover][1]" r="5" fill="#A67B00" stroke="#fff" stroke-width="2" />
        </template>
      </svg>
      <div v-if="hover !== null" class="pointer-events-none absolute top-0 z-10 rounded-lg bg-char px-3 py-2 text-sm text-[#FFF7DA] shadow-lg"
           :style="{ left: Math.min(geo.pts[hover][0] + 12, geo.w - 170) + 'px' }">
        <div class="text-xs opacity-80">{{ points[hover].title }}</div>
        <div class="font-semibold tabular-nums">{{ format(points[hover].value) }}</div>
        <div v-if="points[hover].extra" class="text-xs opacity-80">{{ points[hover].extra }}</div>
      </div>
    </div>
    <table class="sr-only">
      <caption>{{ caption }}</caption>
      <tr v-for="p in points" :key="p.key"><th>{{ p.title }}</th><td>{{ format(p.value) }}</td></tr>
    </table>
  </figure>
</template>
