import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { ArrowUpFromLine, Building2, Smartphone, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

export default function RequestWithdrawModal({ open, onClose }) {
  const { authFetch } = useAuth()
  const { mainAccount, profile, reloadDashboard, addToast } = useMember()
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [method, setMethod] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const mobileNumber = String(profile?.whatsapp || '').trim()
  const bankName = String(profile?.bankName || '').trim()
  const bankAccountNumber = String(profile?.bankAccountNumber || '').trim()
  const bankAccountName = String(profile?.bankAccountName || '').trim()
  const bankReady = Boolean(bankName && bankAccountNumber && bankAccountName)
  const mobileReady = Boolean(mobileNumber)
  const available = Number(mainAccount?.available || 0)

  const options = useMemo(
    () => [
      {
        id: 'mobile_money',
        title: 'Send to my mobile money number',
        detail: mobileReady ? mobileNumber : 'No mobile money number on your profile',
        ready: mobileReady,
        Icon: Smartphone,
      },
      {
        id: 'bank',
        title: 'Send to my bank account',
        detail: bankReady
          ? `${bankName} · ${bankAccountNumber} · ${bankAccountName}`
          : 'Bank account details incomplete on your profile',
        ready: bankReady,
        Icon: Building2,
      },
    ],
    [bankAccountName, bankAccountNumber, bankName, bankReady, mobileNumber, mobileReady],
  )

  useEffect(() => {
    if (!open) return
    setAmount('')
    setReason('')
    setError('')
    setSubmitting(false)
    setMethod(mobileReady ? 'mobile_money' : bankReady ? 'bank' : '')
  }, [open, mobileReady, bankReady])

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

  if (!open) return null

  const parsedAmount = Number(String(amount).replace(/,/g, '').trim())
  const amountValid = Number.isFinite(parsedAmount) && parsedAmount > 0
  const canSubmit =
    amountValid &&
    parsedAmount <= available &&
    Boolean(method) &&
    options.some((opt) => opt.id === method && opt.ready) &&
    !submitting

  const submit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    setError('')
    try {
      await authFetch('/api/main-account/withdraw/', {
        method: 'POST',
        body: {
          amount: parsedAmount,
          payoutMethod: method,
          reason: reason.trim(),
        },
      })
      await reloadDashboard()
      addToast('Withdrawal request submitted for review')
      onClose()
    } catch (err) {
      setError(err.message || 'Could not submit withdrawal request.')
    } finally {
      setSubmitting(false)
    }
  }

  return createPortal(
    <div className="modal-overlay" onClick={submitting ? undefined : onClose} role="presentation">
      <div
        className="modal modal-wide withdraw-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="withdraw-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon">
            <ArrowUpFromLine size={20} />
          </div>
          <div className="modal-head-text">
            <b id="withdraw-title">Request withdraw</b>
            <span>Available {formatUGX(available)} · choose where to send funds</span>
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
          <div className="modal-body profile-form-body">
            <label className="profile-field full">
              <span>
                Amount (UGX) <em>*</em>
              </span>
              <input
                required
                inputMode="decimal"
                placeholder="e.g. 100000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={submitting}
              />
            </label>

            <div className="withdraw-dest-label">Send money to</div>
            <div className="withdraw-dest-list" role="radiogroup" aria-label="Payout destination">
              {options.map((opt) => {
                const selected = method === opt.id
                return (
                  <label
                    key={opt.id}
                    className={`withdraw-dest-option ${selected ? 'selected' : ''} ${
                      opt.ready ? '' : 'disabled'
                    }`}
                  >
                    <input
                      type="radio"
                      name="payoutMethod"
                      value={opt.id}
                      checked={selected}
                      disabled={!opt.ready || submitting}
                      onChange={() => setMethod(opt.id)}
                    />
                    <span className="withdraw-dest-icon">
                      <opt.Icon size={18} />
                    </span>
                    <span className="withdraw-dest-copy">
                      <b>{opt.title}</b>
                      <span>{opt.detail}</span>
                      {!opt.ready ? (
                        <Link to="/profile" className="withdraw-dest-link" onClick={onClose}>
                          Update on profile
                        </Link>
                      ) : null}
                    </span>
                  </label>
                )
              })}
            </div>

            <label className="profile-field full">
              <span>Reason (optional)</span>
              <textarea
                rows={2}
                placeholder="Optional note for the review team"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={submitting}
              />
            </label>

            {!mobileReady && !bankReady ? (
              <p className="withdraw-hint warn">
                Add a mobile money number or bank account on your{' '}
                <Link to="/profile" onClick={onClose}>
                  profile
                </Link>{' '}
                before requesting a withdrawal.
              </p>
            ) : (
              <p className="withdraw-hint">
                Funds stay reserved while your request is pending admin review.
              </p>
            )}

            {error ? <p className="withdraw-error">{error}</p> : null}
          </div>

          <div className="modal-foot">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
              {submitting ? 'Submitting…' : 'Submit request'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}
