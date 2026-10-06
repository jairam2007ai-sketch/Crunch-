// The 3D Crunch packet: a printed stand-up pouch with a heap of chips, toppings,
// sauce drizzle and masala. Pieces drop in as they are chosen; "shake" mixes them.
import * as THREE from 'three'

// Keep the flat, poster-like colours of the original design.
THREE.ColorManagement.enabled = false

const SPICE = { oregano: '#56692B', chilli: '#B0241B', periperi: '#D8452A', tandoori: '#C24E28', chaat: '#74492A' }
const CHIPS = {
  potato: ['#F2C65C', '#E9B84A', '#F6D27A'], masala: ['#E5853A', '#D9702E', '#EE9A4C'],
  kurkure: ['#F2902F', '#E57F26', '#F59E42'], bingo: ['#F2B04C', '#E8A23E', '#F6BE62'],
}
const TOPS = { onion: 0xB8508A, tomato: 0xD93A2B, corn: 0xF8D044, cucumber: 0x8CC152, coriander: 0x2E8B3C }
const SAUCES = { garlic: 0xF7EFD8, tandoori: 0xEC7B3D, periperi: 0xC8281C }

const BOTTOM = -1.12, HEIGHT = 2.14, TOP = BOTTOM + HEIGHT, RIM = TOP - 0.07
const RX = 0.66, RZ = 0.33, HH = 0.54
const heapY = (x, z) => RIM + HH * Math.pow(Math.max(0, 1 - (x / RX) ** 2 - (z / RZ) ** 2), 0.6)
const pouchW = (t) => 0.74 + 0.05 * Math.sin(Math.PI * t) - 0.06 * (1 - t) * (1 - t)
const pouchD = (t) => 0.31 + 0.1 * Math.sin(Math.PI * Math.min(1, 0.15 + t * 0.8))

