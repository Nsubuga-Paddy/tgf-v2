import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Circle, Eye, EyeOff, Moon, Sun } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import mcsLogo from '../../mcs-logo2.png'

const INITIAL = {
  password1: '',
  password2: '',
}

const COMMON_PASSWORDS = new Set([
  'password',
  'password123',
  '12345678',
  '123456789',
  'qwerty123',
  'admin123',
  'letmein123',
])

function getPasswordCriteria(password, confirmation) {
  const value = password.trim().toLowerCase()
  return [
    {
      id: 'length',
      label: 'At least 8 characters',
      met: password.length >= 8,
    },
    {
      id: 'common',
      label: 'Not a commonly used password',
      met: password.length > 0 && !COMMON_PASSWORDS.has(value),
    },
    {
      id: 'numeric',
      label: 'Not entirely numeric',
      met: password.length > 0 && !/^\d+$/.test(password),
    },
    {
      id: 'similar',
      label: 'Not too similar to your username or email',
      met: password.length >= 8,
    },
    {
      id: 'match',
      label: 'Both password entries match',
      met: confirmation.length > 0 && password === confirmation,
    },
  ]
}

function validate(form) {
  const errors = {}
  if (!form.password1) {
    errors.password1 = 'This field is required.'
  } else if (form.password1.length < 8) {
    errors.password1 = 'Password must be at least 8 characters.'
  } else if (/^\d+$/.test(form.password1)) {
    errors.password1 = 'Password cannot be entirely numeric.'
  } else if (COMMON_PASSWORDS.has(form.password1.trim().toLowerCase())) {
    errors.password1 = 'Password is too common.'
  }
  if (!form.password2) {
    errors.password2 = 'This field is required.'
  } else if (form.password1 !== form.password2) {
    errors.password2 = "The two password fields didn't match."
  }
  return errors
}

export default function ResetPassword() {
  const navigate = useNavigate()
  const { uid, token } = useParams()
  const { confirmPasswordReset } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [form, setForm] = useState(INITIAL)
  const [errors, setErrors] = useState({})
  const [showPassword1, setShowPassword1] = useState(false)
  const [showPassword2, setShowPassword2] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const criteria = getPasswordCriteria(form.password1, form.password2)

  const linkValid = useMemo(() => Boolean(uid && token), [uid, token])

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
    if (!linkValid) return

    const nextErrors = validate(form)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setSubmitError('')
    try {
      await confirmPasswordReset({
        uid,
        token,
        new_password1: form.password1,
        new_password2: form.password2,
      })
      navigate('/reset/complete', { replace: true })
    } catch (err) {
      const data = err?.data
      const mapped = {}
      if (data && typeof data === 'object') {
        if (data.new_password1) {
          mapped.password1 = Array.isArray(data.new_password1)
            ? String(data.new_password1[0])
            : String(data.new_password1)
        }
        if (data.new_password2) {
          mapped.password2 = Array.isArray(data.new_password2)
            ? String(data.new_password2[0])
            : String(data.new_password2)
        }
      }
      if (Object.keys(mapped).length > 0) setErrors(mapped)
      setSubmitError(
        err?.message || 'The password reset link is invalid or has expired.',
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
            <h1>Set new password</h1>
            <p>Choose a new password for your account</p>
          </div>
        </header>

        <div className="auth-card-body">
          {!linkValid ? (
            <div className="auth-state-card">
              <h2>Reset link required</h2>
              <p>
                Open the password reset link from your email to choose a new password. If
                the link expired, request a new one.
              </p>
              <div className="auth-state-actions">
                <Link to="/forgot-password" className="btn btn-primary">
                  Request new link
                </Link>
                <Link to="/login" className="btn btn-outline">
                  Back to login
                </Link>
              </div>
            </div>
          ) : (
            <>
              <p className="auth-intro">Enter your new password below.</p>

              {submitError ? (
                <div className="auth-alert error" role="alert">
                  {submitError}
                </div>
              ) : null}

              <form className="auth-form" onSubmit={onSubmit} noValidate>
                <label className={`auth-field ${errors.password1 ? 'invalid' : ''}`}>
                  <span>
                    New password <em>*</em>
                  </span>
                  <div className="auth-password">
                    <input
                      type={showPassword1 ? 'text' : 'password'}
                      name="new_password1"
                      autoComplete="new-password"
                      value={form.password1}
                      onChange={set('password1')}
                      required
                      disabled={submitting}
                    />
                    <button
                      type="button"
                      className="auth-eye"
                      aria-label={showPassword1 ? 'Hide password' : 'Show password'}
                      onClick={() => setShowPassword1((v) => !v)}
                    >
                      {showPassword1 ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password1 ? (
                    <small className="auth-error">{errors.password1}</small>
                  ) : null}
                </label>

                <div className="password-criteria" aria-label="Password creation criteria">
                  <strong>Password must:</strong>
                  <ul>
                    {criteria.map((item) => {
                      const Icon = item.met ? CheckCircle2 : Circle
                      return (
                        <li key={item.id} className={item.met ? 'met' : ''}>
                          <Icon size={14} />
                          <span>{item.label}</span>
                        </li>
                      )
                    })}
                  </ul>
                </div>

                <label className={`auth-field ${errors.password2 ? 'invalid' : ''}`}>
                  <span>
                    Confirm new password <em>*</em>
                  </span>
                  <div className="auth-password">
                    <input
                      type={showPassword2 ? 'text' : 'password'}
                      name="new_password2"
                      autoComplete="new-password"
                      value={form.password2}
                      onChange={set('password2')}
                      required
                      disabled={submitting}
                    />
                    <button
                      type="button"
                      className="auth-eye"
                      aria-label={showPassword2 ? 'Hide password' : 'Show password'}
                      onClick={() => setShowPassword2((v) => !v)}
                    >
                      {showPassword2 ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password2 ? (
                    <small className="auth-error">{errors.password2}</small>
                  ) : null}
                </label>

                <button
                  type="submit"
                  className="btn btn-primary auth-submit"
                  disabled={submitting}
                >
                  {submitting ? 'Changing password…' : 'Confirm password reset'}
                </button>
              </form>

              <div className="auth-footer">
                <p>
                  Link expired? <Link to="/forgot-password">Request new link</Link>
                </p>
                <p>
                  <Link to="/login">Back to login</Link>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
