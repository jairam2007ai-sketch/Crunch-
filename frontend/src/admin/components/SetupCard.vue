<script setup>
// First run: no accounts exist yet, so the owner creates theirs here.
import { reactive, ref } from 'vue'
import { publicApi } from '../../shared/api'
import PasswordInput from '../../shared/components/PasswordInput.vue'

const props = defineProps({
  session: { type: Object, required: true },
  allowed: { type: Boolean, default: true },
})
const form = reactive({ name: '', email: '', password: '', again: '' })
const error = ref('')
const busy = ref(false)

async function create() {
  error.value = ''
  if (form.password !== form.again) { error.value = "The two passwords don't match."; return }
  busy.value = true
  try {
    await publicApi.post('/api/setup/owner', { name: form.name, email: form.email, password: form.password, role: 'owner' })
    await props.session.login(form.email.trim(), form.password)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="grid min-h-dvh place-items-center bg-char px-4 py-10">
    <form class="card w-full max-w-md p-6" @submit.prevent="create">
      <div class="mb-4 flex items-center gap-3">
        <span class="mini-lock rounded-lg bg-char px-2.5 py-1.5"><span class="a">Customize Your</span><span class="b">CRUNCH</span></span>
        <div>
          <h1 class="m-0 font-display text-2xl font-extrabold leading-tight">Welcome! Create your owner account</h1>
        </div>
      </div>
      <template v-if="allowed">
        <p class="m-0 mb-5 text-ink-2">This is the first time Crunch has started. You'll use this account to sign in here, see your sales and add your team.</p>
        <label class="label" for="su-name">Your name</label>
        <input id="su-name" v-model="form.name" class="field mb-4" autocomplete="name" minlength="2" maxlength="80" required />
        <label class="label" for="su-email">Email</label>
        <input id="su-email" v-model="form.email" class="field mb-4" type="email" autocomplete="username" required />
        <label class="label" for="su-pw">Password (8 or more characters)</label>
        <PasswordInput id="su-pw" v-model="form.password" class="mb-4" autocomplete="new-password" minlength="8" required />
        <label class="label" for="su-pw2">Type the password again</label>
        <PasswordInput id="su-pw2" v-model="form.again" class="mb-4" autocomplete="new-password" minlength="8" required />
        <p v-if="error" class="error-box mb-4">{{ error }}</p>
        <button class="btn btn-dark w-full" type="submit" :disabled="busy">{{ busy ? 'Creating…' : 'Create account and sign in' }}</button>
      </template>
      <p v-else class="m-0 text-ink-2">
        No owner account exists yet. For safety it can only be created on the computer running the server,
        or by setting <code class="rounded bg-sunk px-1">OWNER_EMAIL</code> and <code class="rounded bg-sunk px-1">OWNER_PASSWORD</code> on your host.
      </p>
    </form>
  </main>
</template>
