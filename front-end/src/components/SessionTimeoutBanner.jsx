import { useAuth } from '../context/AuthContext'

export default function SessionTimeoutBanner() {
  const { idleWarning, dismissIdleWarning, logoutForTimeout } = useAuth()

  if (!idleWarning) return null

  return (
    <div className="session-timeout-banner" role="alertdialog" aria-modal="true" aria-labelledby="session-timeout-title">
      <div className="session-timeout-card">
        <h2 id="session-timeout-title">Session timeout</h2>
        <p>
          You have been inactive. For your security, you will be signed out soon unless you
          continue.
        </p>
        <div className="session-timeout-actions">
          <button type="button" className="btn btn-outline" onClick={() => logoutForTimeout()}>
            Sign out now
          </button>
          <button type="button" className="btn btn-primary" onClick={dismissIdleWarning}>
            Stay signed in
          </button>
        </div>
      </div>
    </div>
  )
}
