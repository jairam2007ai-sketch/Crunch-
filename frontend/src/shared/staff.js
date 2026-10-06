// Live order data for the counter screens (POS and queue). The seller site and the
// admin site each create one with their own signed-in API and provide it as 'staff'.
import { reactive } from 'vue'
import { beep, toast } from './toast'

export function createStaff(api) {
  const live = reactive({ active: [], today: null, loaded: false })
  const seen = new Set()

  async function refreshActive() {
    const list = await api.get('/api/orders?active=true')
    const fresh = list.filter((o) => o.source === 'online' && o.status === 'placed' && !seen.has(o.id))
    if (live.loaded && fresh.length) {
      beep()
      toast(fresh.length === 1 ? `New online order ${fresh[0].number} from ${fresh[0].customer_name}` : `${fresh.length} new online orders`)
    }
    list.forEach((o) => seen.add(o.id))
    live.active = list
    live.loaded = true
  }

  async function refreshToday() {
    live.today = await api.get('/api/dashboard/today')
  }

  function reset() {
    live.loaded = false
    live.active = []
    seen.clear()
  }

  return { api, live, refreshActive, refreshToday, reset }
}
