import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Clock3, HelpCircle, Info, ListChecks, LogIn, LogOut, Send } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function VerificationPending() {
  const navigate = useNavigate()
  const { authFetch, isAuthenticated, user, logout, updateUser } = useAuth()
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [account, setAccount] = useState(null)
  const [requestable, setRequestable] = useState([])
  const [requests, setRequests] = useState([])
  const [selectedProjects, setSelectedProjects] = useState([])
  const [notes, setNotes] = useState('')
  const [message, setMessage] = useState(null)
  const [supportPhone, setSupportPhone] = useState('+256755142271')

  const applyPayload = useCallback(
    (data) => {
      if (data?.isVerified) {
        updateUser({ is_verified: true })
        navigate('/', { replace: true })
        return true
      }
      setAccount(data?.user || null)
      setRequestable(data?.requestableProjects || [])
      setRequests(data?.projectAccessRequests || [])
      if (data?.supportPhone) setSupportPhone(data.supportPhone)
      return false
    },
    [navigate, updateUser],
  )

  const load = useCallback(
    async ({ silent = false } = {}) => {
      if (!isAuthenticated) return
      if (!silent) {
        setLoading(true)
        setError('')
      }
      try {
        const data = await authFetch('/api/verification/')
        applyPayload(data)
      } catch (err) {
        if (!silent) setError(err.message || 'Could not load verification status.')
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [applyPayload, authFetch, isAuthenticated],
  )

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!isAuthenticated) return undefined
    const poll = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      load({ silent: true })
    }
    const timer = window.setInterval(poll, 20000)
    return () => window.clearInterval(timer)
  }, [isAuthenticated, load])

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.is_verified === true) {
    return <Navigate to="/" replace />
  }

  const toggleProject = (id) => {
    setSelectedProjects((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  const submitRequests = async (e) => {
    e.preventDefault()
    if (selectedProjects.length === 0) {
      setMessage({ type: 'warning', text: 'Select at least one MCS group you belong to.' })
      return
    }
    setSubmitting(true)
    setMessage(null)
    try {
      const data = await authFetch('/api/verification/', {
        method: 'POST',
        body: {
          projectIds: selectedProjects,
          memberNotes: notes.trim(),
        },
      })
      if (applyPayload(data)) return
      setSelectedProjects([])
      setNotes('')
      const first = (data.messages || [])[0]
      setMessage({
        type: first?.level === 'success' ? 'success' : first?.level || 'success',
        text:
          first?.text ||
          (data.ok
            ? 'Your group access request has been submitted.'
            : 'No new project requests were submitted.'),
      })
    } catch (err) {
      setMessage({ type: 'warning', text: err.message || 'Could not submit requests.' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleSignOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const displayName =
    account?.fullName ||
    [account?.firstName, account?.lastName].filter(Boolean).join(' ') ||
    user?.first_name ||
    user?.username ||
    'Member'

  return (
    <div className="verification-page">
      <main className="verification-container">
        <div className="verification-icon">
          <Clock3 size={36} />
        </div>

        <h1 className="verification-title">Account Verification Pending</h1>
        <p className="verification-subtitle">
          Your account is currently under review by our administrators.
        </p>

        <section className="verification-message">
          <h2>
            <Info size={18} />
            What happens next?
          </h2>
          <p>
            An administrator will review your account and the MCS groups you belong to.
            Access to each project is approved separately — not every request is granted
            automatically.
          </p>
        </section>

        {error ? <div className="verification-flash warning">{error}</div> : null}
        {message ? <div className={`verification-flash ${message.type}`}>{message.text}</div> : null}

        <section className="verification-card">
          <h2>Account Information</h2>
          {loading && !account ? (
            <p className="verification-loading">Loading your account…</p>
          ) : (
            <>
              <div className="verification-detail">
                <span>Username:</span>
                <strong>{account?.username || user?.username}</strong>
              </div>
              <div className="verification-detail">
                <span>Name:</span>
                <strong>{displayName}</strong>
              </div>
              <div className="verification-detail">
                <span>Email:</span>
                <strong>{account?.email || user?.email || '—'}</strong>
              </div>
              <div className="verification-detail">
                <span>Account Number:</span>
                <strong>{account?.accountNumber || 'Not assigned yet'}</strong>
              </div>
            </>
          )}
        </section>

        <section className="verification-card">
          <h2>Which MCS groups do you belong to?</h2>
          <p>
            Select every Target Group Funding project you are part of. You can submit more
            groups later — duplicate pending requests are not created.
          </p>

          {loading && requestable.length === 0 ? (
            <p className="verification-loading">Loading available groups…</p>
          ) : requestable.length === 0 ? (
            <p className="verification-loading">
              No additional groups are available to request right now. If you already
              submitted requests, check the list below.
            </p>
          ) : (
            <form onSubmit={submitRequests}>
              <div className="verification-project-list">
                {requestable.map((project) => (
                  <label key={project.id} className="verification-project-check">
                    <input
                      type="checkbox"
                      checked={selectedProjects.includes(project.id)}
                      onChange={() => toggleProject(project.id)}
                      disabled={submitting}
                    />
                    <span>{project.name}</span>
                  </label>
                ))}
              </div>

              <label className="verification-notes">
                <span>Optional note for the administrator</span>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. club name, member ID, or which savings group you joined"
                  rows={3}
                  disabled={submitting}
                />
              </label>

              <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
                <Send size={16} />
                {submitting ? 'Submitting…' : 'Submit group requests'}
              </button>
            </form>
          )}
        </section>

        <section className="verification-card">
          <h2>
            <ListChecks size={18} />
            Your group access requests
          </h2>
          <div className="verification-request-list">
            {requests.length === 0 ? (
              <p className="verification-loading">No group access requests yet.</p>
            ) : (
              requests.map((req) => (
                <article key={req.id} className="verification-request-item">
                  <div className="verification-request-head">
                    <strong>{req.project}</strong>
                    <span className={`status-pill ${req.status}`}>{req.statusDisplay}</span>
                  </div>
                  <span>Submitted {req.createdAt || '—'}</span>
                  {req.status === 'rejected' && req.adminNotes ? (
                    <p>
                      <strong>Admin reason:</strong> {req.adminNotes}
                    </p>
                  ) : null}
                </article>
              ))
            )}
          </div>
        </section>

        <div className="verification-actions">
          <button type="button" className="btn btn-primary" onClick={handleSignOut}>
            <LogOut size={16} />
            Sign Out
          </button>
          <button type="button" className="btn btn-outline" onClick={handleSignOut}>
            <LogIn size={16} />
            Try Signing In Again
          </button>
          <Link to="/help" className="btn btn-outline">
            <HelpCircle size={16} />
            Help Center
          </Link>
        </div>

        <p className="verification-support">
          Need help? Contact support at <strong>{supportPhone}</strong>
        </p>
      </main>
    </div>
  )
}
