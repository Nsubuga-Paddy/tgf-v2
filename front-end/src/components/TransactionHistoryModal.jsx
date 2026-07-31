import { createPortal } from 'react-dom'
import { ArrowDownLeft, ArrowUpRight, Banknote, Download, History, X } from 'lucide-react'
import { useEffect } from 'react'
import { useMember } from '../context/MemberContext'
import { formatSignedUGX, formatTxDate, formatUGX } from '../utils/format'
import { downloadTransactionsCsv } from '../utils/downloadTransactions'

const ICONS = {
  in: ArrowDownLeft,
  out: ArrowUpRight,
  invest: Banknote,
}

export default function TransactionHistoryModal({ open, onClose }) {
  const { member, transactions, mainAccount } = useMember()

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null

  const handleDownload = () => {
    downloadTransactionsCsv(transactions, member)
  }

  return createPortal(
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal modal-wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tx-history-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon">
            <History size={20} />
          </div>
          <div className="modal-head-text">
            <b id="tx-history-title">Main account transactions</b>
            <span>
              {member.accountNumber} · {transactions.length} records · balance{' '}
              {formatUGX(mainAccount.available)}
            </span>
          </div>
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {transactions.length === 0 ? (
            <p className="modal-empty">No transactions yet.</p>
          ) : (
            <ul className="tx-list modal-tx-list">
              {transactions.map((tx) => {
                const Icon = ICONS[tx.category] ?? ArrowUpRight
                const positive = Number(tx.amount) >= 0
                const title = tx.title || tx.label || 'Transaction'
                const when = tx.at ? formatTxDate(tx.at) : ''
                return (
                  <li key={tx.id} className="tx-row">
                    <div className={`tx-icon ${tx.category || 'in'}`}>
                      <Icon size={15} />
                    </div>
                    <div className="tx-body">
                      <b>{title}</b>
                      <span>
                        {[tx.meta, when, tx.ref].filter(Boolean).join(' · ')}
                      </span>
                    </div>
                    <div className={`tx-amount ${positive ? 'pos' : 'neg'}`}>
                      {formatSignedUGX(tx.amount)}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="modal-foot">
          <button type="button" className="btn btn-outline" onClick={onClose}>
            Close
          </button>
          <button type="button" className="btn btn-primary" onClick={handleDownload}>
            <Download size={16} />
            Download CSV
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
