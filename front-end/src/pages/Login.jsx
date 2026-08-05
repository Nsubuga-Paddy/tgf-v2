import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Moon, Sun } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  SESSION_TIMEOUT_MESSAGE,
  SESSION_TIMEOUT_REASON,
} from '../lib/sessionPolicy'
import mcsLogo from '../../mcs-logo2.png'

const INITIAL = {
  username: '',
  password: '',
}

function validate(form) {
  const errors = {}
  if (!form.username.trim()) errors.username = 'This field is required.'
  if (!form.password) errors.password = 'This field is required.'
  return errors
}

export default function Login() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { login, isAuthenticated, user } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [form, setForm] = useState(INITIAL)
  const [errors, setErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(null)
  const [submitError, setSubmitError] = useState('')
  const [timeoutNotice, setTimeoutNotice] = useState('')

  useEffect(() => {
    if (searchParams.get('reason') !== SESSION_TIMEOUT_REASON) return
    setTimeoutNotice(SESSION_TIMEOUT_MESSAGE)
    const next = new URLSearchParams(searchParams)
    next.delete('reason')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (!isAuthenticated) return
    navigate(user?.is_verified === false ? '/verification-pending' : '/', { replace: true })
  }, [isAuthenticated, navigate, user])

  const set = (key) => (e) => {
    const value = e.target.value
    setForm((prev) => ({ ...prev, [key]: value }))
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
    }
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    const nextErrors = validate(form)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setSubmitError('')
    setSuccess(null)
    setTimeoutNotice('')
    try {
      const session = await login({
        username: form.username.trim(),
        password: form.password,
      })
      const destination =
        session.user?.is_verified === false ? '/verification-pending' : '/'
      setSuccess(`Welcome back, ${session.user?.first_name || form.username}!`)
      navigate(destination, { replace: true })
    } catch (error) {
      setSubmitError(
        error?.message ||
          'Invalid username or password. Please check your credentials and try again.',
      )
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
            <h1>Login</h1>
            <p>Access your MCS member account</p>
          </div>
        </header>

        <div className="auth-card-body">
          {timeoutNotice ? (
            <div className="auth-alert warning" role="status">
              {timeoutNotice}
            </div>
          ) : null}
          {success ? (
            <div className="auth-alert success" role="status">
              {success}
            </div>
          ) : null}
          {submitError ? (
            <div className="auth-alert error" role="alert">
              {submitError}
            </div>
          ) : null}

          <form className="auth-form" onSubmit={onSubmit} noValidate>
            <label className={`auth-field ${errors.username ? 'invalid' : ''}`}>
              <span>
                Username <em>*</em>
              </span>
              <input
                type="text"
                name="username"
                autoComplete="username"
                value={form.username}
                onChange={set('username')}
                required
              />
              {errors.username ? <small className="auth-error">{errors.username}</small> : null}
            </label>

            <label className={`auth-field ${errors.password ? 'invalid' : ''}`}>
              <span>
                Password <em>*</em>
              </span>
              <div className="auth-password">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  autoComplete="current-password"
                  value={form.password}
                  onChange={set('password')}
                  required
                />
                <button
                  type="button"
                  className="auth-eye"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password ? <small className="auth-error">{errors.password}</small> : null}
            </label>

            <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
              {submitting ? 'Logging in…' : 'Login'}
            </button>

            <Link className="auth-muted-link" to="/forgot-password">
              Forgot password?
            </Link>

            <Link className="auth-muted-link" to="/help">
              Need help getting started? Visit the Help Center
            </Link>
          </form>

          <div className="auth-footer">
            <p>
              Don&apos;t have an account? <Link to="/signup">Sign up</Link>
            </p>
            <p>
              <Link to="/help">Watch tutorials in the Help Center</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
