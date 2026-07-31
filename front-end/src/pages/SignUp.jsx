import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Moon, Sun } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import mcsLogo from '../../mcs-logo2.png'

const INITIAL = {
  firstName: '',
  lastName: '',
  username: '',
  email: '',
  whatsappNumber: '',
  password1: '',
  password2: '',
}

function validate(form) {
  const errors = {}

  if (!form.firstName.trim()) errors.firstName = 'This field is required.'
  if (!form.lastName.trim()) errors.lastName = 'This field is required.'
  if (!form.username.trim()) errors.username = 'This field is required.'

  if (!form.email.trim()) {
    errors.email = 'This field is required.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = 'Enter a valid email address.'
  }

  if (!form.whatsappNumber.trim()) {
    errors.whatsappNumber = 'This field is required.'
  } else if (!/^\+[1-9]\d{7,14}$/.test(form.whatsappNumber.trim().replace(/[\s-]/g, ''))) {
    errors.whatsappNumber =
      'Enter a WhatsApp number beginning with a country code (e.g., +2567xxxxxxxx).'
  }

  if (!form.password1) {
    errors.password1 = 'This field is required.'
  } else if (form.password1.length < 8) {
    errors.password1 = 'Password must be at least 8 characters.'
  }

  if (!form.password2) {
    errors.password2 = 'This field is required.'
  } else if (form.password1 !== form.password2) {
    errors.password2 = "The two password fields didn't match."
  }

  return errors
}

export default function SignUp() {
  const navigate = useNavigate()
  const { signup } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [form, setForm] = useState(INITIAL)
  const [errors, setErrors] = useState({})
  const [showPassword1, setShowPassword1] = useState(false)
  const [showPassword2, setShowPassword2] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(null)
  const [submitError, setSubmitError] = useState('')

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
    try {
      const response = await signup({
        username: form.username.trim(),
        first_name: form.firstName.trim(),
        last_name: form.lastName.trim(),
        email: form.email.trim(),
        whatsapp_number: form.whatsappNumber.trim().replace(/[\s-]/g, ''),
        password1: form.password1,
        password2: form.password2,
      })
      setSuccess(response.message || `Account created for ${form.username}.`)
      navigate('/verification-pending', { replace: true })
    } catch (error) {
      const fieldMap = {
        first_name: 'firstName',
        last_name: 'lastName',
        username: 'username',
        email: 'email',
        whatsapp_number: 'whatsappNumber',
        password1: 'password1',
        password2: 'password2',
      }
      const apiErrors = error?.data
      if (apiErrors && typeof apiErrors === 'object' && !Array.isArray(apiErrors)) {
        const mapped = {}
        for (const [key, value] of Object.entries(apiErrors)) {
          const formKey = fieldMap[key]
          if (!formKey) continue
          const text = Array.isArray(value) ? value[0] : value
          if (text) mapped[formKey] = String(text)
        }
        if (Object.keys(mapped).length > 0) setErrors(mapped)
      }
      setSubmitError(
        error?.message || 'Signup failed. Please check your details and try again.',
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

      <div className="auth-card">
        <header className="auth-card-head">
          <img src={mcsLogo} alt="MCS logo" className="auth-logo" />
          <div>
            <h1>Sign Up</h1>
            <p>Create your MCS member account</p>
          </div>
        </header>

        <div className="auth-card-body">
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
            <div className="auth-row">
              <label className={`auth-field ${errors.firstName ? 'invalid' : ''}`}>
                <span>
                  First Name <em>*</em>
                </span>
                <input
                  type="text"
                  name="first_name"
                  autoComplete="given-name"
                  value={form.firstName}
                  onChange={set('firstName')}
                  required
                />
                {errors.firstName ? <small className="auth-error">{errors.firstName}</small> : null}
              </label>

              <label className={`auth-field ${errors.lastName ? 'invalid' : ''}`}>
                <span>
                  Last Name <em>*</em>
                </span>
                <input
                  type="text"
                  name="last_name"
                  autoComplete="family-name"
                  value={form.lastName}
                  onChange={set('lastName')}
                  required
                />
                {errors.lastName ? <small className="auth-error">{errors.lastName}</small> : null}
              </label>
            </div>

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

            <label className={`auth-field ${errors.email ? 'invalid' : ''}`}>
              <span>
                Email <em>*</em>
              </span>
              <input
                type="email"
                name="email"
                autoComplete="email"
                value={form.email}
                onChange={set('email')}
                required
              />
              {errors.email ? <small className="auth-error">{errors.email}</small> : null}
            </label>

            <label className={`auth-field ${errors.whatsappNumber ? 'invalid' : ''}`}>
              <span>
                WhatsApp Number <em>*</em>
              </span>
              <input
                type="tel"
                name="whatsapp_number"
                autoComplete="tel"
                placeholder="+2567xxxxxxxx"
                value={form.whatsappNumber}
                onChange={set('whatsappNumber')}
                required
              />
              <small className="auth-hint">
                Must begin with a country code (e.g., +2567xxxxxxxx for Uganda)
              </small>
              {errors.whatsappNumber ? (
                <small className="auth-error">{errors.whatsappNumber}</small>
              ) : null}
            </label>

            <label className={`auth-field ${errors.password1 ? 'invalid' : ''}`}>
              <span>
                Password <em>*</em>
              </span>
              <div className="auth-password">
                <input
                  type={showPassword1 ? 'text' : 'password'}
                  name="password1"
                  autoComplete="new-password"
                  value={form.password1}
                  onChange={set('password1')}
                  required
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
              {errors.password1 ? <small className="auth-error">{errors.password1}</small> : null}
            </label>

            <label className={`auth-field ${errors.password2 ? 'invalid' : ''}`}>
              <span>
                Confirm Password <em>*</em>
              </span>
              <div className="auth-password">
                <input
                  type={showPassword2 ? 'text' : 'password'}
                  name="password2"
                  autoComplete="new-password"
                  value={form.password2}
                  onChange={set('password2')}
                  required
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
              {errors.password2 ? <small className="auth-error">{errors.password2}</small> : null}
            </label>

            <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
              {submitting ? 'Creating account…' : 'Sign Up'}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Already have an account? <Link to="/login">Login</Link>
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
