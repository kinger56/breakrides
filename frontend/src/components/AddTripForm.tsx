import { useState, type FormEvent } from 'react'
import { api, type Airport, type Direction, type Trip } from '../api'
import { pacificInputToISO } from '../time'

export function AddTripForm({ onAdded }: { onAdded: (trip: Trip) => void }) {
  const [direction, setDirection] = useState<Direction>('to_airport')
  const [airport, setAirport] = useState<Airport>('SJC')
  const [when, setWhen] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      onAdded(await api.addTrip(airport, direction, pacificInputToISO(when)))
      setWhen('')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>Add a flight</h2>
      <form onSubmit={submit} className="stack">
        <div className="segmented" role="radiogroup" aria-label="Direction">
          {([['to_airport', 'Leaving campus'], ['from_airport', 'Coming back']] as const).map(
            ([value, label]) => (
              <button type="button" key={value} role="radio" aria-checked={direction === value}
                className={direction === value ? 'active' : ''} onClick={() => setDirection(value)}>
                {label}
              </button>
            ),
          )}
        </div>
        <div className="row">
          <label>
            Airport
            <select value={airport} onChange={(e) => setAirport(e.target.value as Airport)}>
              <option value="SJC">San José (SJC)</option>
              <option value="SFO">San Francisco (SFO)</option>
              <option value="OAK">Oakland (OAK)</option>
            </select>
          </label>
          <label>
            {direction === 'to_airport' ? 'Flight departs' : 'Flight lands'}
            <input type="datetime-local" required value={when} onChange={(e) => setWhen(e.target.value)} />
          </label>
        </div>
        <small>Times are Pacific time, as on your boarding pass.</small>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Adding…' : 'Find my ride group'}</button>
      </form>
    </section>
  )
}
