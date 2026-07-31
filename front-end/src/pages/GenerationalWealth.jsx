import { useEffect, useState } from 'react'
import {
  Activity,
  Circle,
  Fingerprint,
  Flag,
  Layers,
  Receipt,
  Vault,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

const EMPTY_PORTFOLIO = {
  totalPrincipal: 0,
  totalAccruedInterest: 0,
  totalMaturityValue: 0,
}

function titleCase(value) {
  if (!value) return ''
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function StatusBadge({ deposit }) {
  if (deposit.status === 'Active' && deposit.isUpcoming) {
    return (
      <span className="gwc-status gwc-status-upcoming">
        <Circle size={8} fill="currentColor" />
        Matures soon
      </span>
    )
  }
  if (deposit.status === 'Active') {
    return (
      <span className="gwc-status gwc-status-active">
        <Circle size={8} fill="currentColor" />
        Active
      </span>
    )
  }
  if (deposit.status === 'Matured') {
    return (
      <span className="gwc-status gwc-status-matured">
        <Flag size={11} />
        Matured
      </span>
    )
  }
  if (deposit.status === 'Withdrawn') {
    return <span className="gwc-status gwc-status-withdrawn">Withdrawn</span>
  }
  if (deposit.status === 'Cancelled') {
    return <span className="gwc-status gwc-status-cancelled">Cancelled</span>
  }
  return <span className="gwc-status">{deposit.status}</span>
}

function DepositCard({ deposit }) {
  const methodLabel = titleCase(deposit.interestMethod)
  const rate = Number(deposit.interestRate || 0)
  const rateLine = `${rate.toFixed(2)}% p.a · ${methodLabel}`

  return (
    <article className="gwc-fd-card">
      <div className="gwc-fd-card-top">
        <span className="gwc-fd-id">
          <Fingerprint size={12} />
          FD · {deposit.depositId}
        </span>
        <div className="gwc-fd-badges">
          <StatusBadge deposit={deposit} />
        </div>
      </div>

      <div className="gwc-fd-highlight">
        <div className="gwc-fd-highlight-cell">
          <span className="gwc-fd-highlight-label">You deposited</span>
          <span className="gwc-fd-highlight-value">{formatUGX(deposit.principalAmount)}</span>
          <span className="gwc-fd-highlight-sub">{rateLine}</span>
        </div>
        <div className="gwc-fd-highlight-cell gwc-fd-highlight-daily">
          <span className="gwc-fd-highlight-label">Earning daily</span>
          <span className="gwc-fd-highlight-value gwc-fd-accent">
            {formatUGX(deposit.dailyInterest)}
          </span>
          <span className="gwc-fd-highlight-sub">
            ~{formatUGX(deposit.monthlyInterest)} / month
          </span>
        </div>
        <div className="gwc-fd-highlight-cell">
          <span className="gwc-fd-highlight-label">Expected at maturity</span>
          <span className="gwc-fd-highlight-value">
            {formatUGX(deposit.projectedMaturityAmount)}
          </span>
          <span className="gwc-fd-highlight-sub">
            Accrued so far: {formatUGX(deposit.accruedInterest)}
          </span>
        </div>
      </div>

      <div className="gwc-fd-body">
        <div className="gwc-fd-progress-wrap">
          <div className="gwc-progress-bar">
            <div style={{ width: `${deposit.completionPercent}%` }} />
          </div>
          <div className="gwc-progress-labels">
            <span>{deposit.elapsedDurationDisplay}</span>
            <span>
              <strong>{deposit.completionPercent}%</strong>
            </span>
            <span>{deposit.remainingDurationDisplay}</span>
          </div>
        </div>

        <div className="gwc-fd-chip-row">
          <span className="gwc-fd-chip">
            <strong>Received</strong> {deposit.transactionDate}
          </span>
          <span className="gwc-fd-chip">
            <strong>Start</strong> {deposit.startDate}
          </span>
          <span className="gwc-fd-chip">
            <strong>Matures</strong> {deposit.maturityDate}
          </span>
          <span className="gwc-fd-chip">
            <strong>Tenure</strong> {deposit.tenureDisplay}
          </span>
          {deposit.interestMethod === 'compound' && deposit.compoundingFrequency ? (
            <span className="gwc-fd-chip">
              <strong>Compound</strong> {titleCase(deposit.compoundingFrequency)}
            </span>
          ) : null}
          <span className="gwc-fd-chip gwc-fd-chip-payout">
            <Receipt size={12} />
            {deposit.payoutStructureDisplay}
          </span>
        </div>

        <div className="gwc-fd-metrics-foot">
          <span>
            Interest at maturity (net){' '}
            <em>{formatUGX(deposit.interestAtMaturityAfterTax)}</em>
          </span>
        </div>
      </div>
    </article>
  )
}

export default function GenerationalWealth() {
  const { authFetch } = useAuth()
  const { member, addToast } = useMember()
  const [showWithdrawHint, setShowWithdrawHint] = useState(false)
  const [deposits, setDeposits] = useState([])
  const [portfolio, setPortfolio] = useState(EMPTY_PORTFOLIO)
  const [activities, setActivities] = useState([])
  const [accountNumber, setAccountNumber] = useState(member.accountNumber || '—')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    authFetch('/api/projects/gwc/')
      .then((payload) => {
        if (!alive) return
        setAccountNumber(payload.account?.accountNumber || member.accountNumber || '—')
        setPortfolio({ ...EMPTY_PORTFOLIO, ...(payload.portfolio || {}) })
        setDeposits(payload.deposits || [])
        setActivities(payload.activities || [])
      })
      .catch((err) => {
        if (!alive) return
        const message = err.message || 'Could not load GWC data.'
        setError(message)
        addToast(message)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [authFetch, addToast, member.accountNumber])

  const maturedDeposits = deposits.filter((d) => d.status === 'Matured')
  const canTransfer = maturedDeposits.length > 0
  const transferHint = canTransfer
    ? `${maturedDeposits.length} matured deposit${maturedDeposits.length === 1 ? '' : 's'} ready to transfer to your main account.`
    : 'This button becomes active after the deposit cycle has matured.'

  const revealTransferHint = () => {
    if (canTransfer) return
    setShowWithdrawHint(true)
  }

  const hideTransferHint = () => {
    setShowWithdrawHint(false)
  }

  return (
    <AppShell title="Generational Wealth Creation">
      <div className="gwc-page">
        <section className="gwc-hero">
          <div>
            <h2>Generational Wealth Creation</h2>
            <p>25% annualized interest in one year · Individual or group investment</p>
          </div>
          <div className="gwc-account-box">
            <small>Account</small>
            <strong>{accountNumber}</strong>
          </div>
        </section>

        {loading ? <p className="gwc-status-line">Loading your GWC deposits…</p> : null}
        {error && !loading ? <p className="gwc-status-line danger-text">{error}</p> : null}

        <section className="gwc-panel">
          <div className="gwc-panel-head">
            <div>
              <h3>
                <Vault size={18} />
                GWC fixed deposits
              </h3>
              <p>
                Money you deposited, interest earned each day, and what you can expect at maturity
                — all in one place.
              </p>
            </div>
          </div>

          <div className="gwc-panel-body">
            <div className="gwc-portfolio-hero">
              <div className="gwc-portfolio-copy">
                <h4>Portfolio snapshot</h4>
                <p>
                  Totals across all your fixed deposits — deposited principal, interest earned so
                  far, and expected payout at maturity.
                </p>
              </div>
              <div className="gwc-portfolio-stats">
                <div className="gwc-ph-stat">
                  <span className="gwc-ph-label">Total deposited</span>
                  <span className="gwc-ph-value">{formatUGX(portfolio.totalPrincipal)}</span>
                </div>
                <div className="gwc-ph-stat">
                  <span className="gwc-ph-label">Interest so far</span>
                  <span className="gwc-ph-value">
                    {formatUGX(portfolio.totalAccruedInterest)}
                  </span>
                </div>
                <div className="gwc-ph-stat">
                  <span className="gwc-ph-label">Expected at maturity</span>
                  <span className="gwc-ph-value">
                    {formatUGX(portfolio.totalMaturityValue)}
                  </span>
                </div>
              </div>
            </div>

            <div className="gwc-divider" />

            <div className="gwc-fd-shell">
              <div>
                <div className="gwc-fd-block-title">
                  <h4>
                    <Layers size={18} />
                    Your deposits
                  </h4>
                  <span className="gwc-fd-count">
                    {deposits.length} deposit{deposits.length === 1 ? '' : 's'}
                  </span>
                </div>

                {deposits.length === 0 && !loading ? (
                  <p className="gwc-empty">No fixed deposits yet.</p>
                ) : (
                  <div className="gwc-fd-grid">
                    {deposits.map((deposit) => (
                      <DepositCard key={deposit.depositId} deposit={deposit} />
                    ))}
                  </div>
                )}
              </div>

              <aside className="gwc-aside">
                <h4>
                  <Activity size={16} />
                  Activity
                </h4>
                <p className="gwc-aside-intro">Latest movements on your fixed deposits.</p>
                <ul className="gwc-activity-list">
                  {activities.length === 0 ? (
                    <li className="gwc-activity-empty">No activity yet.</li>
                  ) : (
                    activities.map((activity) => (
                      <li key={activity.id} className="gwc-activity-item">
                        <div className="gwc-activity-main">
                          <div className="gwc-activity-title">{activity.description}</div>
                          <div className="gwc-activity-detail">
                            {activity.timestamp} · FD {activity.depositId} ·{' '}
                            {titleCase(activity.type)}
                          </div>
                        </div>
                        {activity.amount != null ? (
                          <div className="gwc-activity-meta">
                            <span className={`gwc-activity-${activity.type}`}>
                              {activity.type === 'debit' ? '−' : activity.type === 'credit' ? '+' : ''}
                              {Math.round(activity.amount).toLocaleString('en-UG')}
                            </span>
                            <div className="gwc-activity-unit">UGX</div>
                          </div>
                        ) : null}
                      </li>
                    ))
                  )}
                </ul>

                <div className="gwc-aside-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => addToast('Add deposit is still under development')}
                  >
                    Add deposit
                  </button>
                  <div
                    className={`gwc-withdraw-wrap ${!canTransfer ? 'locked' : ''}`}
                    onMouseEnter={revealTransferHint}
                    onMouseLeave={hideTransferHint}
                    onFocus={revealTransferHint}
                    onBlur={hideTransferHint}
                    onClick={(e) => {
                      if (canTransfer) return
                      e.preventDefault()
                      setShowWithdrawHint(true)
                      window.setTimeout(() => setShowWithdrawHint(false), 2800)
                    }}
                  >
                    {showWithdrawHint && !canTransfer ? (
                      <div className="gwc-withdraw-tooltip" role="status">
                        {transferHint}
                      </div>
                    ) : null}
                    <button
                      type="button"
                      className="btn btn-outline"
                      disabled={!canTransfer}
                      aria-disabled={!canTransfer}
                      aria-describedby={
                        !canTransfer && showWithdrawHint ? 'gwc-transfer-hint' : undefined
                      }
                      onClick={() => {
                        if (!canTransfer) return
                        addToast('Transfer to main account is still under development')
                      }}
                    >
                      Transfer to main account
                    </button>
                    {showWithdrawHint && !canTransfer ? (
                      <span id="gwc-transfer-hint" className="sr-only">
                        {transferHint}
                      </span>
                    ) : null}
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  )
}
