import { useEffect, useState, type FormEvent } from 'react'
import { api, type User } from '../api'

const RESEND_SECONDS = 60

export function VerifyEmail({ user, onVerified }: { user: User; onVerified: (user: User) => void }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  // Matches the server's limit, so the button isn't offered when it would fail.
  const [cooldown, setCooldown] = useState(RESEND_SECONDS)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setNotice('')
    setBusy(true)
    try {
      onVerified(await api.verify(code))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function resend() {
    setError('')
    try {
      await api.resendCode()
      setNotice('New code sent. Check your inbox (and spam folder).')
      setCooldown(RESEND_SECONDS)
      setCode('')
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section className="card">
      <h2>Check your email</h2>
      <p className="muted">
        We sent a 6-digit code to <strong>{user.email}</strong>. Entering it proves you're a
        Santa Clara student, which keeps BreakRides safe for everyone.
      </p>
      <form onSubmit={submit} className="stack" style={{ marginTop: 14 }}>
        <label>
          Code
          <input
            className="code-input"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            required
            placeholder="123456"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="notice" role="status">{notice}</p>}
        <button className="primary" disabled={busy || code.length !== 6}>
          {busy ? 'Checking…' : 'Verify'}
        </button>
        <button type="button" className="link" onClick={resend} disabled={cooldown > 0}>
          {cooldown > 0 ? `Send a new code in ${cooldown}s` : 'Send a new code'}
        </button>
      </form>
    </section>
  )
}