function rng(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
function hashStr(s) {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return h >>> 0
}
function easeBounce(k) {
  const n = 7.5625, d = 2.75
  if (k < 1 / d) return n * k * k
  if (k < 2 / d) { k -= 1.5 / d; return n * k * k + 0.75 }
  if (k < 2.5 / d) { k -= 2.25 / d; return n * k * k + 0.9375 }
  k -= 2.625 / d; return n * k * k + 0.984375
}
const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Where each piece sits; seeded per ingredient so adding one never moves the others.
function homesFor(kind, id, n, seed) {
  const r = rng((seed ^ hashStr(kind + ':' + id)) >>> 0)
  const out = []
  for (let i = 0; i < n; i++) {
    let x, z
    do { x = r() * 2 - 1; z = r() * 2 - 1 } while (x * x + z * z > 1)
    let y, tilt = 3.2
    if (kind === 'chips') {
      x *= RX * 0.88; z *= RZ * 0.85
      y = heapY(x, z) - 0.05 - Math.pow(r(), 1.3) * 0.34
      if (y < TOP) { x *= 0.8; z *= 0.55 } // keep chips below the rim inside the walls
      tilt = 1.9
    } else {
      x *= RX * 0.9; z *= RZ * 0.86
      y = heapY(x, z) + (kind === 'specks' ? 0.09 : kind === 'cheese' ? 0.075 : 0.06)
    }
    out.push({ p: [x, y, z], r: [(r() - 0.5) * tilt, r() * 6.283, (r() - 0.5) * tilt], s: 0.85 + r() * 0.35, ph: r() * 6.283, d: r() })
  }
  return out
}

function paintPouch(cv) {
  const ctx = cv.getContext('2d'), W = cv.width, H = cv.height, px = W / (2 * Math.PI * 0.78)
  const g = ctx.createLinearGradient(0, 0, 0, H)
  g.addColorStop(0, '#F9D03A'); g.addColorStop(0.6, '#F5C211'); g.addColorStop(1, '#E0A808')
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = 'rgba(140,95,0,.24)'
  for (let x = 0; x < W; x += 12) ctx.fillRect(x, 0, 5, H * 0.075)
  ctx.fillRect(0, H * 0.075, W, 3)

  ctx.save(); ctx.translate(W / 2, H * 0.52); ctx.rotate(-0.05)
  const lw = 1.26 * px, lh = 0.74 * px
  const jag = [[-.5, -.42], [-.36, -.5], [-.1, -.45], [.12, -.52], [.36, -.46], [.5, -.5], [.48, -.1], [.52, .2], [.47, .5], [.2, .45], [-.05, .52], [-.3, .46], [-.5, .5], [-.47, .1], [-.52, -.2]]
  ctx.beginPath()
  jag.forEach(([a, b], i) => (i ? ctx.lineTo(a * lw, b * lh) : ctx.moveTo(a * lw, b * lh)))
  ctx.closePath(); ctx.fillStyle = '#1B1A17'; ctx.fill()
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillStyle = '#FFFFFF'; ctx.font = `700 ${Math.round(0.15 * px)}px Kalam, 'Segoe Print', cursive`
  ctx.fillText('Customize Your', 0, -0.2 * lh)
  let fs = Math.round(0.36 * px)
  const face = (s) => `800 ${s}px 'Baloo 2', 'Arial Rounded MT Bold', sans-serif`
  ctx.font = face(fs)
  const mw = ctx.measureText('CRUNCH').width
  if (mw > lw * 0.8) { fs = Math.floor((fs * lw * 0.8) / mw); ctx.font = face(fs) }
  for (let i = 5; i > 0; i--) { ctx.fillStyle = i > 2 ? '#6E5100' : '#A67B00'; ctx.fillText('CRUNCH', i * 1.5, 0.17 * lh + i * 1.5) }
  ctx.fillStyle = '#F5C211'; ctx.fillText('CRUNCH', 0, 0.17 * lh)
  ctx.strokeStyle = '#F5C211'; ctx.lineWidth = 5; ctx.lineCap = 'round'
  for (const sx of [-1, 1]) for (let k = -1; k <= 1; k++) {
    const x0 = sx * lw * 0.43, y0 = 0.17 * lh + k * 0.1 * px
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + sx * 0.06 * px, y0 + k * 0.035 * px); ctx.stroke()
  }
  ctx.restore()

  ctx.fillStyle = '#1B1A17'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.font = `700 ${Math.round(0.11 * px)}px Kalam, 'Segoe Print', cursive`
  ctx.fillText('Fresh · Tasty · Affordable', W / 2, H * 0.52 + 0.56 * px)
  const vs = 0.12 * px, vx = W / 2 + 0.46 * px, vy = H * 0.84
  ctx.fillStyle = '#FFFFFF'; ctx.fillRect(vx, vy, vs, vs)
  ctx.strokeStyle = '#1E6E3A'; ctx.lineWidth = 4; ctx.strokeRect(vx, vy, vs, vs)
  ctx.fillStyle = '#1E6E3A'; ctx.beginPath(); ctx.arc(vx + vs / 2, vy + vs / 2, vs * 0.26, 0, 6.283); ctx.fill()

  ctx.fillStyle = '#1B1A17'
  for (const cx of [0, W]) { // back of the pack, centred on the seam so it wraps
    ctx.font = `700 ${Math.round(0.2 * px)}px Kalam, 'Segoe Print', cursive`
    ctx.fillText('Freshly mixed', cx, H * 0.42)
    ctx.fillText('just for you!', cx, H * 0.42 + 0.26 * px)
    ctx.font = `700 ${Math.round(0.09 * px)}px Hind, 'Segoe UI', sans-serif`
    ctx.fillText('100% VEG  ·  MADE AT THE CART', cx, H * 0.42 + 0.55 * px)
  }
}

function webglOK() {
  try {
    const c = document.createElement('canvas')
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')))
  } catch { return false }
}

