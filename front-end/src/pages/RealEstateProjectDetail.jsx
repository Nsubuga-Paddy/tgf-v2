import { useEffect, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CalendarCheck,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Coins,
  FileText,
  Gauge,
  Lock,
  Map,
  MapPin,
  PlayCircle,
  Receipt,
  Scale,
  Settings,
  UserCheck,
  Users,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

function StatusBadge({ status }) {
  const label = status === 'running' ? 'Running' : status === 'closed' ? 'Closed' : 'Upcoming'
  return (
    <span className={`rep-status rep-status-${status}`}>
      {status === 'running' ? (
        <PlayCircle size={12} />
      ) : status === 'closed' ? (
        <CheckCircle2 size={12} />
      ) : (
        <Clock3 size={12} />
      )}
      {label}
    </span>
  )
}

function StatCard({ icon: Icon, label, value, meta, tone }) {
  return (
    <article className={`rep-detail-stat${tone ? ` ${tone}` : ''}`}>
      <span className="rep-detail-stat-label">
        <Icon size={14} />
        {label}
      </span>
      <strong>{value}</strong>
      {meta ? <p>{meta}</p> : null}
    </article>
  )
}

export default function RealEstateProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { authFetch } = useAuth()
  const { member, addToast } = useMember()
  const [showTransferHint, setShowTransferHint] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [accountNumber, setAccountNumber] = useState(member.accountNumber || '—')
  const [project, setProject] = useState(null)
  const [userStats, setUserStats] = useState({
    totalPaid: 0,
    pendingBalance: null,
    paymentCompleted: false,
  })
  const [transactions, setTransactions] = useState([])

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    setNotFound(false)
    authFetch(`/api/projects/rep/${projectId}/`)
      .then((payload) => {
        if (!alive) return
        setAccountNumber(payload.member?.accountNumber || member.accountNumber || '—')
        setProject(payload.project || null)
        setUserStats({
          totalPaid: payload.user?.totalPaid || 0,
          pendingBalance: payload.user?.pendingBalance ?? null,
          paymentCompleted: Boolean(payload.user?.paymentCompleted),
        })
        setTransactions(payload.transactions || [])
      })
      .catch((err) => {
        if (!alive) return
        const message = err.message || 'Could not load project.'
        if (err.status === 404 || /not found/i.test(message)) {
          setNotFound(true)
          return
        }
        setError(message)
        addToast(message)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [authFetch, addToast, member.accountNumber, projectId])

  if (!loading && notFound) return <Navigate to="/projects/rep" replace />

  const isMatured = project?.status === 'closed'
  const totalBudget =
    project?.totalBudget ??
    ((project?.vendorTotalAmount || 0) + (project?.operationalCosts || 0) || 0)
  const transferHint = 'This button becomes active after the project cycle has matured.'

  return (
    <AppShell title={project?.name || 'Real Estate project'}>
      <div className="rep-page rep-detail-page">
        <button type="button" className="rep-back" onClick={() => navigate('/projects/rep')}>
          <ArrowLeft size={15} />
          Real Estate dashboard
        </button>

        {loading ? <p className="rep-status-line">Loading project details…</p> : null}
        {error && !loading ? <p className="rep-status-line danger-text">{error}</p> : null}

        {project ? (
          <>
            <section className="rep-detail-hero">
              <div>
                <h2>{project.name}</h2>
                <div className="rep-detail-pills">
                  <span>
                    <MapPin size={13} />
                    {project.location}
                  </span>
                  <span>
                    <CalendarDays size={13} />
                    Start: {project.startDate}
                  </span>
                  <span>
                    <CalendarCheck size={13} />
                    End: {project.endDate}
                  </span>
                </div>
              </div>
              <div className="rep-detail-account">
                <small>Account Number</small>
                <strong>{accountNumber}</strong>
                <StatusBadge status={project.status} />
              </div>
            </section>

            <section className="rep-section">
              <div className="rep-section-head">
                <div>
                  <h2>
                    <FileText size={18} />
                    Project financial snapshot
                  </h2>
                  <p>Land size, vendor amount, operational costs, and total project budget.</p>
                </div>
              </div>
              <div className="rep-section-body">
                {project.userHasAccess ? (
                  <div className="rep-detail-stats">
                    <StatCard
                      icon={Map}
                      label="Land size"
                      value={
                        project.landSize != null
                          ? `${Number(project.landSize).toFixed(2)} ${project.landSizeUnit || ''}`
                          : 'Not set'
                      }
                      meta="Size of land being acquired for this project."
                    />
                    <StatCard
                      icon={Coins}
                      label="Total required by vendor"
                      value={
                        project.vendorTotalAmount != null
                          ? formatUGX(project.vendorTotalAmount)
                          : 'Not set'
                      }
                      meta="Agreed total amount to be paid to the vendor."
                    />
                    <StatCard
                      icon={Settings}
                      label="Operational costs"
                      value={
                        project.operationalCosts != null
                          ? formatUGX(project.operationalCosts)
                          : 'Not set'
                      }
                      meta="Projected operational and overhead costs."
                    />
                    <StatCard
                      icon={Gauge}
                      label="Summary"
                      value={totalBudget ? formatUGX(totalBudget) : '—'}
                      meta="Vendor amount plus operational costs."
                    />
                  </div>
                ) : (
                  <p className="rep-no-access">
                    <Lock size={16} />
                    You do not have access to detailed financial information for this project.
                  </p>
                )}
              </div>
            </section>

            <section className="rep-section">
              <div className="rep-section-head">
                <div>
                  <h2>
                    <Users size={18} />
                    Member completion overview
                  </h2>
                  <p>Members marked fully paid compared with those making partial payments.</p>
                </div>
              </div>
              <div className="rep-section-body">
                {project.userHasAccess ? (
                  <div className="rep-detail-stats rep-member-stats">
                    <StatCard
                      icon={UserCheck}
                      label="Fully paid"
                      value={project.completedMembersCount}
                      meta={`Total payments: ${formatUGX(project.completedPaymentsTotal || 0)}`}
                      tone="success"
                    />
                    <StatCard
                      icon={Clock3}
                      label="Partial payments"
                      value={project.incompleteMembersCount}
                      meta={`Total payments: ${formatUGX(project.partialPaymentsTotal || 0)}`}
                      tone="warning"
                    />
                  </div>
                ) : (
                  <p className="rep-no-access">
                    <Lock size={16} />
                    You do not have access to member completion statistics for this project.
                  </p>
                )}
              </div>
            </section>

            <section className="rep-section">
              <div className="rep-section-head">
                <div>
                  <h2>
                    <Receipt size={18} />
                    Your transactions
                  </h2>
                  <p>Your payments, acquired quantity, pending balance, and payment status.</p>
                </div>
              </div>
              <div className="rep-section-body">
                <div className="rep-detail-stats rep-transaction-stats">
                  <StatCard
                    icon={Coins}
                    label="Total paid"
                    value={formatUGX(userStats.totalPaid || 0)}
                  />
                  <StatCard
                    icon={Scale}
                    label="Current balance"
                    value={
                      userStats.pendingBalance == null
                        ? '—'
                        : formatUGX(userStats.pendingBalance)
                    }
                  />
                  <StatCard
                    icon={CheckCircle2}
                    label="Payment status"
                    value={userStats.paymentCompleted ? 'Completed' : 'In progress'}
                  />
                </div>

                {transactions.length ? (
                  <div className="rep-table-wrap">
                    <table className="rep-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Amount</th>
                          <th>Acquisition</th>
                          <th>Balance</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map((transaction) => (
                          <tr key={transaction.id}>
                            <td>{transaction.date}</td>
                            <td>{formatUGX(transaction.amount)}</td>
                            <td>
                              {transaction.acquisitionQuantity
                                ? `${transaction.acquisitionQuantity} ${transaction.acquisitionUnit}`
                                : '—'}
                            </td>
                            <td>
                              {transaction.balanceAfter == null
                                ? '—'
                                : formatUGX(transaction.balanceAfter)}
                            </td>
                            <td>
                              <span
                                className={`rep-payment-status rep-payment-${transaction.paymentStatus}`}
                              >
                                {transaction.paymentStatus === 'full'
                                  ? 'Fully paid'
                                  : 'Partially paid'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="rep-empty">No transactions recorded for you on this project yet.</p>
                )}
              </div>
            </section>

            {project.userHasAccess ? (
              <section className="rep-detail-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => addToast('Add contribution is still under development')}
                >
                  Add contribution
                </button>
                <div
                  className={`rep-transfer-wrap${isMatured ? '' : ' locked'}`}
                  onMouseEnter={() => !isMatured && setShowTransferHint(true)}
                  onMouseLeave={() => setShowTransferHint(false)}
                  onFocus={() => !isMatured && setShowTransferHint(true)}
                  onBlur={() => setShowTransferHint(false)}
                  onClick={() => {
                    if (isMatured) return
                    setShowTransferHint(true)
                    window.setTimeout(() => setShowTransferHint(false), 2800)
                  }}
                >
                  {showTransferHint && !isMatured ? (
                    <div className="rep-transfer-tooltip" role="status">
                      {transferHint}
                    </div>
                  ) : null}
                  <button
                    type="button"
                    className="btn btn-outline"
                    disabled={!isMatured}
                    aria-disabled={!isMatured}
                    onClick={() => {
                      if (isMatured) {
                        addToast('Transfer to main account is still under development')
                      }
                    }}
                  >
                    Transfer to main account
                  </button>
                </div>
              </section>
            ) : null}
          </>
        ) : null}
      </div>
    </AppShell>
  )
}
