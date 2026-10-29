// Typed client for the BreakRides API. These types mirror the Pydantic
// models in app/schemas.py, so TypeScript catches mismatches at build time.

export type Airport = 'SJC' | 'SFO' | 'OAK'
export type Direction = 'to_airport' | 'from_airport'

export interface User {
  id: number
  email: string
  first_name: string
  email_verified: boolean
}

export interface Trip {
  id: number
  airport: Airport
  direction: Direction
  flight_time: string // ISO 8601, UTC
}

export interface Rider {
  first_name: string
  is_you: boolean
  confirmed: boolean
  email: string | null // only once the group is locked
}

export interface Group {
  airport: Airport
  direction: Direction
  pickup_time: string
  matched: boolean
  locked: boolean // everyone confirmed: contact info is shared
  you_confirmed: boolean
  riders: Rider[]
  fare_estimate: number
  cost_per_person: number
  savings_per_person: number
}

/** An error the user should see, with the server's message when it has one. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin', // send the login cookie
  })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new ApiError(response.status, errorMessage(data, response.status))
  return data as T
}

// FastAPI sends {"detail": "text"} for our own errors and
// {"detail": [{"msg": ...}, ...]} for validation errors.
function errorMessage(data: { detail?: unknown }, status: number): string {
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail) && data.detail[0]?.msg) {
    return String(data.detail[0].msg).replace(/^Value error, /, '')
  }
  return `Something went wrong (${status}). Please try again.`
}

export const api = {
  me: () => request<User>('GET', '/api/me'),
  signup: (email: string, first_name: string, password: string) =>
    request<User>('POST', '/api/auth/signup', { email, first_name, password }),
  login: (email: string, password: string) =>
    request<User>('POST', '/api/auth/login', { email, password }),
  logout: () => request<void>('POST', '/api/auth/logout'),
  verify: (code: string) => request<User>('POST', '/api/auth/verify', { code }),
  resendCode: () => request<void>('POST', '/api/auth/resend'),
  trips: () => request<Trip[]>('GET', '/api/trips'),
  addTrip: (airport: Airport, direction: Direction, flight_time: string) =>
    request<Trip>('POST', '/api/trips', { airport, direction, flight_time }),
  deleteTrip: (id: number) => request<void>('DELETE', `/api/trips/${id}`),
  group: (tripId: number) => request<Group>('GET', `/api/trips/${tripId}/group`),
  confirm: (tripId: number) => request<Group>('POST', `/api/trips/${tripId}/confirm`),
  leave: (tripId: number) => request<Group>('POST', `/api/trips/${tripId}/leave`),
}
