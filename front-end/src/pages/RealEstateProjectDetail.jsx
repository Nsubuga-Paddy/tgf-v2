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
  RotateCcw,
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
  const { member, addToast, reloadDashboard } = useMember()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [accountNumber, setAccountNumber] = useState(member.accountNumber || '—')
  const [project, setProject] = useState(null)
  const [userStats, setUserStats] = useState({
    totalPaid: 0,
    pendingBalance: null,
    paymentCompleted: false,
    refundableAmount: 0,
    pendingRefundTotal: 0,
    projectStatus: '',
    projectStatusLabel: '',
    latestRefundStatus: '',
    latestRefundStatusDisplay: '',
  })
  const [transactions, setTransactions] = useState([])
  const [refreshKey, setRefreshKey] = useState(0)
  const [refundSubmitting, setRefundSubmitting] = useState(false)

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
          refundableAmount: payload.user?.refundableAmount || 0,
          pendingRefundTotal: payload.user?.pendingRefundTotal || 0,
          projectStatus: payload.user?.projectStatus || '',
          projectStatusLabel: payload.user?.projectStatusLabel || '',
          latestRefundStatus: payload.user?.latestRefundStatus || '',
          latestRefundStatusDisplay: payload.user?.latestRefundStatusDisplay || '',
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
  }, [authFetch, addToast, member.accountNumber, projectId, refreshKey])

  if (!loading && notFound) return <Navigate to="/projects/rep" replace />

  const totalBudget =
    project?.totalBudget ??
    ((project?.vendorTotalAmount || 0) + (project?.operationalCosts || 0) || 0)
  const refundable = Number(userStats.refundableAmount || 0)

  const requestRefund = () => {
    if (!project || refundSubmitting) return
    if (userStats.paymentCompleted) {
      addToast('Fully paid projects move to land title processing, not refund.')
      return
    }
    if (userStats.latestRefundStatus === 'pending' || userStats.latestRefundStatus === 'approved') {
      addToast('Your refund request is already awaiting administrator processing.')
      return
    }
    if (!refundable) {
      addToast('No refundable amount is currently available for this project.')
      return
    }
    setRefundSubmitting(true)
    authFetch(`/api/projects/rep/${project.id}/refund/`, {
      method: 'POST',
      body: {
        amount: refundable,
        reason: 'Unable to complete Real Estate project payment',
      },
    })
      .then((payload) => {
        addToast(
          payload.detail ||
            'Refund request submitted. A staff member will get in touch with you to confirm this request before it is processed.',
        )
        setRefreshKey((key) => key + 1)
        if (typeof reloadDashboard === 'function') {
          reloadDashboard({ silent: true })
        }
      })
      .catch((err) => {
        addToast(err.message || 'Could not submit refund request.')
      })
      .finally(() => {
        setRefundSubmitting(false)
      })
  }

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
                    value={
                      userStats.projectStatusLabel ||
                      (userStats.paymentCompleted ? 'Completed' : 'In progress')
                    }
                  />
                  <StatCard
                    icon={RotateCcw}
                    label="Refundable amount"
                    value={formatUGX(refundable)}
                    meta="No penalties are deducted. Pending refund requests reduce this figure."
                  />
                  <StatCard
                    icon={Clock3}
                    label="Pending refund"
                    value={formatUGX(userStats.pendingRefundTotal || 0)}
                    meta={
                      Number(userStats.pendingRefundTotal || 0) > 0
                        ? 'Held while a staff member contacts you to confirm, then credits Main Account after approval.'
                        : 'No refund request is currently awaiting review.'
                    }
                    tone={Number(userStats.pendingRefundTotal || 0) > 0 ? 'warning' : undefined}
                  />
                </div>

                {transactions.length ? (
                  <div className="rep-table-wrap">
                    <table className="rep-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Amount</th>
                          <th>Type</th>
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
                              {transaction.type === 'refund'
                                ? 'Refund'
                                : transaction.type === 'adjustment'
                                  ? 'Adjustment'
                                  : 'Payment'}
                            </td>
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
                <button
                  type="button"
                  className="btn btn-outline"
                  disabled={loading || refundSubmitting}
                  onClick={requestRefund}
                >
                  <RotateCcw size={15} />
                  {refundSubmitting ? 'Submitting refund…' : 'Request refund'}
                </button>
                {userStats.paymentCompleted ? (
                  <p className="rep-transfer-note">Fully paid projects move toward land title processing.</p>
                ) : userStats.latestRefundStatus === 'pending' || userStats.latestRefundStatus === 'approved' ? (
                  <p className="rep-transfer-note">
                    Refund of {formatUGX(userStats.pendingRefundTotal || 0)} is held. A staff
                    member will get in touch with you to confirm this request before it is
                    credited to your Main Account.
                  </p>
                ) : refundable > 0 ? (
                  <p className="rep-transfer-note">
                    Request a full no-penalty refund of {formatUGX(refundable)} to your Main Account.
                    Bank details must be complete on your profile.
                  </p>
                ) : (
                  <p className="rep-transfer-note">No refundable amount is currently available.</p>
                )}
              </section>
            ) : null}
          </>
        ) : null}
      </div>
    </AppShell>
  )
}
