export const inr = (n) => '₹' + Math.round(Number(n) || 0).toLocaleString('en-IN')

export const clock = (iso) => (iso ? new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) : '')

export function dayLabel(ymd, opts = { weekday: 'short', day: 'numeric', month: 'short' }) {
  const [y, m, d] = ymd.split('-').map(Number)
  return new Date(y, m - 1, d, 12).toLocaleDateString('en-IN', opts)
}

export function todayYmd() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function ago(iso) {
  if (!iso) return ''
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const h = Math.floor(mins / 60)
  return h < 24 ? `${h} h ${mins % 60} min ago` : clock(iso)
}

export const STATUS = {
  placed: { label: 'New', cls: 'bg-sky-soft text-sky' },
  preparing: { label: 'Making', cls: 'bg-amber-soft text-amber' },
  ready: { label: 'Ready', cls: 'bg-leaf-soft text-leaf' },
  completed: { label: 'Collected', cls: 'bg-sunk text-ink-2' },
  cancelled: { label: 'Cancelled', cls: 'bg-chili-soft text-chili' },
}

export const PAYMENT = {
  unpaid: { label: 'Unpaid', cls: 'bg-amber-soft text-amber' },
  paid: { label: 'Paid', cls: 'bg-leaf-soft text-leaf' },
  partially_refunded: { label: 'Part refunded', cls: 'bg-chili-soft text-chili' },
  refunded: { label: 'Refunded', cls: 'bg-chili-soft text-chili' },
}

export const METHOD = { cash: 'Cash', upi: 'UPI', pay_at_cart: 'Pay at cart' }

// "Masala chips · Onion, Corn · Garlic mayo · Chaat masala · cheese"
export function describe(sel, names) {
  if (!sel) return ''
  const n = (cat, code) => names?.[cat]?.[code] || code
  const parts = [n('base', sel.base)]
  if (sel.toppings?.length) parts.push(sel.toppings.map((c) => n('topping', c)).join(', '))
  if (sel.sauces?.length) parts.push(sel.sauces.map((c) => n('sauce', c)).join(', '))
  if (sel.seasonings?.length) parts.push(sel.seasonings.map((c) => n('seasoning', c)).join(', '))
  if (sel.cheese) parts.push('cheese')
  return parts.join(' · ')
}
