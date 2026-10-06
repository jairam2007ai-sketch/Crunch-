<script setup>
import { onMounted, reactive, ref } from 'vue'
import PasswordInput from '../../shared/components/PasswordInput.vue'
import { toast, toastError } from '../../shared/toast'
import { api, session } from '../store'

const users = ref([])
const form = reactive({ name: '', email: '', password: '', role: 'seller' })
const resetFor = ref(null)
const newPassword = ref('')
const busy = ref(false)

async function load() {
  try { users.value = await api.get('/api/users') } catch (e) { toastError(e) }
}
onMounted(load)

async function add() {
  busy.value = true
  try {
    const u = await api.post('/api/users', { ...form })
    toast(`${u.name} can now sign in to the ${u.role === 'owner' ? 'admin' : 'seller'} site with ${u.email}.`)
    Object.assign(form, { name: '', email: '', password: '', role: 'seller' })
    load()
  } catch (e) { toastError(e) } finally { busy.value = false }
}
async function setActive(u, active) {
  try { await api.patch(`/api/users/${u.id}`, { is_active: active }); toast(active ? `${u.name} can sign in again.` : `${u.name} can no longer sign in.`); load() } catch (e) { toastError(e) }
}
async function resetPassword(u) {
  try {
    await api.patch(`/api/users/${u.id}`, { password: newPassword.value })
    toast(`New password set for ${u.name}. Tell them in person.`)
    resetFor.value = null
    newPassword.value = ''
  } catch (e) { toastError(e) }
}
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="m-0 font-display text-3xl font-extrabold">Team</h1>
    <p class="m-0 mb-5 max-w-[75ch] text-ink-2">Sellers sign in on the seller site (<b>/seller/</b>) with their own email and password: new orders, the queue, refund requests and stock. A seller can never use the owner's email or password. Your owner account works only here on the admin site, which has everything, including the counter screens.</p>

    <div class="card overflow-x-auto">
      <table class="w-full min-w-[640px] border-collapse text-sm">
        <thead><tr class="border-b border-line text-left text-xs uppercase tracking-wider text-ink-3">
          <th class="px-4 py-3">Name</th><th class="px-2 py-3">Email</th><th class="px-2 py-3">Role</th><th class="px-2 py-3">Status</th><th class="px-4 py-3"><span class="sr-only">Actions</span></th>
        </tr></thead>
        <tbody>
          <template v-for="u in users" :key="u.id">
            <tr class="border-b border-line">
              <td class="px-4 py-3 font-semibold">{{ u.name }}<span v-if="u.id === session.state.user?.id" class="font-normal text-ink-3"> (you)</span></td>
              <td class="px-2 py-3 text-ink-2">{{ u.email }}</td>
              <td class="px-2 py-3"><span class="pill" :class="u.role === 'owner' ? 'bg-turmeric-soft text-turmeric-deep' : 'bg-leaf-soft text-leaf'">{{ u.role === 'owner' ? 'Owner' : 'Seller' }}</span></td>
              <td class="px-2 py-3"><span class="pill" :class="u.is_active ? 'bg-leaf-soft text-leaf' : 'bg-sunk text-ink-3'">{{ u.is_active ? 'Can sign in' : 'Turned off' }}</span></td>
              <td class="px-4 py-3 text-right">
                <div class="flex justify-end gap-2 pb-1">
                  <button class="btn btn-light btn-sm" type="button" @click="resetFor = resetFor === u.id ? null : u.id">New password</button>
                  <button v-if="u.id !== session.state.user?.id" class="btn btn-light btn-sm" type="button" @click="setActive(u, !u.is_active)">{{ u.is_active ? 'Turn off' : 'Turn on' }}</button>
                </div>
              </td>
            </tr>
            <tr v-if="resetFor === u.id" class="border-b border-line bg-sunk">
              <td colspan="5" class="px-4 py-3">
                <form class="flex flex-wrap items-end gap-3" @submit.prevent="resetPassword(u)">
                  <div><label class="label" :for="`pw-${u.id}`">New password for {{ u.name }} (8+ characters)</label>
                    <PasswordInput :id="`pw-${u.id}`" v-model="newPassword" class="w-64" minlength="8" autocomplete="new-password" required /></div>
                  <button class="btn btn-dark btn-sm mb-1" type="submit">Set password</button>
                </form>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <form class="card mt-6 grid gap-4 p-5 md:grid-cols-2" @submit.prevent="add">
      <h2 class="m-0 font-display text-xl font-bold md:col-span-2">Add someone</h2>
      <div><label class="label" for="t-name">Name</label><input id="t-name" v-model="form.name" class="field" minlength="2" maxlength="80" required /></div>
      <div><label class="label" for="t-email">Email (they sign in with this)</label><input id="t-email" v-model="form.email" class="field" type="email" required /></div>
      <div><label class="label" for="t-pw">First password (8+ characters)</label><PasswordInput id="t-pw" v-model="form.password" minlength="8" autocomplete="new-password" required /></div>
      <div>
        <span class="label">Role</span>
        <div class="flex gap-2">
          <button class="key key-sm" type="button" :aria-pressed="form.role === 'seller'" @click="form.role = 'seller'">Seller</button>
          <button class="key key-sm" type="button" :aria-pressed="form.role === 'owner'" @click="form.role = 'owner'">Owner</button>
        </div>
      </div>
      <button class="btn btn-dark justify-self-start" type="submit" :disabled="busy">Add to team</button>
    </form>
  </div>
</template>
