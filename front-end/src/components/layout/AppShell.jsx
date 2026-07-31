import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  ChevronDown,
  Compass,
  HelpCircle,
  Home,
  LayoutGrid,
  LogOut,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Shield,
  Sun,
  User,
  X,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useMember } from '../../context/MemberContext'
import { useTheme } from '../../context/ThemeContext'
import mcsLogo from '../../../mcs-logo2.png'

const NAV = [
  { id: 'home', label: 'Home', icon: Home, to: '/' },
  { id: 'projects', label: 'My Projects', icon: LayoutGrid, hash: 'projects' },
  { id: 'protection', label: 'Protection Benefits', icon: Shield, to: '/protection' },
  { id: 'discover', label: 'Other Projects', icon: Compass, hash: 'discover' },
]

export default function AppShell({ children, title = 'Home' }) {
  const [sidebarOpen, setSidebarOpen] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 960 : true,
  )
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 960 : false,
  )
  const [profileOpen, setProfileOpen] = useState(false)
  const profileRef = useRef(null)
  const { member, toast } = useMember()
  const { logout } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()

  const activeId = location.pathname.startsWith('/help')
    ? 'help'
    : location.pathname.startsWith('/protection')
      ? 'protection'
      : location.pathname.startsWith('/projects/')
        ? 'projects'
        : location.pathname.startsWith('/profile')
          ? 'profile'
          : location.hash.replace('#', '') || 'home'

  useEffect(() => {
    const onResize = () => {
      const mobile = window.innerWidth < 960
      setIsMobile(mobile)
      setSidebarOpen(!mobile)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const onClick = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false)
      }
    }
    const onKey = (e) => {
      if (e.key === 'Escape') setProfileOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  useEffect(() => {
    if (location.pathname !== '/') return
    const id = location.hash.replace('#', '')
    if (!id) return
    const el = document.getElementById(id)
    if (el) {
      window.setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    }
  }, [location.pathname, location.hash])

  const toggleSidebar = () => setSidebarOpen((v) => !v)

  const go = (item) => {
    if (isMobile) setSidebarOpen(false)

    if (item.to) {
      navigate(item.to)
      return
    }

    if (item.hash) {
      if (location.pathname !== '/') {
        navigate({ pathname: '/', hash: item.hash })
      } else {
        navigate({ pathname: '/', hash: item.hash })
        document.getElementById(item.hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }

  const sidebarVisible = sidebarOpen
  const pageTitle = location.pathname.startsWith('/protection')
    ? 'Protection Benefits'
    : location.pathname.startsWith('/projects/52wsc')
      ? '52 Weeks Saving Challenge'
    : location.pathname.startsWith('/projects/gwc')
      ? 'Generational Wealth Creation'
    : location.pathname.startsWith('/projects/cgf/investment')
      ? 'Investment Packages'
    : location.pathname.startsWith('/projects/cgf/transactions')
      ? 'Transactions'
    : location.pathname.startsWith('/projects/cgf')
      ? 'Commercial Goat Farming'
    : location.pathname.startsWith('/projects/rep')
      ? 'Real Estate Projects'
    : location.pathname.startsWith('/profile')
      ? 'My Profile'
    : location.pathname.startsWith('/help')
      ? 'Help Center'
      : title

  const pageSubtitle = location.pathname.startsWith('/protection')
    ? 'Bereavement cover and retirement protection'
    : location.pathname.startsWith('/projects/52wsc')
      ? 'Track personal 52WSC savings, targets, fixed savings, and history'
    : location.pathname.startsWith('/projects/gwc')
      ? '25% annualized interest · fixed deposits and maturity payouts'
    : location.pathname.startsWith('/projects/cgf/investment')
      ? 'Packages, breeding timeline, and your current investments'
    : location.pathname.startsWith('/projects/cgf/transactions')
      ? 'Payments, receipts, and estimated returns'
    : location.pathname.startsWith('/projects/cgf')
      ? 'Goat holdings, packages, and farm cycle progress'
    : location.pathname.startsWith('/projects/rep')
      ? 'Cooperative property projects, contributions, and performance'
    : location.pathname.startsWith('/profile')
      ? 'Your member details, bank info, and action requests'
    : location.pathname.startsWith('/help')
      ? 'Video tutorials for MCS projects and account setup'
      : 'Your personal cooperative portfolio'

  return (
    <div className={`shell ${sidebarVisible ? 'sidebar-open' : 'sidebar-collapsed'}`}>
      <header className="navbar">
        <div className="navbar-left">
          <button
            type="button"
            className="nav-icon-btn"
            aria-label={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
            onClick={toggleSidebar}
          >
            {isMobile ? (
              sidebarVisible ? <X size={18} /> : <Menu size={18} />
            ) : sidebarVisible ? (
              <PanelLeftClose size={18} />
            ) : (
              <PanelLeftOpen size={18} />
            )}
          </button>

          <div className="navbar-brand">
            <img src={mcsLogo} alt="MCS logo" />
            <div className="navbar-brand-text">
              <strong>MCS Portal</strong>
              <span>Member dashboard</span>
            </div>
          </div>
        </div>

        <div className="navbar-right">
          <button
            type="button"
            className="nav-icon-btn"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Light mode' : 'Dark mode'}
            onClick={toggleTheme}
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <button
            type="button"
            className={`nav-icon-btn ${activeId === 'help' ? 'active' : ''}`}
            aria-label="Help Center"
            title="Help Center"
            aria-current={activeId === 'help' ? 'page' : undefined}
            onClick={() => navigate('/help')}
          >
            <HelpCircle size={18} />
          </button>

          <button
            type="button"
            className="nav-icon-btn has-dot"
            aria-label="Notifications"
            title="Notifications"
          >
            <Bell size={18} />
            <span className="notif-dot" />
          </button>

          <div className="profile-menu" ref={profileRef}>
            <button
              type="button"
              className={`profile-trigger ${profileOpen ? 'open' : ''}`}
              aria-haspopup="menu"
              aria-expanded={profileOpen}
              onClick={() => setProfileOpen((v) => !v)}
            >
              <span className="avatar sm">{member.initials}</span>
              <span className="profile-meta">
                <b>{member.firstName}</b>
                <small>Verified</small>
              </span>
              <ChevronDown size={16} className="caret" />
            </button>

            {profileOpen ? (
              <div className="profile-dropdown" role="menu">
                <div className="profile-dropdown-head">
                  <span className="avatar">{member.initials}</span>
                  <div>
                    <b>{member.fullName}</b>
                    <span>{member.accountNumber}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="dropdown-item"
                  role="menuitem"
                  onClick={() => {
                    setProfileOpen(false)
                    navigate('/profile')
                  }}
                >
                  <User size={16} />
                  My profile
                </button>
                <button type="button" className="dropdown-item" role="menuitem">
                  <Settings size={16} />
                  Account settings
                </button>
                <div className="dropdown-divider" />
                <button
                  type="button"
                  className="dropdown-item danger"
                  role="menuitem"
                  onClick={async () => {
                    setProfileOpen(false)
                    await logout()
                    navigate('/login')
                  }}
                >
                  <LogOut size={16} />
                  Log out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div
        className={`backdrop ${isMobile && sidebarVisible ? 'show' : ''}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden={!isMobile || !sidebarVisible}
      />

      <aside
        className={`sidebar ${sidebarVisible ? 'open' : ''}`}
        aria-label="Member navigation"
        aria-hidden={!sidebarVisible}
      >
        <nav className="sidebar-nav">
          {NAV.map((item) => {
            const Icon = item.icon
            const isActive =
              item.to === '/protection'
                ? activeId === 'protection'
                : item.to === '/'
                  ? activeId === 'home' && !location.hash
                  : activeId === item.hash
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => go(item)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="sidebar-foot">
          <div className="sidebar-user">
            <div className="avatar">{member.initials}</div>
            <div>
              <b>{member.fullName}</b>
              <span>{member.accountNumber}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <div className="page-banner">
          <h1>{pageTitle}</h1>
          <p>{pageSubtitle}</p>
        </div>
        <main className="content">{children}</main>
      </div>

      {toast ? <div className="toast">{toast}</div> : null}
    </div>
  )
}
