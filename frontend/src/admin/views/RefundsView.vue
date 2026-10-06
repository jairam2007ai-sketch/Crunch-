<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { clock, dayLabel, inr } from '../../shared/format'
import { toast, toastError } from '../../shared/toast'
import { api, refreshBadges } from '../store'

const list = ref([])
const notes = reactive({})
const busy = ref(null)

async function load() {
  try { list.value = await api.get('/api/refunds?limit=200') } catch (e) { toastError(e) }
}
onMounted(load)
const pending = computed(() => list.value.filter((r) => r.status === 'pending'))
const done = computed(() => list.value.filter((r) => r.status !== 'pending'))

async function decide(r, approve) {
  busy.value = r.id
  try {
    await api.post(`/api/refunds/${r.id}/${approve ? 'approve' : 'reject'}`, { note: notes[r.id] || '' })
    toast(approve ? `Approved ${inr(r.amount)} refund on order ${r.order_number}.` : `Rejected the refund on order ${r.order_number}.`)
    await load()
    refreshBadges().catch(() => {})
  } catch (e) { toastError(e) } finally { busy.value = null }
}
const STATUS = { approved: 'bg-leaf-soft text-leaf', rejected: 'bg-chili-soft text-chili' }
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="m-0 font-display text-3xl font-extrabold">Refunds</h1>
    <p class="m-0 mb-5 text-ink-2">Sellers ask for refunds at the cart. Nothing is refunded in the books until you approve it here.</p>

    <h2 class="m-0 mb-3 font-display text-xl font-bold">Waiting for you ({{ pending.length }})</h2>
    <p v-if="!pending.length" class="m-0 mb-6 rounded-xl bg-sunk p-4 text-ink-2">No refunds are waiting.</p>
    <div class="mb-8 grid gap-3 md:grid-cols-2">
      <article v-for="r in pending" :key="r.id" class="card border-l-4 border-l-chili p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="m-0 font-display text-2xl font-extrabold">{{ inr(r.amount) }} <span class="text-base font-semibold text-ink-2">by {{ r.method.toUpperCase() }}</span></p>
            <p class="m-0 text-sm text-ink-2">Order {{ r.order_number }} · {{ dayLabel(r.order_date) }} · order total {{ inr(r.order_total) }}</p>
          </div>
          <span class="pill bg-amber-soft text-amber">Pending</span>
        </div>
        <p class="m-0 mt-2">"{{ r.reason }}"</p>
        <p class="m-0 text-sm text-ink-3">Asked by {{ r.requested_by || 'someone' }} at {{ clock(r.created_at) }}</p>
        <input v-model="notes[r.id]" class="field mt-3" maxlength="200" placeholder="Note (optional)" :aria-label="`Note for refund on order ${r.order_number}`" />
        <div class="mt-3 flex gap-2 pb-1">
          <button class="btn btn-green btn-sm" type="button" :disabled="busy === r.id" @click="decide(r, true)">Approve</button>
          <button class="btn btn-light btn-sm" type="button" :disabled="busy === r.id" @click="decide(r, false)">Reject</button>
        </div>
      </article>
    </div>

    <h2 class="m-0 mb-3 font-display text-xl font-bold">History</h2>
    <div class="card overflow-x-auto">
      <table class="w-full min-w-[640px] border-collapse text-sm">
        <thead><tr class="border-b border-line text-left text-xs uppercase tracking-wider text-ink-3">
          <th class="px-4 py-3">Order</th><th class="px-2 py-3">Reason</th><th class="px-2 py-3 text-right">Amount</th><th class="px-2 py-3">Result</th><th class="px-4 py-3">Asked by / decided by</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in done" :key="r.id" class="border-b border-line last:border-0">
            <td class="px-4 py-2.5"><b>#{{ r.order_number }}</b> <span class="text-ink-3">{{ dayLabel(r.order_date) }}</span></td>
            <td class="px-2 py-2.5">{{ r.reason }}<span v-if="r.decision_note" class="block text-xs text-ink-3">{{ r.decision_note }}</span></td>
            <td class="px-2 py-2.5 text-right font-semibold tabular-nums">{{ inr(r.amount) }}</td>
            <td class="px-2 py-2.5"><span class="pill capitalize" :class="STATUS[r.status]">{{ r.status }}</span></td>
            <td class="px-4 py-2.5 text-ink-2">{{ r.requested_by || '—' }} / {{ r.decided_by || '—' }}</td>
          </tr>
          <tr v-if="!done.length"><td colspan="5" class="px-4 py-6 text-center text-ink-3">No decided refunds yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
