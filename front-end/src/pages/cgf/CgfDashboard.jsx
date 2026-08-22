import { useCallback, useEffect, useState } from 'react'
import {
  ArrowLeftRight,
  Baby,
  Clock,
  Info,
  Receipt,
  ShoppingCart,
  Sprout,
  Wallet,
} from 'lucide-react'
import CgfShell from '../../components/cgf/CgfShell'
import {
  CGF_BREEDING_INFO,
  maturityFromPurchaseDate,
  purchaseStatusBadge,
} from '../../data/cgfData'
import { useAuth } from '../../context/AuthContext'
import { useMember } from '../../context/MemberContext'
import { formatUGX } from '../../utils/format'

const EMPTY_SUMMARY = {
  accountNumber: '—',
  totalGoats: 0,
  totalInvested: 0,
  totalPaid: 0,
  totalBalance: 0,
  totalExpectedKids: 0,
  nextMaturityDate: null,
  canTransferMatured: false,
  maturedTransferAmount: 0,
  maturedCycleCount: 0,
  maturedGoats: 0,
  maturedKids: 0,
}

function Badge({ tone, children }) {
  return <span className={`cgf-badge cgf-badge-${tone}`}>{children}</span>
}

export default function CgfDashboard() {
  const { authFetch } = useAuth()
  const { member, addToast, reloadDashboard } = useMember()
  const [summary, setSummary] = useState(EMPTY_SUMMARY)
  const [farmAccounts, setFarmAccounts] = useState([])
  const [purchases, setPurchases] = useState([])
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [transferring, setTransferring] = useState(false)

  const applyPayload = useCallback((payload) => {
    setSummary({ ...EMPTY_SUMMARY, ...(payload.member || {}) })
    setFarmAccounts(payload.farmAccounts || [])
    setPurchases(payload.purchases || [])
    setPayments((payload.payments || []).slice(0, 10))
  }, [])

  const loadCgf = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const payload = await authFetch('/api/projects/cgf/')
      applyPayload(payload)
    } catch (err) {
      const message = err.message || 'Could not load CGF dashboard.'
      setError(message)
      addToast(message)
    } finally {
      setLoading(false)
    }
  }, [authFetch, addToast, applyPayload])

  useEffect(() => {
    loadCgf()
  }, [loadCgf])

  const handleTransferToMain = async (farmId = null) => {
    if (transferring) return
    setTransferring(farmId || 'all')
    try {
      const payload = await authFetch('/api/projects/cgf/transfer-to-main/', {
        method: 'POST',
        body: farmId ? { farmId } : {},
      })
      addToast(
        payload.detail ||
          'Matured CGF value was credited to your Main Account.',
      )
      if (payload.dashboard) {
        applyPayload(payload.dashboard)
      } else {
        await loadCgf()
      }
      await reloadDashboard({ silent: true })
    } catch (err) {
      addToast(err.message || 'Could not transfer matured CGF funds.')
    } finally {
      setTransferring(false)
    }
  }

  const accountNumber = summary.accountNumber || member.accountNumber || '—'

  return (
    <CgfShell title="Commercial Goat Farming">
      <section className="cgf-hero">
        <div>
          <h2>Welcome back, {member.firstName}!</h2>
          <p>Track your investment progress and manage your goat farm efficiently</p>
          <div className="cgf-account-row">
            <div className="cgf-account-left">
              <span>Account Number</span>
              <strong>{accountNumber}</strong>
            </div>
            <button
              type="button"
              className="btn btn-outline cgf-purchase-btn"
              onClick={() => addToast('Purchase package is still under development')}
            >
              <ShoppingCart size={15} />
              Purchase package
            </button>
          </div>
        </div>
      </section>

      {loading ? <p className="cgf-status-line">Loading your CGF dashboard…</p> : null}
      {error && !loading ? <p className="cgf-status-line danger-text">{error}</p> : null}

      <section className="cgf-stats">
        <article className="cgf-stat">
          <div className="cgf-stat-icon primary">
            <Sprout size={18} />
          </div>
          <strong>{summary.totalGoats}</strong>
          <span>Total Goats</span>
          <small>Ledger-based</small>
        </article>
        <article className="cgf-stat">
          <div className="cgf-stat-icon success">
            <Wallet size={18} />
          </div>
          <strong>{formatUGX(summary.totalInvested)}</strong>
          <span>Total Invested (Charges)</span>
          <small>All packages</small>
        </article>
        <article className="cgf-stat">
          <div className="cgf-stat-icon warning">
            <Clock size={18} />
          </div>
          <strong>{formatUGX(summary.totalBalance)}</strong>
          <span>Balance Due</span>
          <small>Outstanding</small>
        </article>
        <article className="cgf-stat">
          <div className="cgf-stat-icon info">
            <Baby size={18} />
          </div>
          <strong>{summary.totalExpectedKids}</strong>
          <span>Expected Kids</span>
          <small>
            Next maturity: <b>{summary.nextMaturityDate || 'All mature'}</b>
          </small>
        </article>
      </section>

      {farmAccounts.length > 0 ? (
        <>
          <section className="cgf-card">
            <div className="cgf-card-head">
              <h3>
                <Sprout size={18} />
                Your Goat Holdings by Farm
              </h3>
              <Badge tone="info">Breeding cycle: 14 months</Badge>
            </div>
            <div className="cgf-table-wrap">
              <table className="cgf-table">
                <thead>
                  <tr>
                    <th>Farm</th>
                    <th>Current Goats</th>
                    <th>Expected Kids</th>
                    <th>Matures On</th>
                    <th>Cycle Start</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {farmAccounts.map((account) => {
                    const progressPct = Number(account.progressPct || 0)
                    const cycleComplete = Boolean(
                      account.canTransfer || account.isCycleComplete,
                    )
                    const remaining = maturityFromPurchaseDate(
                      account.cycleStartAtIso || account.createdAt,
                    )
                    const tone = cycleComplete ? 'success' : remaining.tone
                    const statusLabel = cycleComplete
                      ? account.canTransfer
                        ? 'Cycle complete · ready to transfer'
                        : 'Cycle complete'
                      : remaining.statusLabel
                    const showTransfer = Boolean(account.canTransfer)
                    const busy = transferring === account.farmId || transferring === 'all'
                    return (
                      <tr key={account.id}>
                        <td>
                          <b>{account.farmName}</b>
                          {account.farmLocation ? (
                            <>
                              <br />
                              <small>{account.farmLocation}</small>
                            </>
                          ) : null}
                        </td>
                        <td>
                          <div className="cgf-cell-value">{account.currentGoats}</div>
                          <small>Active goats</small>
                        </td>
                        <td>
                          <div className="cgf-cell-value accent">{account.expectedKids}</div>
                          <small>Expected kids</small>
                        </td>
                        <td>
                          <b>{account.maturityDate || remaining.dateLabel || '—'}</b>
                          <br />
                          <small className={`cgf-tone-${tone}`}>
                            {statusLabel}
                            {account.maturityDate ? ` · ${progressPct}%` : ''}
                          </small>
                        </td>
                        <td>
                          {account.cycleStartAt ||
                            new Date(account.createdAt).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                        </td>
                        <td className="cgf-row-action">
                          {showTransfer ? (
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              onClick={() => handleTransferToMain(account.farmId)}
                              disabled={Boolean(transferring)}
                              title={`Transfer ${formatUGX(account.transferAmount)} to Main Account`}
                            >
                              <ArrowLeftRight size={14} />
                              {busy ? 'Transferring…' : 'Transfer to Main Account'}
                            </button>
                          ) : (
                            <span className="cgf-action-placeholder">—</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="cgf-card">
            <div className="cgf-card-head">
              <h3>
                <Info size={18} />
                Goat Breeding Information
              </h3>
            </div>
            <div className="cgf-info-grid">
              <div>
                <p>
                  <strong>Breeding Cycle:</strong> {CGF_BREEDING_INFO.cycle}
                </p>
                <p>
                  <strong>Kids per Birth:</strong> {CGF_BREEDING_INFO.kidsPerBirth}
                </p>
                <p>
                  <strong>Gestation Period:</strong> {CGF_BREEDING_INFO.gestation}
                </p>
              </div>
              <div>
                <p>
                  <strong>Maturity Age:</strong> {CGF_BREEDING_INFO.maturityAge}
                </p>
                <p>
                  <strong>Expected ROI:</strong> {CGF_BREEDING_INFO.expectedRoi}
                </p>
                <p>
                  <strong>Next Generation:</strong> {CGF_BREEDING_INFO.nextGeneration}
                </p>
              </div>
            </div>
          </section>
        </>
      ) : (
        <section className="cgf-card">
          <div className="cgf-empty">
            <Sprout size={40} />
            <h4>No goats allocated yet</h4>
            <p>
              Your goats will appear here once you complete package purchases and they are
              allocated to farms.
            </p>
          </div>
        </section>
      )}

      <section className="cgf-card">
        <div className="cgf-card-head">
          <h3>
            <ShoppingCart size={18} />
            Your Package Purchases
          </h3>
        </div>
        <div className="cgf-table-wrap">
          {purchases.length === 0 ? (
            <div className="cgf-empty">
              <Info size={36} />
              <h4>No package purchases found</h4>
              <p>Contact your administrator to purchase investment packages.</p>
            </div>
          ) : (
            <table className="cgf-table">
                <thead>
                  <tr>
                    <th>Farm</th>
                    <th>Package</th>
                    <th>Total Amount</th>
                    <th>Amount Paid</th>
                    <th>Balance</th>
                    <th>Status</th>
                    <th>Goats Allocated</th>
                    <th>Purchase Date</th>
                    <th>Matures On</th>
                  </tr>
                </thead>
                <tbody>
                  {purchases.map((purchase) => {
                    const matured = Boolean(purchase.isMatured)
                    const settled = purchase.status === 'settled'
                    return (
                      <tr key={purchase.id}>
                        <td>{purchase.farmName}</td>
                        <td>{purchase.packageName}</td>
                        <td>{formatUGX(purchase.totalAmount)}</td>
                        <td>{formatUGX(purchase.amountPaid)}</td>
                        <td>{formatUGX(purchase.balanceDue)}</td>
                        <td>
                          <Badge tone={purchaseStatusBadge(purchase.status)}>
                            {purchase.statusLabel}
                          </Badge>
                        </td>
                        <td>
                          {purchase.goatsAllocated}/{purchase.goatCount}
                        </td>
                        <td>{purchase.purchaseDate}</td>
                        <td>
                          {purchase.maturityDate || '—'}
                          {settled ? (
                            <>
                              <br />
                              <small className="cgf-tone-info">Settled</small>
                            </>
                          ) : matured ? (
                            <>
                              <br />
                              <small className="cgf-tone-success">Matured</small>
                            </>
                          ) : purchase.progressPct != null && purchase.maturityDate ? (
                            <>
                              <br />
                              <small className="cgf-tone-warning">
                                {purchase.progressPct}% ·{' '}
                                {purchase.daysUntilMaturity != null &&
                                purchase.daysUntilMaturity > 0
                                  ? `${purchase.daysUntilMaturity} days left`
                                  : 'in progress'}
                              </small>
                            </>
                          ) : null}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
            </table>
          )}
        </div>
      </section>

      {payments.length > 0 ? (
        <section className="cgf-card">
          <div className="cgf-card-head">
            <h3>
              <Receipt size={18} />
              Recent Payments (Receipts)
            </h3>
          </div>
          <div className="cgf-table-wrap">
            <table className="cgf-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Receipt #</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Package</th>
                  <th>Farm</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{payment.paymentDate}</td>
                    <td>{payment.receiptNumber}</td>
                    <td>{formatUGX(payment.amount)}</td>
                    <td>{payment.paymentMethod || '—'}</td>
                    <td>{payment.packageName}</td>
                    <td>{payment.farmName}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </CgfShell>
  )
}
