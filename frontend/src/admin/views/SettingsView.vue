<script setup>
import { onMounted, reactive, ref } from 'vue'
import { loadMenu } from '../../shared/menu'
import { toast, toastError } from '../../shared/toast'
import { api } from '../store'

const form = reactive({ shop_name: '', upi_id: '', upi_name: '', pickup_note: '', daily_target_min: 20, daily_target_max: 30, is_open: true })
const ai = ref(null)
const busy = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    Object.assign(form, await api.get('/api/settings'))
    ai.value = await api.get('/api/ai/status')
  } catch (e) { toastError(e) }
})

async function save() {
  busy.value = true
  error.value = ''
  try {
    Object.assign(form, await api.patch('/api/settings', {
      shop_name: form.shop_name, upi_id: form.upi_id, upi_name: form.upi_name, pickup_note: form.pickup_note,
      daily_target_min: Number(form.daily_target_min), daily_target_max: Number(form.daily_target_max),
    }))
    toast('Settings saved.')
    loadMenu(true).catch(() => {})
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="mx-auto max-w-3xl">
    <h1 class="m-0 mb-5 font-display text-3xl font-extrabold">Settings</h1>
    <form class="card grid gap-5 p-5" @submit.prevent="save">
      <div>
        <label class="label" for="s-name">Shop name</label>
        <input id="s-name" v-model="form.shop_name" class="field" minlength="2" maxlength="80" required />
      </div>
      <fieldset class="m-0 grid gap-4 border-0 p-0 sm:grid-cols-2">
        <legend class="mb-2 font-display text-lg font-bold">UPI payments</legend>
        <div>
          <label class="label" for="s-upi">UPI ID</label>
          <input id="s-upi" v-model="form.upi_id" class="field" maxlength="80" placeholder="yourname@okaxis" />
        </div>
        <div>
          <label class="label" for="s-upiname">Name shown in UPI apps</label>
          <input id="s-upiname" v-model="form.upi_name" class="field" maxlength="80" placeholder="Customize Your Crunch" />
        </div>
        <p class="m-0 text-sm text-ink-2 sm:col-span-2">With a UPI ID set, online customers can pay before they arrive. Leave it empty and they pay at the cart.</p>
      </fieldset>
      <div>
        <label class="label" for="s-note">Pickup note for customers</label>
        <textarea id="s-note" v-model="form.pickup_note" class="field min-h-20" maxlength="300" placeholder="e.g. We're outside the college main gate, 4–10 pm." />
      </div>
      <fieldset class="m-0 flex flex-wrap items-end gap-3 border-0 p-0">
        <legend class="mb-2 font-display text-lg font-bold">Daily goal (packets)</legend>
        <div><label class="label" for="s-min">From</label><input id="s-min" v-model="form.daily_target_min" class="field w-24" type="number" min="0" /></div>
        <div><label class="label" for="s-max">To</label><input id="s-max" v-model="form.daily_target_max" class="field w-24" type="number" min="0" /></div>
      </fieldset>
      <p v-if="error" class="error-box m-0">{{ error }}</p>
      <button class="btn btn-dark justify-self-start" type="submit" :disabled="busy">Save settings</button>
    </form>

    <section v-if="ai" class="card mt-5 p-5">
      <h2 class="m-0 font-display text-lg font-bold">AI assistant</h2>
      <p v-if="ai.mode === 'model'" class="m-0 mt-1 text-ink-2">Using <b class="text-ink">{{ ai.model }}</b> through {{ ai.provider }}.</p>
      <p v-else class="m-0 mt-1 text-ink-2">
        Running in basic mode, which understands common questions without any AI service. To use a free model, set
        <code class="rounded bg-sunk px-1">AI_PROVIDER</code>, <code class="rounded bg-sunk px-1">AI_MODEL</code> and (for OpenRouter)
        <code class="rounded bg-sunk px-1">AI_API_KEY</code> in the server's <code class="rounded bg-sunk px-1">.env</code> file and restart it.
      </p>
    </section>
  </div>
</template>
