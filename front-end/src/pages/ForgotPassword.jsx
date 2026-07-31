import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Moon, Sun } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import mcsLogo from '../../mcs-logo2.png'

export default function ForgotPassword() {
  const { requestPasswordReset } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  const onSubmit = async (e) => {
    e.preventDefault()
    const value = email.trim().toLowerCase()
    if (!value) {
      setError('This field is required.')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      setError('Enter a valid email address.')
      return
    }

    setError('')
    setSubmitError('')
    setSubmitting(true)
    try {
      const data = await requestPasswordReset(value)
      setSuccessMessage(
        data?.message ||
          'If the email address is registered, a password reset link has been sent.',
      )
      setSent(true)
    } catch (err) {
      const apiEmail = err?.data?.email
      if (Array.isArray(apiEmail) && apiEmail[0]) {
        setError(String(apiEmail[0]))
      } else if (typeof apiEmail === 'string') {
        setError(apiEmail)
      } else {
        setSubmitError(err?.message || 'Could not send the reset email. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <button
        type="button"
        className="auth-theme-btn"
        aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        onClick={toggleTheme}
      >
        {isDark ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div className="auth-card auth-card-compact">
        <header className="auth-card-head">
          <img src={mcsLogo} alt="MCS logo" className="auth-logo" />
          <div>
            <h1>Forgot Password</h1>
            <p>Request a link to reset your password</p>
          </div>
        </header>

        <div className="auth-card-body">
          {sent ? (
            <div className="auth-state-card">
              <div className="auth-state-icon">
                <Mail size={22} />
              </div>
              <h2>Check your email</h2>
              <p>
                {successMessage} If you do not receive an email, make sure you entered the
                address you registered with and check your spam folder.
              </p>
              <div className="auth-state-actions">
                <Link to="/login" className="btn btn-primary">
                  Back to login
                </Link>
                <Link to="/help" className="btn btn-outline">
                  Help Center
                </Link>
              </div>
            </div>
          ) : (
            <>
              <p className="auth-intro">
                Enter the email address you signed up with. If it exists in our database,
                we will send you a link to reset your password.
              </p>

              {submitError ? (
                <div className="auth-alert error" role="alert">
                  {submitError}
                </div>
              ) : null}

              <form className="auth-form" onSubmit={onSubmit} noValidate>
                <label className={`auth-field ${error ? 'invalid' : ''}`}>
                  <span>
                    Email address <em>*</em>
                  </span>
                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    placeholder="Enter the email you signed up with"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value)
                      if (error) setError('')
                    }}
                    required
                    autoFocus
                    disabled={submitting}
                  />
                  <small className="auth-hint">
                    Enter the email address you used when registering.
                  </small>
                  {error ? <small className="auth-error">{error}</small> : null}
                </label>

                <button
                  type="submit"
                  className="btn btn-primary auth-submit"
                  disabled={submitting}
                >
                  {submitting ? 'Sending…' : 'Send reset email'}
                </button>
              </form>

              <div className="auth-footer">
                <p>
                  Remembered your password? <Link to="/login">Back to login</Link>
                </p>
                <p>
                  <Link to="/help">Need help getting started? Visit the Help Center</Link>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
