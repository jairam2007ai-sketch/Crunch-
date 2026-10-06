import { reactive } from 'vue'
import { createSession } from '../shared/session'
import { createStaff } from '../shared/staff'

// Owner accounts only. Sellers have their own accounts on the seller site.
export const session = createSession('crunch.admin', ['owner'])
export const api = session.api
// The owner can work the counter too: same POS and queue as the seller site.
export const staff = createStaff(api)

// Counts shown as badges in the sidebar.
export const badges = reactive({ refunds: 0, lowStock: 0, isOpen: null })

export async function refreshBadges() {
  const [refunds, stock] = await Promise.all([api.get('/api/refunds?status=pending'), api.get('/api/inventory')])
  badges.refunds = refunds.length
  badges.lowStock = stock.filter((i) => i.low || (i.tracked && i.out)).length
}
