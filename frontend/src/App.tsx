import { useEffect, useState } from 'react'
import { api, type Stats, type Trip, type User } from './api'
import { AddTripForm } from './components/AddTripForm'
import { AuthForm } from './components/AuthForm'
import { Footer } from './components/Footer'
import { TripCard } from './components/TripCard'
import { VerifyEmail } from './components/VerifyEmail'

export default function App() {
  // undefined = still checking whether we're logged in; null = logged out
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [trips, setTrips] = useState<Trip[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  // Bumped whenever trips change, so every card re-checks its group
  // (adding a flight can change who you're grouped with).
  const [version, setVersion] = useState(0)

  useEffect(() => {
    api.me().then(setUser, () => setUser(null))
    api.stats().then(setStats, () => {}) // nice to have: the page works without it
  }, [])

  useEffect(() => {
    if (user?.email_verified) api.trips().then(setTrips)
  }, [user, version])

  async function logout() {
    await api.logout()
    setTrips([])
    setUser(null)
  }

  return (
    <main>
      <header className="top">
        <h1>Break<span>Rides</span></h1>
        {user && (
          <p className="muted">
            Hi, {user.first_name} · <button className="link" onClick={logout}>Log out</button>
          </p>
        )}
      </header>
      <p className="tagline">Split a ride to the airport with students on nearby flights.</p>
      {stats && stats.riders_matched > 0 && (
        <p className="stats">
          {stats.riders_matched} students have shared {stats.rides_confirmed}{' '}
          {stats.rides_confirmed === 1 ? 'ride' : 'rides'}, saving about ${stats.estimated_savings}.
        </p>
      )}

      {user === undefined && <p className="muted">Loading…</p>}
      {user === null && <AuthForm onAuthed={setUser} />}
      {user && !user.email_verified && <VerifyEmail user={user} onVerified={setUser} />}
      {user?.email_verified && (
        <>
          <AddTripForm onAdded={() => setVersion((v) => v + 1)} />
          <h2 className="section">Your flights</h2>
          {trips.length === 0 && <p className="muted">No flights yet. Add one above.</p>}
          {trips.map((t) => (
            <TripCard key={`${t.id}-${version}`} trip={t} onDeleted={() => setVersion((v) => v + 1)} />
          ))}
        </>
      )}
      <Footer user={user} stats={stats} onDeleted={() => { setTrips([]); setUser(null) }} />
    </main>
  )
}
