import { useState } from 'react'
import { api, type Stats, type User } from '../api'

export function Footer({ user, stats, onDeleted }: {
  user: User | null | undefined
  stats: Stats | null
  onDeleted: () => void
}) {
  const [error, setError] = useState('')

  async function deleteAccount() {
    const password = prompt(
      'This permanently deletes your account and flights, and removes you from any ride group.\n\n' +
      'Enter your password to confirm:',
    )
    if (!password) return
    try {
      await api.deleteAccount(password)
      onDeleted()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <footer className="footer">
      <details>
        <summary>Privacy and safety</summary>
        <ul>
          <li>We store your school email, first name, a hashed password (never the password itself) and the flights you add.</li>
          <li>Other riders see only your first name until everyone in your group confirms. Then the group sees each other's school email.</li>
          <li>Nothing is sold or shared. Delete your account any time and it's all gone.</li>
          <li>BreakRides only helps you find riders. Meet somewhere public, share your plans with a friend, and check the driver and plate in your rideshare app.</li>
        </ul>
      </details>
      <p className="muted">
        {stats?.feedback_email && (
          <>Questions or feedback? <a href={`mailto:${stats.feedback_email}`}>{stats.feedback_email}</a> · </>
        )}
        <a href="https://github.com/kinger56/breakrides">Source on GitHub</a>
        {user && (
          <> · <button className="link danger" onClick={deleteAccount}>Delete my account</button></>
        )}
      </p>
      {error && <p className="error" role="alert">{error}</p>}
    </footer>
  )
}
