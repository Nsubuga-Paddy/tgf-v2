import { useEffect, useState } from 'react'
import {
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
  kiddingFromCreated,
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
}

function Badge({ tone, children }) {
  return <span className={`cgf-badge cgf-badge-${tone}`}>{children}</span>
}

export default function CgfDashboard() {
  const { authFetch } = useAuth()
  const { member, addToast } = useMember()
  const [summary, setSummary] = useState(EMPTY_SUMMARY)
  const [farmAccounts, setFarmAccounts] = useState([])
  const [purchases, setPurchases] = useState([])
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    authFetch('/api/projects/cgf/')
      .then((payload) => {
        if (!alive) return
        setSummary({ ...EMPTY_SUMMARY, ...(payload.member || {}) })
        setFarmAccounts(payload.farmAccounts || [])
        setPurchases(payload.purchases || [])
        setPayments((payload.payments || []).slice(0, 10))
      })
      .catch((err) => {
        if (!alive) return
        const message = err.message || 'Could not load CGF dashboard.'
        setError(message)
        addToast(message)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [authFetch, addToast])

  const accountNumber = summary.accountNumber || member.accountNumber || '—'

  return (
    <CgfShell title="Commercial Goat Farming">
      <section className="cgf-hero">
        <div>
          <h2>Welcome back, {member.firstName}!</h2>
          <p>Track your investment progress and manage your goat farm efficiently</p>
          <div className="cgf-account-row">
            <span>Account Number</span>
            <strong>{accountNumber}</strong>
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
                    <th>Next Kidding Date</th>
                    <th>Account Created</th>
                  </tr>
                </thead>
                <tbody>
                  {farmAccounts.map((account) => {
                    const kidding = kiddingFromCreated(account.createdAt)
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
                          <b>{kidding.dateLabel}</b>
                          <br />
                          <small className={`cgf-tone-${kidding.tone}`}>{kidding.statusLabel}</small>
                        </td>
                        <td>
                          {new Date(account.createdAt).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
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
                </tr>
              </thead>
              <tbody>
                {purchases.map((purchase) => (
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
                  </tr>
                ))}
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
