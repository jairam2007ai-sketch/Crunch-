import { reactive } from 'vue'
import { createClient } from './api'

function read(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function write(key, value) {
  try { value == null ? localStorage.removeItem(key) : localStorage.setItem(key, value) } catch { /* storage blocked */ }
}

// One sign-in per website: the seller site and the admin site keep separate sessions.
export function createSession(appKey, allowedRoles) {
  let user = null
  try { user = JSON.parse(read(`${appKey}.user`) || 'null') } catch { user = null }
  let token = read(`${appKey}.token`)
  if (user && !allowedRoles.includes(user.role)) { user = null; token = null } // e.g. an owner session from before
  const state = reactive({ token, user, expired: false })

  function clear() {
    state.token = null
    state.user = null
    write(`${appKey}.token`, null)
    write(`${appKey}.user`, null)
  }

  const api = createClient({
    getToken: () => state.token,
    onUnauthorized: () => { clear(); state.expired = true },
  })

  async function login(email, password) {
    const data = await api.post('/api/auth/login', { email, password })
    if (!allowedRoles.includes(data.user.role)) {
      throw new Error(data.user.role === 'owner'
        ? "That's the owner's account. The owner signs in on the admin site (/admin/), which has everything the seller site has. This site needs a seller account."
        : 'Only the owner can sign in here. Sellers sign in on the seller site (/seller/).')
    }
    state.token = data.access_token
    state.user = data.user
    state.expired = false
    write(`${appKey}.token`, data.access_token)
    write(`${appKey}.user`, JSON.stringify(data.user))
  }

  return { state, api, login, logout: clear }
}

export const storage = { read, write }
