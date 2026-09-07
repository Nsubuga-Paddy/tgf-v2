import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { ArrowUpFromLine, Wallet, X } from 'lucide-react'
import { formatUGX } from '../../utils/format'

export default function RepayFromMainModal({ open, onClose, loan, available, onSubmit }) {
  const [amount, setAmount] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !loan) return
    setAmount(String(loan.nextDueAmount || loan.installmentAmount || ''))
    setError('')
    setSubmitting(false)
  }, [open, loan])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape' && !submitting) onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose, submitting])

  if (!open || !loan) return null

  const parsed = Number(String(amount).replace(/,/g, '').trim())
  const outstanding = Number(loan.outstanding || 0)
  const mainAvail = Number(available || 0)
  const cap = Math.min(outstanding, mainAvail)
  const nextDue = Math.round(loan.nextDueAmount || loan.installmentAmount || 0)
  const valid = Number.isFinite(parsed) && parsed > 0 && parsed <= cap

  const setFull = () => setAmount(String(Math.round(outstanding)))
  const setDue = () => setAmount(String(nextDue))

  const submit = async (e) => {
    e.preventDefault()
    if (!valid || submitting) return
    setSubmitting(true)
    setError('')
    try {
      await onSubmit(parsed)
      onClose()
    } catch (err) {
      setError(err.message || 'Could not submit repayment.')
    } finally {
      setSubmitting(false)
    }
  }

  return createPortal(
    <div className="modal-overlay" onClick={submitting ? undefined : onClose} role="presentation">
      <div
        className="modal modal-wide repay-loan-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="repay-loan-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon">
            <ArrowUpFromLine size={20} />
          </div>
          <div className="modal-head-text">
            <b id="repay-loan-title">Repay from Main Account</b>
            <span>
              {loan.reference} · {loan.purposeLabel || loan.purpose}
            </span>
          </div>
          <button
            type="button"
            className="modal-close"
            aria-label="Close"
            onClick={onClose}
            disabled={submitting}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body profile-form-body loans-repay-modal-body">
            <div className="loans-repay-summary">
              <div className="loans-repay-summary-item">
                <small>Outstanding balance</small>
                <strong>{formatUGX(outstanding)}</strong>
              </div>
              <div className="loans-repay-summary-item highlight">
                <small>
                  <Wallet size={12} />
                  Main Account available
                </small>
                <strong>{formatUGX(mainAvail)}</strong>
              </div>
              {nextDue > 0 ? (
                <div className="loans-repay-summary-item">
                  <small>Next installment</small>
                  <strong>{formatUGX(nextDue)}</strong>
                </div>
              ) : null}
            </div>

            <section className="loans-repay-amount-block" aria-labelledby="repay-amount-label">
              <label className="loans-repay-amount-field" htmlFor="repay-amount-input">
                <span id="repay-amount-label">
                  Repayment amount <em>*</em>
                </span>
                <div className="loans-repay-amount-input-wrap">
                  <span className="loans-repay-amount-prefix">UGX</span>
                  <input
                    id="repay-amount-input"
                    type="text"
                    inputMode="numeric"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0"
                    disabled={submitting}
                    autoComplete="off"
                  />
                </div>
                <span className="loans-repay-amount-hint">
                  {cap > 0
                    ? `You can repay up to ${formatUGX(cap)} from your Main Account.`
                    : 'Insufficient Main Account balance to repay this loan.'}
                </span>
              </label>
            </section>

            <section className="loans-repay-quick-section" aria-label="Quick amount selection">
              <span className="loans-repay-quick-label">Quick select</span>
              <div className="loans-repay-quick">
                {nextDue > 0 ? (
                  <button
                    type="button"
                    className={`loans-repay-quick-btn ${parsed === nextDue ? 'active' : ''}`}
                    onClick={setDue}
                    disabled={submitting}
                  >
                    Next installment
                    <small>{formatUGX(nextDue)}</small>
                  </button>
                ) : null}
                <button
                  type="button"
                  className={`loans-repay-quick-btn ${parsed === Math.round(outstanding) ? 'active' : ''}`}
                  onClick={setFull}
                  disabled={submitting}
                >
                  Full outstanding
                  <small>{formatUGX(outstanding)}</small>
                </button>
              </div>
            </section>

            {error ? <p className="loans-repay-error">{error}</p> : null}

            <p className="loans-repay-note">
              This transfers immediately from your Main Account to your loan repayment.
            </p>
          </div>

          <div className="modal-foot">
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={!valid || submitting}>
              <ArrowUpFromLine size={15} />
              {submitting ? 'Transferring…' : 'Repay now'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}
