import { NavLink } from 'react-router-dom'
import { ArrowLeftRight, Home, TrendingUp } from 'lucide-react'
import AppShell from '../layout/AppShell'

const LINKS = [
  { to: '/projects/cgf', end: true, label: 'Dashboard', icon: Home },
  { to: '/projects/cgf/investment', end: false, label: 'Investment Info', icon: TrendingUp },
  { to: '/projects/cgf/transactions', end: false, label: 'Transactions', icon: ArrowLeftRight },
]

export default function CgfShell({ title, children }) {
  return (
    <AppShell title={title || 'Commercial Goat Farming'}>
      <div className="cgf-page">
        <nav className="cgf-subnav" aria-label="Goat farming sections">
          {LINKS.map(({ to, end, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `cgf-subnav-link${isActive ? ' active' : ''}`}
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>
        {children}
      </div>
    </AppShell>
  )
}
