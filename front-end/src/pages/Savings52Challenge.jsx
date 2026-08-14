import { useCallback, useEffect, useState } from 'react'
import {
  ArrowRight,
  CalendarDays,
  Download,
  Flag,
  Lightbulb,
  PiggyBank,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import WscMaturedCyclePanel from '../components/WscMaturedCyclePanel'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

const EMPTY_MEMBER = {
  accountNumber: '—',
  targetAmount: 13_780_000,
  currentYearDeposits: 0,
  progressPercentage: 0,
  balanceBroughtForward: 0,
  weeksCompleted: 0,
  nextWeekToCover: 1,
  totalWeeks: 52,
  cycleComplete: false,
  cycleStartDate: null,
  cycleEndDate: null,
  cycleMaturedOn: null,
  cycleLabel: null,
  maturedCycle: null,
  fixedSavings: {
    totalInvested: 0,
    totalInterestExpected: 0,
    dailyUnfixedInterest: 0,
    unfixedInterestEarnedYtd: 0,
    latestMaturityDate: '—',
  },
  weeklyTarget: {
    currentWeek: 1,
    requiredSavings: 10_000,
    remainingWeeks: 51,
  },
}

function formatDailyUGX(amount) {
  return new Intl.NumberFormat('en-UG', {
    style: 'currency',
    currency: 'UGX',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(Number(amount) || 0))
}

function downloadCsv(filename, headers, rows) {
  const csv = [headers, ...rows]
    .map((row) => row.map((field) => `"${String(field).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function StatusBadge({ type, children }) {
  return <span className={`wsc-badge ${type}`}>{children}</span>
}

export default function Savings52Challenge() {
  const { authFetch } = useAuth()
  const { member, addToast } = useMember()
  const [showWithdrawHint, setShowWithdrawHint] = useState(false)
  const [data, setData] = useState(EMPTY_MEMBER)
  const [investments, setInvestments] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [maturedCycle, setMaturedCycle] = useState(null)

  const applyPayload = useCallback((payload) => {
    const next = { ...EMPTY_MEMBER, ...(payload.member || {}) }
    setData(next)
    setInvestments(payload.investments || [])
    setTransactions(payload.transactions || [])
    setMaturedCycle(payload.member?.maturedCycle || null)
  }, [])

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    authFetch('/api/projects/52wsc/')
      .then((payload) => {
        if (!alive) return
        applyPayload(payload)
      })
      .catch((err) => {
        if (!alive) return
        setError(err.message || 'Could not load 52WSC data.')
        addToast(err.message || 'Could not load 52WSC data.')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [authFetch, addToast, applyPayload])

  const progress = Math.min(Math.max(data.progressPercentage, 0), 100)
  const personalWeek = data.weeklyTarget?.currentWeek || data.weeksCompleted || 1
  const canTransfer =
    data.cycleComplete ||
    data.weeksCompleted >= (data.totalWeeks || 52) ||
    data.nextWeekToCover > (data.totalWeeks || 52)
  const transferHint = `This button becomes active after the cycle has matured (week ${data.totalWeeks}). Covered so far: ${data.weeksCompleted}/${data.totalWeeks}.`

  const revealTransferHint = () => {
    if (canTransfer) return
    setShowWithdrawHint(true)
  }

  const hideTransferHint = () => {
    setShowWithdrawHint(false)
  }

  const downloadSavings = () => {
    downloadCsv(
      'my_52wsc_savings.csv',
      ['Date Saved', 'Txn Type', 'Amount', 'Running Total', 'Weeks Covered', 'Receipt No.', 'Balance Forward'],
      transactions.map((tx) => [
        tx.date,
        tx.type,
        formatUGX(Math.abs(tx.amount)),
        formatUGX(tx.runningTotal),
        tx.weeksCovered,
        tx.receipt,
        tx.balanceForward == null ? '—' : formatUGX(tx.balanceForward),
      ]),
    )
  }

  const downloadInvestments = () => {
    downloadCsv(
      'my_52wsc_investments.csv',
      ['Date Invested', 'Amount', 'Interest Rate', 'Interest Earned', 'Expected Interest', 'Maturity Date', 'Status'],
      investments.map((investment) => [
        investment.startDate,
        formatUGX(investment.amount),
        investment.interestRate,
        formatUGX(investment.interestEarned),
        formatUGX(investment.expectedInterest),
        investment.maturityDate,
        investment.status,
      ]),
    )
  }

  const handleStartNewCycle = async () => {
    try {
      const payload = await authFetch('/api/projects/52wsc/start-new-cycle/', {
        method: 'POST',
        body: {},
      })
      addToast(payload.detail || 'New cycle started with your balance brought forward.')
      if (payload.dashboard) applyPayload(payload.dashboard)
    } catch (err) {
      addToast(err.message || 'Could not start a new cycle.')
    }
  }

  const handleTransferAll = async () => {
    try {
      const payload = await authFetch('/api/projects/52wsc/transfer-all/', {
        method: 'POST',
        body: {},
      })
      addToast(payload.detail || 'Matured funds were credited to your Main Account.')
      if (payload.dashboard) applyPayload(payload.dashboard)
    } catch (err) {
      addToast(err.message || 'Could not transfer matured funds.')
    }
  }

  const handleTransferMaturedPot = async () => {
    try {
      const payload = await authFetch('/api/projects/52wsc/transfer-pot/', {
        method: 'POST',
        body: {},
      })
      addToast(payload.detail || 'Matured pot was credited to your Main Account.')
      if (payload.dashboard) applyPayload(payload.dashboard)
    } catch (err) {
      addToast(err.message || 'Could not transfer matured pot.')
    }
  }

  return (
    <AppShell title="52 Weeks Saving Challenge">
      <div className="wsc-page">
        <section className="wsc-hero">
          <div>
            <span className="wsc-kicker">Personal Transactions</span>
            <h2>
              {member.firstName}&apos;s <span>52WSC</span> Dashboard
            </h2>
            <p>
              Track your personal savings progress, fixed savings, and transaction history.
              {data.cycleStartDate && data.cycleEndDate ? (
                <>
                  {' '}
                  Your cycle runs from {data.cycleStartDate} to {data.cycleEndDate}.
                </>
              ) : null}
            </p>
          </div>
          <div className="wsc-account-box">
            <small>Account Number</small>
            <strong>{data.accountNumber}</strong>
          </div>
        </section>

        {loading ? <p className="wsc-status-line">Loading your 52WSC ledger…</p> : null}
        {error && !loading ? <p className="wsc-status-line danger-text">{error}</p> : null}

        {maturedCycle ? (
          <WscMaturedCyclePanel
            cycle={maturedCycle}
            onStartNewCycle={handleStartNewCycle}
            onTransferAll={handleTransferAll}
            onTransferMaturedPot={handleTransferMaturedPot}
          />
        ) : null}

        <section className="wsc-stats-grid">
          <article className="wsc-stat-card">
            <div className="wsc-stat-head">
              <span>Total Savings</span>
              <div className="wsc-stat-icon success">
                <Wallet size={18} />
              </div>
            </div>
            <strong>{formatUGX(data.currentYearDeposits)}</strong>
            <small>Target: {formatUGX(data.targetAmount)}</small>
            <div className="wsc-progress">
              <div style={{ width: `${progress}%` }} />
            </div>
            <p>
              {data.cycleLabel
                ? `${data.cycleLabel} deposits toward the 52-week ladder.`
                : 'Deposits for your personal cycle, locked until 52 weeks complete.'}
            </p>
          </article>

          <article className="wsc-stat-card">
            <div className="wsc-stat-head">
              <span>Balance Forward</span>
              <div className="wsc-stat-icon warning">
                <ArrowRight size={18} />
              </div>
            </div>
            <strong>{formatUGX(data.balanceBroughtForward)}</strong>
            <small>
              Fully Covered Weeks: {data.weeksCompleted}
              <br />
              Next Week: {data.nextWeekToCover > 52 ? 'Complete' : data.nextWeekToCover}
            </small>
            <p>Unallocated balance for weeks not yet fully covered.</p>
          </article>

          <article className="wsc-stat-card">
            <div className="wsc-stat-head">
              <span>Fixed Savings</span>
              <div className="wsc-stat-icon info">
                <TrendingUp size={18} />
              </div>
            </div>
            <strong>{formatUGX(data.fixedSavings.totalInvested)}</strong>
            <small>
              Expected Interest: {formatUGX(data.fixedSavings.totalInterestExpected)}
              <br />
              Maturity: {data.fixedSavings.latestMaturityDate}
            </small>
            <p>Funds fixed from your 52WSC savings pool.</p>
          </article>

          <article className="wsc-stat-card">
            <div className="wsc-stat-head">
              <span>Interest on Unfixed Savings</span>
              <div className="wsc-stat-icon purple">
                <PiggyBank size={18} />
              </div>
            </div>
            <strong>
              {formatDailyUGX(data.fixedSavings.dailyUnfixedInterest)} <em>daily</em>
            </strong>
            <small>Accrued: {formatUGX(data.fixedSavings.unfixedInterestEarnedYtd)}</small>
            <p>15% annualized on unfixed savings (daily accrual).</p>
          </article>
        </section>

        <section className="wsc-week-card">
          <div className="wsc-week-head">
            <h3>
              <CalendarDays size={18} />
              Your personal week progress
            </h3>
          </div>

          <div className="wsc-week-grid">
            <div className="wsc-required-box">
              <div className="wsc-required-icon">
                <Wallet size={22} />
              </div>
              <div>
                <span>Required Savings</span>
                <strong>{formatUGX(data.weeklyTarget.requiredSavings)}</strong>
                <small>
                  Your week {personalWeek} × UGX 10,000
                  {data.cycleStartDate ? ` · from ${data.cycleStartDate}` : ''}
                </small>
              </div>
            </div>

            <div className="wsc-compact-stats">
              <div>
                <CalendarDays size={18} />
                <span>Your Week</span>
                <b>Week {personalWeek}</b>
              </div>
              <div>
                <Flag size={18} />
                <span>Remaining</span>
                <b>{data.weeklyTarget.remainingWeeks} weeks</b>
              </div>
            </div>

            <div className="wsc-motivation">
              <Lightbulb size={17} />
              <p>
                {data.cycleStartDate && data.cycleEndDate
                  ? `Your 52 weeks savings challenge runs from ${data.cycleStartDate} and will end on ${data.cycleEndDate}.`
                  : 'Your 52 weeks savings challenge starts on your first deposit date for this cycle.'}
              </p>
            </div>
          </div>
        </section>

        <section className="wsc-table-card">
          <div className="wsc-card-head">
            <h3>My Investment History</h3>
            <button type="button" className="btn btn-outline btn-sm" onClick={downloadInvestments}>
              <Download size={15} />
              Download Data
            </button>
          </div>
          <div className="wsc-table-wrap">
            <table className="wsc-table">
              <thead>
                <tr>
                  <th>Date Invested</th>
                  <th>Amount</th>
                  <th>Interest Rate</th>
                  <th>Interest Earned</th>
                  <th>Expected Interest</th>
                  <th>Maturity Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {investments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center">
                      No fixed savings yet
                    </td>
                  </tr>
                ) : (
                  investments.map((investment) => (
                    <tr key={investment.id}>
                      <td data-label="Date Invested">{investment.startDate}</td>
                      <td data-label="Amount">{formatUGX(investment.amount)}</td>
                      <td data-label="Interest Rate">{investment.interestRate}</td>
                      <td data-label="Interest Earned">{formatUGX(investment.interestEarned)}</td>
                      <td data-label="Expected Interest">{formatUGX(investment.expectedInterest)}</td>
                      <td data-label="Maturity Date">{investment.maturityDate}</td>
                      <td data-label="Status">
                        <StatusBadge
                          type={
                            String(investment.status).toLowerCase() === 'fixed'
                              ? 'success'
                              : 'warning'
                          }
                        >
                          {investment.status}
                        </StatusBadge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="wsc-table-card">
          <div className="wsc-card-head">
            <h3>My Savings History</h3>
            <button type="button" className="btn btn-outline btn-sm" onClick={downloadSavings}>
              <Download size={15} />
              Download Data
            </button>
          </div>
          <div className="wsc-table-wrap">
            <table className="wsc-table">
              <thead>
                <tr>
                  <th>Date Saved</th>
                  <th>Txn Type</th>
                  <th>Amount</th>
                  <th>Running Total</th>
                  <th>Weeks Covered</th>
                  <th>Receipt No.</th>
                  <th>Balance Forward</th>
                </tr>
              </thead>
              <tbody>
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center">
                      No savings transactions yet
                    </td>
                  </tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.id}>
                      <td data-label="Date Saved">{tx.date}</td>
                      <td data-label="Txn Type">
                        <StatusBadge
                          type={
                            tx.typeKey === 'deposit'
                              ? 'success'
                              : tx.typeKey === 'withdrawal'
                                ? 'danger'
                                : 'warning'
                          }
                        >
                          {tx.type}
                        </StatusBadge>
                      </td>
                      <td data-label="Amount" className={tx.amount < 0 ? 'danger-text' : ''}>
                        {tx.amount < 0 ? '-' : ''}
                        {formatUGX(Math.abs(tx.amount))}
                      </td>
                      <td data-label="Running Total">{formatUGX(tx.runningTotal)}</td>
                      <td data-label="Weeks Covered">{tx.weeksCovered}</td>
                      <td data-label="Receipt No.">{tx.receipt}</td>
                      <td data-label="Balance Forward">
                        {tx.balanceForward == null ? '—' : formatUGX(tx.balanceForward)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <div className="wsc-footer-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => addToast('Add contribution is still under development')}
          >
            Add contribution
          </button>
          <div
            className={`wsc-withdraw-wrap ${!canTransfer || maturedCycle?.status === 'awaiting_decision' ? 'locked' : ''}`}
            onMouseEnter={revealTransferHint}
            onMouseLeave={hideTransferHint}
            onFocus={revealTransferHint}
            onBlur={hideTransferHint}
            onClick={(e) => {
              if (canTransfer && maturedCycle?.status !== 'awaiting_decision') return
              e.preventDefault()
              setShowWithdrawHint(true)
              window.setTimeout(() => setShowWithdrawHint(false), 2800)
            }}
          >
            {showWithdrawHint &&
            (!canTransfer || maturedCycle?.status === 'awaiting_decision') ? (
              <div className="wsc-withdraw-tooltip" role="status">
                {maturedCycle?.status === 'awaiting_decision'
                  ? 'Use Choose next step on the matured cycle card above.'
                  : transferHint}
              </div>
            ) : null}
            <button
              type="button"
              className="btn btn-outline"
              disabled={!canTransfer || maturedCycle?.status === 'awaiting_decision'}
              onClick={() => {
                if (!canTransfer || maturedCycle?.status === 'awaiting_decision') return
                addToast('Use the matured cycle panel to transfer or start a new cycle.')
              }}
            >
              Transfer to main account
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
