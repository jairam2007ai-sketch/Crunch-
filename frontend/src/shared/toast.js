import { reactive } from 'vue'

export const toasts = reactive([])
let id = 0

export function toast(message, kind = 'info', ms = 3600) {
  const t = { id: ++id, message, kind }
  toasts.push(t)
  setTimeout(() => {
    const i = toasts.indexOf(t)
    if (i >= 0) toasts.splice(i, 1)
  }, ms)
}

export const toastError = (e) => toast(e?.message || String(e), 'error', 5200)

// Re-run a loader every few seconds while the tab is visible.
export function poll(fn, ms) {
  let timer = null
  const tick = () => { if (document.visibilityState === 'visible') fn() }
  const onVis = () => { if (document.visibilityState === 'visible') fn() }
  timer = setInterval(tick, ms)
  document.addEventListener('visibilitychange', onVis)
  return () => { clearInterval(timer); document.removeEventListener('visibilitychange', onVis) }
}

// A short two-tone beep for new online orders (browsers allow it after the first tap).
let audioCtx = null
export function beep() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
    const t = audioCtx.currentTime
    ;[880, 1320].forEach((f, i) => {
      const o = audioCtx.createOscillator()
      const g = audioCtx.createGain()
      o.frequency.value = f
      g.gain.setValueAtTime(0.0001, t + i * 0.16)
      g.gain.exponentialRampToValueAtTime(0.25, t + i * 0.16 + 0.02)
      g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.16 + 0.15)
      o.connect(g).connect(audioCtx.destination)
      o.start(t + i * 0.16)
      o.stop(t + i * 0.16 + 0.16)
    })
  } catch { /* no audio available */ }
}