export function createPacket3D(host, opts = {}) {
  if (!webglOK()) return null
  let renderer
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }) } catch { return null }
  const T = THREE
  renderer.outputColorSpace = T.LinearSRGBColorSpace
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1))
  renderer.setClearColor(0x000000, 0)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = T.PCFShadowMap
  const canvas = renderer.domElement
  canvas.setAttribute('role', 'img')
  canvas.setAttribute('aria-label', opts.label || 'Your packet in 3D. Drag to turn it.')
  host.insertBefore(canvas, host.firstChild)

  const scene = new T.Scene()
  const camera = new T.PerspectiveCamera(32, 0.8, 0.1, 60)
  const camBase = new T.Vector3(0, 2.5, 6.1), look = new T.Vector3(0, 0.14, 0)
  camera.position.copy(camBase); camera.lookAt(look)

  // Physical light units: multiply by PI to match the original look.
  const PI = Math.PI
  scene.add(new T.HemisphereLight(0xfff4dc, 0x5a4a32, 0.72 * PI))
  const key = new T.DirectionalLight(0xffffff, 0.92 * PI)
  key.position.set(2.6, 5.5, 4.2)
  key.castShadow = true
  key.shadow.mapSize.set(1024, 1024)
  Object.assign(key.shadow.camera, { left: -2.6, right: 2.6, top: 3, bottom: -2.4, near: 0.5, far: 16 })
  key.shadow.camera.updateProjectionMatrix()
  key.shadow.bias = -0.0012
  scene.add(key)
  const rim = new T.DirectionalLight(0xffd98a, 0.5 * PI); rim.position.set(-4, 3, -3); scene.add(rim)
  const fill = new T.DirectionalLight(0xffffff, 0.22 * PI); fill.position.set(-2.5, 1, 5); scene.add(fill)

  const disposables = []
  const keep = (x) => { disposables.push(x); return x }
  const std = (color, rough, extra) => keep(new T.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...(extra || {}) }))

  if (opts.counter) { // SS 304 counter top, brushed
    const sc = document.createElement('canvas'); sc.width = 256; sc.height = 256
    const sx = sc.getContext('2d'); sx.fillStyle = '#9FA7AE'; sx.fillRect(0, 0, 256, 256)
    for (let i = 0; i < 420; i++) {
      sx.fillStyle = (i % 2 ? 'rgba(255,255,255,' : 'rgba(70,78,86,') + (Math.random() * 0.12).toFixed(3) + ')'
      sx.fillRect(0, Math.random() * 256, 256, 1)
    }
    const st = keep(new T.CanvasTexture(sc)); st.wrapS = st.wrapT = T.RepeatWrapping; st.repeat.set(3, 1)
    const counter = new T.Mesh(keep(new T.BoxGeometry(9, 0.24, 4)), keep(new T.MeshStandardMaterial({ map: st, roughness: 0.3, metalness: 0.25 })))
    counter.position.set(0, BOTTOM - 0.12, 0.6); counter.receiveShadow = true; scene.add(counter)
  } else {
    const ground = new T.Mesh(keep(new T.PlaneGeometry(8, 8)), keep(new T.ShadowMaterial({ opacity: 0.3 })))
    ground.rotation.x = -PI / 2; ground.position.y = BOTTOM; ground.receiveShadow = true; scene.add(ground)
  }

  const rig = new T.Group(), spin = new T.Group(), heap = new T.Group()
  scene.add(rig); rig.add(spin); spin.add(heap)

  // pouch: a cylinder pushed into a stand-up pouch with a crimped, open mouth
  const tcv = document.createElement('canvas'); tcv.width = 1536; tcv.height = 672
  paintPouch(tcv)
  const tex = keep(new T.CanvasTexture(tcv))
  tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy())
  const pg = keep(new T.CylinderGeometry(1, 1, 1, 72, 30, true, PI, PI * 2))
  const pp = pg.attributes.position
  for (let i = 0; i < pp.count; i++) {
    const x = pp.getX(i), y = pp.getY(i), z = pp.getZ(i)
    const t = y + 0.5, th = Math.atan2(x, z), s = Math.sin(th), c = Math.cos(th)
    const crimp = t > 0.9 ? (Math.sin(th * 34) * 0.02 * (t - 0.9)) / 0.1 : 0
    pp.setXYZ(i, s * pouchW(t), BOTTOM + t * HEIGHT + crimp, c * pouchD(t) * (1 - 0.12 * Math.pow(Math.abs(s), 6)))
  }
  pg.computeVertexNormals()
  const outer = new T.Mesh(pg, keep(new T.MeshStandardMaterial({ map: tex, roughness: 0.36, metalness: 0.12 })))
  outer.castShadow = true
  const inner = new T.Mesh(pg, std(0xB3850A, 0.75, { side: T.BackSide }))
  inner.receiveShadow = true
  const capG = keep(new T.CircleGeometry(1, 48)); capG.rotateX(PI / 2)
  const cap = new T.Mesh(capG, std(0xE3AD0A, 0.5))
  cap.scale.set(pouchW(0), 1, pouchD(0)); cap.position.y = BOTTOM + 0.002
  spin.add(outer, inner, cap)

  // ingredient shapes
  const geos = {}
  {
    const chip = keep(new T.CircleGeometry(0.16, 24)), cp = chip.attributes.position
    for (let i = 0; i < cp.count; i++) {
      let x = cp.getX(i), y = cp.getY(i)
      const a = Math.atan2(y, x), wob = 1 + 0.07 * Math.sin(a * 5 + 1) + 0.04 * Math.sin(a * 9)
      x *= wob; y *= wob * 0.8
      cp.setXYZ(i, x, y, 2.2 * (x * x - 0.8 * y * y) + 0.01 * Math.sin(a * 7)) // saddle-curved like a real chip
    }
    chip.computeVertexNormals(); geos.chip = chip

    const kp = []
    for (let i = 0; i < 8; i++) kp.push(new T.Vector3(-0.17 + i * 0.048, Math.sin(i * 1.7) * 0.04, Math.cos(i * 2.4) * 0.035))
    geos.kurkure = keep(new T.TubeGeometry(new T.CatmullRomCurve3(kp), 36, 0.036, 8, false))

    const sh = new T.Shape(), R = 0.15
    const P = [0, 1, 2].map((i) => { const a = PI / 2 + (i * 2 * PI) / 3; return [Math.cos(a) * R, Math.sin(a) * R] })
    for (let i = 0; i < 3; i++) {
      const c0 = P[i], c1 = P[(i + 1) % 3], cp0 = P[(i + 2) % 3]
      const ax = c0[0] + (cp0[0] - c0[0]) * 0.18, ay = c0[1] + (cp0[1] - c0[1]) * 0.18
      const bx = c0[0] + (c1[0] - c0[0]) * 0.18, by = c0[1] + (c1[1] - c0[1]) * 0.18
      if (i === 0) sh.moveTo(ax, ay); else sh.lineTo(ax, ay)
      sh.quadraticCurveTo(c0[0], c0[1], bx, by)
    }
    sh.closePath()
    const bingo = keep(new T.ExtrudeGeometry(sh, { depth: 0.012, bevelEnabled: true, bevelThickness: 0.008, bevelSize: 0.01, bevelSegments: 2, curveSegments: 5 }))
    bingo.center()
    const bp = bingo.attributes.position
    for (let i = 0; i < bp.count; i++) { const x = bp.getX(i); bp.setZ(i, bp.getZ(i) + 1.4 * x * x) }
    bingo.computeVertexNormals(); geos.bingo = bingo

    geos.onion = keep(new T.TorusGeometry(0.04, 0.011, 6, 18, PI * 1.25))
    geos.tomato = keep(new T.BoxGeometry(0.06, 0.05, 0.045))
    geos.corn = keep(new T.SphereGeometry(0.024, 10, 8)); geos.corn.scale(1, 0.8, 1)
    geos.cucumber = keep(new T.CylinderGeometry(0.04, 0.04, 0.018, 14))
    geos.coriander = keep(new T.CircleGeometry(0.035, 7)); geos.coriander.scale(1, 0.7, 1)
    geos.cheese = keep(new T.BoxGeometry(0.12, 0.018, 0.026))
    geos.speck = keep(new T.BoxGeometry(0.018, 0.018, 0.018))
    geos.flake = keep(new T.BoxGeometry(0.03, 0.006, 0.02))
  }
  const mats = { cheese: std(0xFFE27D, 0.5) }
  for (const [k, v] of Object.entries(TOPS)) mats[k] = std(v, k === 'coriander' ? 0.6 : 0.35, k === 'coriander' ? { side: T.DoubleSide } : undefined)
  for (const [k, v] of Object.entries(SPICE)) mats['sp_' + k] = std(v, 0.9)
  const sauceMats = Object.fromEntries(Object.entries(SAUCES).map(([k, v]) => [k, std(v, 0.24)]))

  let seed = opts.seed || 4242
  let shakeStart = 0, shakeJ = 0, shakeK = 0, shakeReseed = true, shakeSwapped = false
  const dummy = new T.Object3D(), tmpC = new T.Color()

  class Layer {
    constructor(spec, geo, mat, colors, drop) {
      this.spec = spec; this.mat = mat
      this.homes = homesFor(spec.kind, spec.id, spec.n, seed)
      this.inst = new T.InstancedMesh(geo, mat, spec.n)
      this.inst.castShadow = !!spec.cast; this.inst.receiveShadow = true; this.inst.frustumCulled = false
      if (colors) { for (let i = 0; i < spec.n; i++) this.inst.setColorAt(i, tmpC.set(colors[i % colors.length])); this.inst.instanceColor.needsUpdate = true }
      this.drop = drop; this.die = 0; this.dirty = true
      heap.add(this.inst)
    }
    write(now) {
      let moving = false
      for (let i = 0; i < this.homes.length; i++) {
        const h = this.homes[i]
        let y = h.p[1], s = h.s, rx = h.r[0]
        if (this.drop) {
          const t = (now - this.drop.start) / 1000 - h.d * this.drop.spread
          if (t < 0) { s = 0.0001; moving = true } else if (t < 0.65) { const k = t / 0.65; y += (1 - easeBounce(k)) * 2.6; rx += (1 - k) * 4; moving = true }
        }
        if (this.die) { const k = Math.min(1, (now - this.die) / 280); s *= Math.max(0.0001, 1 - k); if (k < 1) moving = true }
        if (shakeJ > 0) { y += Math.abs(Math.sin(shakeK * 26 + h.ph)) * 0.18 * shakeJ; rx += Math.sin(shakeK * 19 + h.ph) * 0.7 * shakeJ }
        dummy.position.set(h.p[0], y, h.p[2]); dummy.rotation.set(rx, h.r[1], h.r[2]); dummy.scale.setScalar(s); dummy.updateMatrix()
        this.inst.setMatrixAt(i, dummy.matrix)
      }
      this.inst.instanceMatrix.needsUpdate = true
      if (this.drop && !moving) this.drop = null
      this.dirty = false
      return moving
    }
    reseed() { this.homes = homesFor(this.spec.kind, this.spec.id, this.spec.n, seed); this.dirty = true }
    remove() { heap.remove(this.inst); this.inst.dispose(); if (this.ownMat) this.mat.dispose() }
  }

  function sauceCurve(id, idx) {
    const r = rng((seed ^ hashStr('sauce:' + id)) >>> 0)
    const zig = 2.5 + r(), ph = r() * 6.283, pts = []
    for (let i = 0; i <= 40; i++) {
      const u = i / 40, x = (-0.86 + 1.72 * u) * RX
      const z = Math.sin(u * zig * 2 * PI + ph) * RZ * 0.7
      pts.push(new T.Vector3(x, heapY(x, z) + 0.085 + idx * 0.015, z))
    }
    return new T.CatmullRomCurve3(pts)
  }
  class Sauce {
    constructor(id, idx, grow) {
      this.id = id; this.idx = idx
      this.mesh = new T.Mesh(this.make(), sauceMats[id] || sauceMats.garlic)
      this.mesh.receiveShadow = true
      heap.add(this.mesh)
      this.grow = grow; this.die = 0; this.dirty = true
      if (grow) this.mesh.geometry.setDrawRange(0, 0)
    }
    make() { return new T.TubeGeometry(sauceCurve(this.id, this.idx), 140, 0.024, 8, false) }
    reseed() { const old = this.mesh.geometry; this.mesh.geometry = this.make(); old.dispose(); this.dirty = true }
    write(now) {
      const g = this.mesh.geometry, full = g.index ? g.index.count : g.attributes.position.count
      let moving = false
      if (this.grow) { // the drizzle draws itself across the heap
        const k = Math.min(1, Math.max(0, (now - this.grow.start) / 750))
        g.setDrawRange(0, Math.floor((full * k) / 3) * 3)
        if (k < 1) moving = true; else { this.grow = null; g.setDrawRange(0, Infinity) }
      }
      if (this.die) { const k = Math.min(1, (now - this.die) / 260); g.setDrawRange(0, Math.floor((full * (1 - k)) / 3) * 3); if (k < 1) moving = true }
      this.mesh.position.y = shakeJ > 0 ? Math.abs(Math.sin(shakeK * 26 + this.idx)) * 0.14 * shakeJ : 0
      this.dirty = false
      return moving
    }
    remove() { heap.remove(this.mesh); this.mesh.geometry.dispose() }
  }

  const L = { chips: null, cheese: null, tops: {}, sauces: {}, specks: {} }
  const dying = []
  let cur = null
  const allLayers = () => [L.chips, L.cheese, ...Object.values(L.tops), ...Object.values(L.sauces), ...Object.values(L.specks), ...dying].filter(Boolean)
  const kill = (x, now, anim) => { if (anim) { x.die = now; dying.push(x) } else x.remove() }
  function syncSet(map, wanted, make, now, anim) {
    for (const id of Object.keys(map)) if (!wanted.includes(id)) { kill(map[id], now, anim); delete map[id] }
    wanted.forEach((id, i) => { if (!map[id]) { const m = make(id, i); if (m) map[id] = m } })
  }

  function setBuild(b, animate) {
    if (!b) return
    const now = performance.now(), anim = !!animate && !reduceMotion()
    const big = !!b.cheese || b.size === 'loaded'
    if (!cur || cur.base !== b.base || cur.big !== big) {
      if (L.chips) kill(L.chips, now, anim)
      const kind = b.base === 'kurkure' ? 'kurkure' : b.base === 'bingo' ? 'bingo' : 'chip'
      const mat = new T.MeshStandardMaterial({ color: 0xffffff, roughness: kind === 'kurkure' ? 0.92 : 0.55, side: T.DoubleSide })
      L.chips = new Layer({ kind: 'chips', id: 'all', n: big ? 48 : 38, cast: true }, geos[kind], mat, CHIPS[b.base] || CHIPS.potato,
        anim ? { start: now + 120, spread: 0.55 } : null)
      L.chips.ownMat = true
    }
    const wantCheese = !!(b.cheese ?? b.size === 'loaded')
    if (wantCheese && !L.cheese) L.cheese = new Layer({ kind: 'cheese', id: 'c', n: 20 }, geos.cheese, mats.cheese, null, anim ? { start: now + 380, spread: 0.4 } : null)
    if (!wantCheese && L.cheese) { kill(L.cheese, now, anim); L.cheese = null }
    syncSet(L.tops, b.toppings || [], (id) => (geos[id] ? new Layer({ kind: 'top', id, n: 13 }, geos[id], mats[id], null, anim ? { start: now + 240, spread: 0.45 } : null) : null), now, anim)
    syncSet(L.sauces, b.sauces || [], (id, i) => (SAUCES[id] ? new Sauce(id, i, anim ? { start: now + 620 } : null) : null), now, anim)
    syncSet(L.specks, b.seasonings || [], (id) => (mats['sp_' + id]
      ? new Layer({ kind: 'specks', id, n: 80 }, id === 'chilli' || id === 'oregano' ? geos.flake : geos.speck, mats['sp_' + id], null, anim ? { start: now + 880, spread: 0.4 } : null)
      : null), now, anim)
    cur = { base: b.base, big }
    wake()
  }

  let shakeNext = null
  function shake(reseed = true) {
    const next = () => { seed = (Math.imul(seed, 48271) + 11) >>> 0; allLayers().forEach((l) => l.reseed?.()) }
    if (reduceMotion()) { if (reseed) next(); wake(); return }
    shakeStart = performance.now(); shakeReseed = reseed; shakeSwapped = false; shakeNext = next
    wake()
  }

  // floating chips around the hero packet, for depth
  const floaters = []
  if (opts.floaters) {
    const spots = [[-1.12, 1.3, -0.5], [1.1, 1.0, -0.3], [-1.18, -0.2, 0.3], [1.15, -0.55, 0.4], [-0.82, -0.95, 1.05], [0.9, 1.75, -0.9]]
    const kinds = ['chip', 'bingo', 'kurkure', 'chip', 'bingo', 'chip']
    const cols = [0xF2C65C, 0xF2B04C, 0xF2902F, 0xE5853A, 0xF6BE62, 0xF2C65C]
    spots.forEach((s, i) => {
      const m = new T.Mesh(geos[kinds[i]], std(cols[i], kinds[i] === 'kurkure' ? 0.9 : 0.55, { side: T.DoubleSide }))
      m.position.set(...s); m.scale.setScalar(1.25); m.rotation.set(i, i * 1.3, i * 0.7); m.castShadow = true
      scene.add(m); floaters.push({ m, y: s[1], ph: i * 1.7 })
    })
  }

  // drag to turn; the mouse nudges the camera for parallax
  let dragging = false, lastX = 0, velY = 0, rotY = opts.spin === 'turn' ? -0.5 : 0, baseRot = 0, idleUntil = 0
  const ptr = { x: 0, y: 0 }, camOff = { x: 0, y: 0 }
  const onDown = (e) => { dragging = true; lastX = e.clientX; velY = 0; try { canvas.setPointerCapture(e.pointerId) } catch { /* ignore */ } canvas.classList.add('grabbing'); wake() }
  const onMove = (e) => {
    if (e.pointerType === 'mouse') {
      const r = canvas.getBoundingClientRect()
      ptr.x = ((e.clientX - r.left) / r.width - 0.5) * 2; ptr.y = ((e.clientY - r.top) / r.height - 0.5) * 2
    }
    if (dragging) { const dx = e.clientX - lastX; lastX = e.clientX; rotY += dx * 0.012; velY = dx * 0.012 }
    wake()
  }
  const onUp = () => {
    if (!dragging) return
    dragging = false; canvas.classList.remove('grabbing')
    idleUntil = performance.now() + 2500
    baseRot = Math.round(rotY / (PI * 2)) * PI * 2
  }
  const onLeave = () => { ptr.x = 0; ptr.y = 0 }
  canvas.addEventListener('pointerdown', onDown)
  canvas.addEventListener('pointermove', onMove)
  canvas.addEventListener('pointerup', onUp)
  canvas.addEventListener('pointercancel', onUp)
  canvas.addEventListener('pointerleave', onLeave)

  let raf = 0, visible = true, last = performance.now(), dead = false
  function wake() { if (!raf && visible && !dead) { last = performance.now(); raf = requestAnimationFrame(frame) } }
  function frame(now) {
    raf = 0
    const dt = Math.min(0.05, Math.max(0, (now - last) / 1000)); last = now
    const still = reduceMotion()
    if (!dragging) {
      rotY += velY; velY *= 0.9
      if (!still && now > idleUntil) {
        if (opts.spin === 'turn') rotY += dt * 0.35
        else { const target = baseRot + Math.sin((now / 1000) * 0.5) * 0.4; rotY += (target - rotY) * Math.min(1, dt * 1.2) }
      }
    }
    spin.rotation.y = rotY
    camOff.x += (ptr.x * 0.45 - camOff.x) * Math.min(1, dt * 3)
    camOff.y += (ptr.y * 0.3 - camOff.y) * Math.min(1, dt * 3)
    camera.position.set(camBase.x + camOff.x, camBase.y - camOff.y, camBase.z)
    camera.lookAt(look)

    let all = allLayers()
    if (shakeStart) {
      const k = (now - shakeStart) / 1100
      if (k >= 1) { shakeStart = 0; shakeJ = 0; rig.rotation.set(0, 0, 0); rig.position.y = 0; all.forEach((l) => { l.dirty = true }) }
      else {
        const decay = Math.pow(1 - k, 1.3)
        rig.rotation.z = Math.sin(k * PI * 9) * 0.15 * decay
        rig.rotation.x = Math.sin(k * PI * 7) * 0.07 * decay
        rig.position.y = Math.abs(Math.sin(k * PI * 9)) * 0.2 * decay
        shakeJ = decay; shakeK = k
        if (shakeReseed && !shakeSwapped && k > 0.45 && shakeNext) { shakeSwapped = true; shakeNext(); all = allLayers() }
      }
    }
    let moving = false
    for (const l of all) if (l.dirty || l.drop || l.grow || l.die || shakeStart) moving = l.write(now) || moving
    for (let i = dying.length - 1; i >= 0; i--) if (now - dying[i].die > 320) { dying[i].remove(); dying.splice(i, 1) }
    if (!still) for (const f of floaters) { f.m.position.y = f.y + Math.sin((now / 1000) * 0.9 + f.ph) * 0.08; f.m.rotation.x += dt * 0.35; f.m.rotation.y += dt * 0.25 }

    renderer.render(scene, camera)
    if ((moving || dragging || shakeStart || dying.length || Math.abs(velY) > 0.0005 || !still) && visible) raf = requestAnimationFrame(frame)
  }

  function resize() {
    const w = canvas.clientWidth || host.clientWidth
    if (!w) return
    const h = Math.round(w * 1.25)
    renderer.setSize(w, h, false)
    camera.aspect = w / h; camera.updateProjectionMatrix()
    wake()
  }
  const ro = 'ResizeObserver' in window ? new ResizeObserver(resize) : null
  ro?.observe(host)
  const io = 'IntersectionObserver' in window
    ? new IntersectionObserver((es) => { visible = es[es.length - 1].isIntersecting; if (visible) wake() })
    : null
  io?.observe(canvas)
  resize()

  return {
    setBuild,
    shake,
    repaint() { paintPouch(tcv); tex.needsUpdate = true; wake() },
    dispose() {
      dead = true
      if (raf) cancelAnimationFrame(raf)
      ro?.disconnect(); io?.disconnect()
      canvas.removeEventListener('pointerdown', onDown)
      canvas.removeEventListener('pointermove', onMove)
      canvas.removeEventListener('pointerup', onUp)
      canvas.removeEventListener('pointercancel', onUp)
      canvas.removeEventListener('pointerleave', onLeave)
      allLayers().forEach((l) => l.remove())
      disposables.forEach((d) => d.dispose?.())
      renderer.dispose()
      renderer.forceContextLoss?.()
      canvas.remove()
    },
  }
}
