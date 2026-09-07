import { AlertCircle, CheckCircle2, Circle } from 'lucide-react'

export function eligibilityTone(status) {
  if (status === 'eligible') return 'eligible'
  if (status === 'may_qualify') return 'may-qualify'
  if (status === 'not_eligible') return 'not-eligible'
  return 'coming-soon'
}

export function LoanStatusBadge({ status, className = '' }) {
  const labels = {
    active: 'Active',
    overdue: 'Overdue',
    closed: 'Fully paid',
    pending: 'Pending',
    submitted: 'Submitted',
    under_review: 'Under review',
    approved: 'Approved',
    rejected: 'Rejected',
    disbursed: 'Disbursed',
    paid: 'Paid',
    due: 'Due now',
    upcoming: 'Upcoming',
  }
  const tone =
    status === 'overdue' || status === 'rejected'
      ? 'overdue'
      : status === 'closed' || status === 'paid' || status === 'approved' || status === 'disbursed'
        ? 'closed'
        : status === 'due' || status === 'under_review' || status === 'submitted'
          ? 'active'
          : status
  return (
    <span className={`loans-status-badge ${tone} ${className}`.trim()}>
      {labels[status] || status}
    </span>
  )
}

export function FactorIcon({ met }) {
  if (met === true) return <CheckCircle2 size={16} className="loans-factor-icon met" />
  if (met === false) return <AlertCircle size={16} className="loans-factor-icon unmet" />
  return <Circle size={16} className="loans-factor-icon pending" />
}

export function formatLoanDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
