import { createSession } from '../shared/session'
import { createStaff } from '../shared/staff'

// Seller accounts only. The owner uses the admin site, which has these screens too.
export const session = createSession('crunch.seller', ['seller'])
export const api = session.api
export const staff = createStaff(api)
export const { live, refreshActive, refreshToday } = staff
