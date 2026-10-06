<script setup>
import { ref } from 'vue'
import PasswordInput from './PasswordInput.vue'

const props = defineProps({
  session: { type: Object, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  notice: { type: String, default: '' },
})
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await props.session.login(email.value.trim(), password.value)
    password.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="grid min-h-dvh place-items-center bg-char px-4 py-10">
    <form class="card w-full max-w-sm p-6" @submit.prevent="submit">
      <div class="mb-5 flex items-center gap-3">
        <span class="mini-lock rounded-lg bg-char px-2.5 py-1.5"><span class="a">Customize Your</span><span class="b">CRUNCH</span></span>
        <div>
          <h1 class="m-0 font-display text-2xl font-extrabold leading-tight">{{ title }}</h1>
          <p v-if="subtitle" class="m-0 text-sm text-ink-2">{{ subtitle }}</p>
        </div>
      </div>
      <p v-if="notice" class="mb-4 rounded-xl bg-sky-soft px-3 py-2.5 text-sm text-sky">{{ notice }}</p>
      <p v-if="session.state.expired" class="error-box mb-4">Your session ended. Please sign in again.</p>
      <label class="label" for="login-email">Email</label>
      <input id="login-email" v-model="email" class="field mb-4" type="email" autocomplete="username" required />
      <label class="label" for="login-password">Password</label>
      <PasswordInput id="login-password" v-model="password" class="mb-4" autocomplete="current-password" required />
      <p v-if="error" class="error-box mb-4">{{ error }}</p>
      <button class="btn btn-dark w-full" type="submit" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
    </form>
  </main>
</template>
