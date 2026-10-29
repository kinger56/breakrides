import { useEffect, useState } from 'react'
import { api, type Group, type Trip } from '../api'
import { formatPacific } from '../time'

export function TripCard({ trip, onDeleted }: { trip: Trip; onDeleted: (id: number) => void }) {
  const [group, setGroup] = useState<Group | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let current = true // ignore a late answer if this card has gone away
    api.group(trip.id).then(
      (g) => current && setGroup(g),
      (err: Error) => current && setError(err.message),
    )
    return () => { current = false }
  }, [trip.id])

  async function remove() {
    if (!confirm('Remove this flight?')) return
    await api.deleteTrip(trip.id)
    onDeleted(trip.id)
  }

  const route = trip.direction === 'to_airport' ? `Campus → ${trip.airport}` : `${trip.airport} → Campus`
  const verb = trip.direction === 'to_airport' ? 'departs' : 'lands'

  return (
    <article className="card trip">
      <header className="trip-head">
        <div>
          <h3>{route}</h3>
          <p className="muted">Flight {verb} {formatPacific(trip.flight_time)}</p>
        </div>
        <button className="link" onClick={remove} aria-label={`Remove ${route} flight`}>Remove</button>
      </header>

      {error && <p className="error">{error}</p>}
      {!group && !error && <p className="muted">Finding your group…</p>}
      {group && (
        <div className={group.matched ? 'group matched' : 'group'}>
          <p className="pickup">
            Pickup <strong>{formatPacific(group.pickup_time)}</strong>
          </p>
          <ul className="riders" aria-label="Riders">
            {group.riders.map((r, i) => (
              <li key={i} className={r.is_you ? 'you' : ''}>{r.is_you ? 'You' : r.first_name}</li>
            ))}
          </ul>
          {group.matched ? (
            <p className="savings">
              <strong>${group.cost_per_person.toFixed(2)}</strong> each instead of ${group.fare_estimate}
              {' · '}you save <strong>${group.savings_per_person.toFixed(2)}</strong>
            </p>
          ) : (
            <p className="muted">
              No match yet. When another student adds a flight near yours, they'll show up here.
              Riding alone is about ${group.fare_estimate}.
            </p>
          )}
        </div>
      )}
    </article>
  )
}
