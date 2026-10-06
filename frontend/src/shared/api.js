// Talks to the FastAPI backend. In development Vite forwards /api to it;
// in production set VITE_API_URL if the API lives on another domain.
const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function messageFrom(data, status) {
  if (data && typeof data.detail === 'string') return data.detail
  if (data && Array.isArray(data.detail) && data.detail.length) {
    const msg = String(data.detail[0].msg || '').replace(/^Value error, /, '')
    return msg || 'Please check the form and try again.'
  }
  if (status === 0) return "Can't reach the server. Check your internet connection and try again."
  return `Something went wrong on our side (error ${status}). Please try again.`
}

export function createClient({ getToken, onUnauthorized } = {}) {
  async function request(method, path, body) {
    const headers = { Accept: 'application/json' }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    const token = getToken?.()
    if (token) headers.Authorization = `Bearer ${token}`
    let res
    try {
      res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
    } catch {
      throw new ApiError(0, messageFrom(null, 0))
    }
    let data = null
    try { data = await res.json() } catch { data = null }
    if (!res.ok) {
      if (res.status === 401 && token) onUnauthorized?.()
      throw new ApiError(res.status, messageFrom(data, res.status))
    }
    return data
  }
  return {
    get: (p) => request('GET', p),
    post: (p, b = {}) => request('POST', p, b),
    patch: (p, b = {}) => request('PATCH', p, b),
  }
}

export const publicApi = createClient()
