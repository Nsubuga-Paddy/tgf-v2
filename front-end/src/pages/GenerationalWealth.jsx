import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  ArrowLeftRight,
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
  totalRedeemableInterest: 0,
  totalInterestRedeemed: 0,
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

function parseAmountInput(raw) {
  if (raw == null || String(raw).trim() === '') return null
  const cleaned = String(raw).replace(/,/g, '').trim()
  const n = Number(cleaned)
  if (!Number.isFinite(n) || n <= 0) return null
  return Math.round(n)
}

function InterestLedger({ deposit, onRedeem, redeeming }) {
  const ledger = deposit.interestLedger
  const maxAmount = Math.round(Number(ledger?.redeemable || 0))
  const [amount, setAmount] = useState(String(maxAmount || ''))
  const busy = redeeming === deposit.depositId
  const canRedeem = Boolean(ledger?.canRedeem)

  useEffect(() => {
    setAmount(String(Math.round(Number(ledger?.redeemable || 0))))
  }, [ledger?.redeemable, deposit.depositId])

  if (!ledger?.enabled) return null

  const submit = () => {
    const parsed = parseAmountInput(amount)
    if (parsed == null) return
    onRedeem(deposit, parsed)
  }

  return (
    <div className="gwc-interest-ledger">
      <div className="gwc-interest-ledger-head">
        <h5>
          <Receipt size={14} />
          Monthly interest ledger
        </h5>
        <p>
          Calendar-month interest earned, transferred to Main Account, and still redeemable.
        </p>
      </div>

      <div className="gwc-interest-summary">
        <div>
          <span>Earned to date</span>
          <strong>{formatUGX(ledger.totalEarned)}</strong>
        </div>
        <div>
          <span>Transferred so far</span>
          <strong>{formatUGX(ledger.totalRedeemed)}</strong>
        </div>
        <div>
          <span>Redeemable now</span>
          <strong className="gwc-fd-accent">{formatUGX(ledger.redeemable)}</strong>
        </div>
      </div>

      {(ledger.months || []).length > 0 ? (
        <div className="gwc-table-wrap">
          <table className="gwc-ledger-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Earned</th>
                <th>Transferred</th>
                <th>Still open</th>
              </tr>
            </thead>
            <tbody>
              {ledger.months.map((row) => (
                <tr key={row.periodKey}>
                  <td>{row.periodLabel}</td>
                  <td>{formatUGX(row.earned)}</td>
                  <td>{formatUGX(row.transferred)}</td>
                  <td>{formatUGX(row.carry)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="gwc-ledger-empty">
          No completed calendar months yet. Interest becomes redeemable after each month ends.
        </p>
      )}

      {(ledger.redemptions || []).length > 0 ? (
        <ul className="gwc-redemption-list">
          {ledger.redemptions.map((r) => (
            <li key={r.id}>
              <span>
                {r.redeemedAt}
                {r.reference ? ` · ${r.reference}` : ''}
              </span>
              <strong>−{formatUGX(r.amount)}</strong>
            </li>
          ))}
        </ul>
      ) : null}

      {canRedeem ? (
        <div className="gwc-redeem-inline">
          <label className="gwc-redeem-field">
            <span>Redeem amount (UGX) — full or partial</span>
            <input
              type="text"
              inputMode="numeric"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={Boolean(redeeming)}
            />
          </label>
          <div className="gwc-redeem-actions">
            <button
              type="button"
              className="btn btn-outline btn-sm"
              disabled={Boolean(redeeming) || maxAmount <= 0}
              onClick={() => setAmount(String(maxAmount))}
            >
              Use full amount
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm gwc-redeem-btn"
              disabled={!canRedeem || Boolean(redeeming)}
              onClick={submit}
            >
              <ArrowLeftRight size={14} />
              {busy ? 'Transferring…' : 'Transfer to Main Account'}
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="btn btn-primary btn-sm gwc-redeem-btn" disabled>
          No redeemable interest yet
        </button>
      )}
    </div>
  )
}

function DepositCard({ deposit, onRedeem, redeeming }) {
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
          {deposit.redeemableMonthlyInterest ? (
            <span className="gwc-status gwc-status-redeemable">Monthly redeem</span>
          ) : null}
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

        <InterestLedger deposit={deposit} onRedeem={onRedeem} redeeming={redeeming} />
      </div>
    </article>
  )
}

export default function GenerationalWealth() {
  const { authFetch } = useAuth()
  const { member, addToast, reloadDashboard } = useMember()
  const [showWithdrawHint, setShowWithdrawHint] = useState(false)
  const [deposits, setDeposits] = useState([])
  const [portfolio, setPortfolio] = useState(EMPTY_PORTFOLIO)
  const [activities, setActivities] = useState([])
  const [meta, setMeta] = useState({ canRedeemInterest: false })
  const [accountNumber, setAccountNumber] = useState(member.accountNumber || '—')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [redeeming, setRedeeming] = useState(false)

  const applyPayload = useCallback(
    (payload) => {
      setAccountNumber(payload.account?.accountNumber || member.accountNumber || '—')
      setPortfolio({ ...EMPTY_PORTFOLIO, ...(payload.portfolio || {}) })
      setDeposits(payload.deposits || [])
      setActivities(payload.activities || [])
      setMeta(payload.meta || {})
    },
    [member.accountNumber],
  )

  const loadGwc = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const payload = await authFetch('/api/projects/gwc/')
      applyPayload(payload)
    } catch (err) {
      const message = err.message || 'Could not load GWC data.'
      setError(message)
      addToast(message)
    } finally {
      setLoading(false)
    }
  }, [authFetch, addToast, applyPayload])

  useEffect(() => {
    loadGwc()
  }, [loadGwc])

  const handleRedeemInterest = async (deposit, amountOverride = null) => {
    if (redeeming) return
    const maxAmount = Math.round(Number(deposit?.interestLedger?.redeemable || 0))
    const amount =
      amountOverride != null
        ? Math.round(Number(amountOverride))
        : maxAmount
    if (!amount || amount <= 0) {
      addToast('Enter a valid amount greater than zero.')
      return
    }
    if (amount > maxAmount) {
      addToast(
        `Amount cannot exceed redeemable interest (${formatUGX(maxAmount)}).`,
      )
      return
    }
    setRedeeming(deposit.depositId)
    try {
      const payload = await authFetch('/api/projects/gwc/redeem-interest/', {
        method: 'POST',
        body: { depositId: deposit.depositId, amount },
      })
      addToast(
        payload.detail ||
          'Redeemable interest was credited to your Main Account.',
      )
      if (payload.dashboard) {
        applyPayload(payload.dashboard)
      } else {
        await loadGwc()
      }
      if (reloadDashboard) {
        await reloadDashboard({ silent: true })
      }
    } catch (err) {
      addToast(err.message || 'Could not transfer GWC interest.')
    } finally {
      setRedeeming(false)
    }
  }

  const maturedDeposits = deposits.filter((d) => d.status === 'Matured')
  const canTransferMatured = maturedDeposits.length > 0
  const canRedeemInterest = Boolean(meta.canRedeemInterest) || Number(portfolio.totalRedeemableInterest) > 0
  const transferHint = canTransferMatured
    ? `${maturedDeposits.length} matured deposit${maturedDeposits.length === 1 ? '' : 's'} ready for maturity settlement.`
    : canRedeemInterest
      ? 'Use Transfer redeemable interest on a deposit card to move monthly interest to Main Account.'
      : 'Monthly interest redeem is available only when admin enables it on your deposit, after completed calendar months.'

  const revealTransferHint = () => {
    if (canTransferMatured) return
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
                {Number(portfolio.totalRedeemableInterest) > 0 ||
                Number(portfolio.totalInterestRedeemed) > 0 ? (
                  <div className="gwc-ph-stat">
                    <span className="gwc-ph-label">Redeemable interest</span>
                    <span className="gwc-ph-value gwc-fd-accent">
                      {formatUGX(portfolio.totalRedeemableInterest)}
                    </span>
                  </div>
                ) : null}
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
                      <DepositCard
                        key={deposit.depositId}
                        deposit={deposit}
                        onRedeem={handleRedeemInterest}
                        redeeming={redeeming}
                      />
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
                    className={`gwc-withdraw-wrap ${!canTransferMatured ? 'locked' : ''}`}
                    onMouseEnter={revealTransferHint}
                    onMouseLeave={hideTransferHint}
                    onFocus={revealTransferHint}
                    onBlur={hideTransferHint}
                    onClick={(e) => {
                      if (canTransferMatured) return
                      e.preventDefault()
                      setShowWithdrawHint(true)
                      window.setTimeout(() => setShowWithdrawHint(false), 2800)
                    }}
                  >
                    {showWithdrawHint && !canTransferMatured ? (
                      <div className="gwc-withdraw-tooltip" role="status">
                        {transferHint}
                      </div>
                    ) : null}
                    <button
                      type="button"
                      className="btn btn-outline"
                      disabled={!canTransferMatured}
                      aria-disabled={!canTransferMatured}
                      onClick={() => {
                        if (!canTransferMatured) return
                        addToast(
                          'Matured principal transfer is still under development. Monthly interest redeem is available on eligible deposit cards.',
                        )
                      }}
                    >
                      Transfer matured to main
                    </button>
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
