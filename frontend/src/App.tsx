import { useEffect, useState } from 'react'
import { api, type Trip, type User } from './api'
import { AddTripForm } from './components/AddTripForm'
import { AuthForm } from './components/AuthForm'
import { TripCard } from './components/TripCard'
import { VerifyEmail } from './components/VerifyEmail'

export default function App() {
  // undefined = still checking whether we're logged in; null = logged out
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [trips, setTrips] = useState<Trip[]>([])
  // Bumped whenever trips change, so every card re-checks its group
  // (adding a flight can change who you're grouped with).
  const [version, setVersion] = useState(0)

  useEffect(() => {
    api.me().then(setUser, () => setUser(null))
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
    </main>
  )
}
