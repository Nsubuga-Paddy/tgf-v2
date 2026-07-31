import { Link } from 'react-router-dom'
import { CheckCircle2, Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import mcsLogo from '../../mcs-logo2.png'

export default function PasswordResetComplete() {
  const { isDark, toggleTheme } = useTheme()

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
            <h1>Password changed</h1>
            <p>Your password reset is complete</p>
          </div>
        </header>

        <div className="auth-card-body">
          <div className="auth-state-card">
            <div className="auth-state-icon success">
              <CheckCircle2 size={24} />
            </div>
            <h2>Password changed</h2>
            <p>Your password has been set. You can now log in with your new password.</p>
            <div className="auth-state-actions">
              <Link to="/login" className="btn btn-primary">
                Log in
              </Link>
              <Link to="/help" className="btn btn-outline">
                Visit Help Center
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
