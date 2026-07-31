import { useEffect, useMemo, useState } from 'react'
import {
  Calculator,
  FileText,
  History,
  PiggyBank,
  X,
} from 'lucide-react'
import CgfShell from '../../components/cgf/CgfShell'
import {
  KIDS_PER_GOAT_PER_YEAR,
  MARKET_PRICE_PER_KID,
  transactionFromPayment,
} from '../../data/cgfData'
import { useAuth } from '../../context/AuthContext'
import { useMember } from '../../context/MemberContext'
import { formatUGX } from '../../utils/format'

function Badge({ tone, children }) {
  return <span className={`cgf-badge cgf-badge-${tone}`}>{children}</span>
}

export default function CgfTransactions() {
  const { authFetch } = useAuth()
  const { addToast } = useMember()
  const [payments, setPayments] = useState([])
  const [totalInvestments, setTotalInvestments] = useState(0)
  const [totalPackageAmounts, setTotalPackageAmounts] = useState(0)
  const [totalPending, setTotalPending] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [goats, setGoats] = useState(2)
  const [years, setYears] = useState(1)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    authFetch('/api/projects/cgf/')
      .then((payload) => {
        if (!alive) return
        const member = payload.member || {}
        setPayments(payload.payments || [])
        setTotalInvestments(member.totalInvestments ?? 0)
        setTotalPackageAmounts(member.totalPackageAmounts ?? member.totalInvested ?? 0)
        setTotalPending(member.totalPendingAmount ?? member.totalBalance ?? 0)
      })
      .catch((err) => {
        if (!alive) return
        const message = err.message || 'Could not load CGF transactions.'
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

  const transactions = useMemo(
    () => payments.map(transactionFromPayment),
    [payments],
  )

  const nGoats = Math.max(0, Number(goats) || 0)
  const nYears = Math.max(0, Number(years) || 0)
  const totalKids = nGoats * KIDS_PER_GOAT_PER_YEAR * nYears
  const estimatedReturns = totalKids * MARKET_PRICE_PER_KID

  return (
    <CgfShell title="Transactions">
      <section className="cgf-hero">
        <div>
          <h2>Transactions</h2>
          <p>Track your investment payments and transaction history</p>
        </div>
      </section>

      {loading ? <p className="cgf-status-line">Loading your CGF transactions…</p> : null}
      {error && !loading ? <p className="cgf-status-line danger-text">{error}</p> : null}

      <section className="cgf-tx-summary">
        <div className="cgf-tx-left">
          <article className="cgf-card">
            <div className="cgf-card-head">
              <h3>
                <PiggyBank size={18} />
                Total Investments
              </h3>
            </div>
            <div className="cgf-summary-body">
              <div>
                <strong>{formatUGX(totalInvestments)}</strong>
                <small>
                  {transactions.length} investment{transactions.length === 1 ? '' : 's'} made
                </small>
              </div>
              <div className="cgf-stat-icon primary">
                <PiggyBank size={22} />
              </div>
            </div>
          </article>

          <article className="cgf-card">
            <div className="cgf-card-head">
              <h3>
                <FileText size={18} />
                Pending Payments
              </h3>
            </div>
            <div className="cgf-summary-body">
              <div>
                <strong className="cgf-warn-value">{formatUGX(totalPending)}</strong>
                <small>
                  Total: {formatUGX(totalPackageAmounts)}
                  <br />
                  Paid: {formatUGX(totalInvestments)}
                </small>
              </div>
              <div className="cgf-stat-icon warning">
                <FileText size={22} />
              </div>
            </div>
          </article>
        </div>

        <article className="cgf-card">
          <div className="cgf-card-head">
            <h3>
              <Calculator size={18} />
              Returns Calculator
            </h3>
          </div>
          <div className="cgf-summary-body cgf-calc-body">
            <div className="cgf-calc-top">
              <div>
                <strong className="cgf-ok-value">{formatUGX(estimatedReturns)}</strong>
                <small>Estimated returns</small>
              </div>
              <div className="cgf-stat-icon success">
                <Calculator size={22} />
              </div>
            </div>
            <div className="cgf-calc-inputs">
              <label>
                Number of Goats
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={goats}
                  onChange={(e) => setGoats(e.target.value)}
                />
              </label>
              <label>
                Years
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                />
              </label>
            </div>
            <div className="cgf-calc-details">
              Estimated kids: <b>{totalKids}</b>
              <br />
              Market value: <b>{formatUGX(estimatedReturns)}</b>
            </div>
          </div>
        </article>
      </section>

      <section className="cgf-card">
        <div className="cgf-card-head">
          <h3>
            <History size={18} />
            Transaction History
          </h3>
        </div>
        <div className="cgf-table-wrap">
          {!loading && transactions.length === 0 ? (
            <div className="cgf-empty">
              <History size={40} />
              <p>No transactions found matching your criteria.</p>
            </div>
          ) : (
            <table className="cgf-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Receipt No.</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="cgf-row-click" onClick={() => setSelected(tx)}>
                    <td>{tx.date}</td>
                    <td>{tx.receiptNo}</td>
                    <td>
                      <Badge tone={tx.typeTone}>{tx.type}</Badge>
                    </td>
                    <td>{tx.description}</td>
                    <td>{formatUGX(tx.amount)}</td>
                    <td>
                      <Badge tone={tx.statusTone}>{tx.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {selected ? (
        <div className="cgf-modal-backdrop" role="presentation" onClick={() => setSelected(null)}>
          <div
            className="cgf-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cgf-tx-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="cgf-modal-head">
              <h3 id="cgf-tx-title">Transaction Details</h3>
              <button
                type="button"
                className="nav-icon-btn"
                aria-label="Close"
                onClick={() => setSelected(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="cgf-modal-body">
              <dl className="cgf-detail-grid">
                <div>
                  <dt>Date</dt>
                  <dd>{selected.date}</dd>
                </div>
                <div>
                  <dt>Type</dt>
                  <dd>
                    <Badge tone={selected.typeTone}>{selected.type}</Badge>
                  </dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    <Badge tone={selected.statusTone}>{selected.status}</Badge>
                  </dd>
                </div>
                <div>
                  <dt>Amount</dt>
                  <dd>
                    <b>{formatUGX(selected.amount)}</b>
                  </dd>
                </div>
                <div className="full">
                  <dt>Description</dt>
                  <dd>{selected.description}</dd>
                </div>
                <div>
                  <dt>Payment method</dt>
                  <dd>{selected.paymentMethod || 'Not specified'}</dd>
                </div>
                <div>
                  <dt>Reference</dt>
                  <dd>{selected.reference}</dd>
                </div>
                <div>
                  <dt>Processed by</dt>
                  <dd>{selected.processedBy}</dd>
                </div>
                <div>
                  <dt>Processed date</dt>
                  <dd>{selected.processedDate}</dd>
                </div>
                <div className="full">
                  <dt>Notes</dt>
                  <dd>{selected.notes || 'No additional notes'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      ) : null}
    </CgfShell>
  )
}
