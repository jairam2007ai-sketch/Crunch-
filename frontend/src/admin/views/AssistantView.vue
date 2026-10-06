<script setup>
// Ask about the business in plain words. Actions it suggests wait for your Confirm.
import { nextTick, onMounted, ref } from 'vue'
import { toast, toastError } from '../../shared/toast'
import { api, refreshBadges } from '../store'

const status = ref(null)
const messages = ref([]) // { role, content, tools?, actions? }
const input = ref('')
const busy = ref(false)
const log = ref(null)

const SUGGESTIONS = [
  "What were today's sales?",
  'Compare this week with last week',
  'Which toppings sell the most?',
  'Cash vs UPI this week',
  'Any low stock?',
  'Profit this week',
  'Give me today\'s report',
]
const TOOL_LABEL = {
  get_today_sales: "today's sales", get_sales_by_date: 'sales for a date', get_sales_by_product: 'sales by size',
  get_sales_by_payment: 'cash vs UPI', get_refund_summary: 'refunds', get_inventory_status: 'stock',
  get_top_products: 'top picks', compare_sales_period: 'period comparison', get_profit_summary: 'profit',
  get_daily_report: 'daily report', find_order: 'order lookup', create_refund_request: 'refund',
  approve_refund: 'refund approval', set_online_ordering: 'online ordering',
}

onMounted(async () => {
  try { status.value = await api.get('/api/ai/status') } catch (e) { toastError(e) }
})

async function scrollDown() { await nextTick(); log.value?.scrollTo({ top: log.value.scrollHeight, behavior: 'smooth' }) }

async function send(text) {
  const q = (text ?? input.value).trim()
  if (!q || busy.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  busy.value = true
  scrollDown()
  try {
    const history = messages.value.map((m) => ({ role: m.role, content: m.content })).slice(-12)
    const res = await api.post('/api/ai/chat', { messages: history })
    messages.value.push({ role: 'assistant', content: res.reply, tools: res.tools_used, actions: res.pending_actions.map((a) => ({ ...a, state: 'waiting' })) })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: `Sorry, that didn't work: ${e.message}`, tools: [], actions: [] })
  } finally {
    busy.value = false
    scrollDown()
  }
}

async function confirm(action) {
  action.state = 'working'
  try {
    const res = await api.post('/api/ai/confirm', { action_token: action.action_token })
    action.state = 'done'
    action.result = res.message
    toast(res.message)
    refreshBadges().catch(() => {})
  } catch (e) {
    action.state = 'failed'
    action.result = e.message
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-3xl flex-col" style="min-height: calc(100dvh - 3rem)">
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="m-0 font-display text-3xl font-extrabold">AI assistant</h1>
        <p class="m-0 text-ink-2">Ask about sales, stock, refunds and orders. It answers from your real numbers.</p>
      </div>
      <span v-if="status" class="pill" :class="status.mode === 'model' ? 'bg-leaf-soft text-leaf' : 'bg-sunk text-ink-2'">
        {{ status.mode === 'model' ? `Model: ${status.model}` : 'Basic mode (no AI key set)' }}
      </span>
    </div>
    <p v-if="status?.mode === 'basic'" class="m-0 mb-4 rounded-xl bg-sky-soft px-4 py-3 text-sm text-sky">
      Basic mode understands common questions. For free-form questions in English or Hinglish, add a free OpenRouter key or run Ollama. The README explains how.
    </p>

    <div ref="log" class="card flex-1 overflow-y-auto p-4" aria-live="polite">
      <div v-if="!messages.length" class="grid gap-3 py-6 text-center">
        <p class="m-0 font-hand text-2xl font-bold">What would you like to know?</p>
        <div class="flex flex-wrap justify-center gap-2">
          <button v-for="s in SUGGESTIONS" :key="s" class="btn btn-light btn-sm" type="button" @click="send(s)">{{ s }}</button>
        </div>
      </div>
      <div v-for="(m, i) in messages" :key="i" class="mb-4 flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
        <div class="max-w-[85%]">
          <div class="whitespace-pre-line rounded-2xl px-4 py-3" :class="m.role === 'user' ? 'bg-char text-[#FFF7DA]' : 'bg-sunk'">{{ m.content }}</div>
          <p v-if="m.tools?.length" class="m-0 mt-1 text-xs text-ink-3">Checked: {{ [...new Set(m.tools.map((t) => TOOL_LABEL[t.tool] || t.tool))].join(', ') }}</p>
          <div v-for="a in m.actions" :key="a.action_token" class="mt-2 rounded-xl border-2 border-turmeric bg-turmeric-soft p-3">
            <p class="m-0 font-semibold">{{ a.summary }}</p>
            <div v-if="a.state === 'waiting' || a.state === 'working'" class="mt-2 flex gap-2 pb-1">
              <button class="btn btn-dark btn-sm" type="button" :disabled="a.state === 'working'" @click="confirm(a)">Confirm</button>
              <button class="btn btn-light btn-sm" type="button" @click="a.state = 'skipped'">Don't do it</button>
            </div>
            <p v-else-if="a.state === 'done'" class="m-0 mt-1 text-sm font-semibold text-leaf">Done. {{ a.result }}</p>
            <p v-else-if="a.state === 'failed'" class="m-0 mt-1 text-sm font-semibold text-chili">{{ a.result }}</p>
            <p v-else class="m-0 mt-1 text-sm text-ink-3">Not done.</p>
          </div>
        </div>
      </div>
      <p v-if="busy" class="m-0 text-ink-3">Checking your numbers…</p>
    </div>

    <form class="mt-3 flex gap-2" @submit.prevent="send()">
      <label class="sr-only" for="ask">Ask the assistant</label>
      <input id="ask" v-model="input" class="field flex-1" maxlength="1000" autocomplete="off" placeholder="e.g. How many Loaded packets did we sell this week?" />
      <button class="btn btn-dark" type="submit" :disabled="busy || !input.trim()">Ask</button>
    </form>
  </div>
</template>
