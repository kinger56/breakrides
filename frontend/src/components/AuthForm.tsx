import { useState, type FormEvent } from 'react'
import { api, type User } from '../api'

type Mode = 'signup' | 'login'

export function AuthForm({ onAuthed }: { onAuthed: (user: User) => void }) {
  const [mode, setMode] = useState<Mode>('signup')
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const user =
        mode === 'signup'
          ? await api.signup(email, firstName, password)
          : await api.login(email, password)
      onAuthed(user)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <div className="tabs" role="tablist">
        {(['signup', 'login'] as const).map((m) => (
          <button
            key={m}
            role="tab"
            aria-selected={mode === m}
            className={mode === m ? 'tab active' : 'tab'}
            onClick={() => { setMode(m); setError('') }}
          >
            {m === 'signup' ? 'Sign up' : 'Log in'}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="stack">
        <label>
          School email
          <input type="email" required autoComplete="email" placeholder="you@scu.edu"
            value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        {mode === 'signup' && (
          <label>
            First name
            <input required maxLength={50} autoComplete="given-name"
              value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <small>Other riders only see your first name.</small>
          </label>
        )}
        <label>
          Password
          <input type="password" required minLength={mode === 'signup' ? 10 : undefined}
            autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            value={password} onChange={(e) => setPassword(e.target.value)} />
          {mode === 'signup' && <small>At least 10 characters.</small>}
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? 'One moment…' : mode === 'signup' ? 'Create account' : 'Log in'}
        </button>
      </form>
    </section>
  )
}
