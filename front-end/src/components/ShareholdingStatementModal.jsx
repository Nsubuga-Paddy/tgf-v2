import { createPortal } from 'react-dom'
import { Download, FileText, X } from 'lucide-react'
import { useEffect } from 'react'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

export default function ShareholdingStatementModal({ open, onClose }) {
  const { shareholding, addToast } = useMember()

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

  const sharesLabel = shareholding.sharesHeldDisplay || String(shareholding.sharesHeld || 0)
  const eligibleLabel =
    shareholding.dividendEligibleDisplay || String(shareholding.dividendEligible || 0)
  const certificateLabel = shareholding.certificateStatus || 'Not issued'

  return createPortal(
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal modal-wide equity-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-statement-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon equity">
            <FileText size={20} />
          </div>
          <div className="modal-head-text">
            <b id="share-statement-title">Shareholding Statement</b>
            <span>
              Shares, dividends & payouts · Certificate: {certificateLabel}
            </span>
          </div>
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div className="statement-summary">
            <div className="mrow">
              <span className="k">Tier</span>
              <span className="v">
                {shareholding.tierEmoji ? `${shareholding.tierEmoji} ` : ''}
                {shareholding.tier || '—'}
              </span>
            </div>
            <div className="mrow">
              <span className="k">Shares held</span>
              <span className="v">{sharesLabel} shares</span>
            </div>
            <div className="mrow">
              <span className="k">Portfolio value</span>
              <span className="v">{formatUGX(shareholding.portfolioValue)}</span>
            </div>
            <div className="mrow">
              <span className="k">Dividend eligible</span>
              <span className="v">
                {eligibleLabel} shares · {formatUGX(shareholding.dividendEligibleValue)}
              </span>
            </div>
            <div className="mrow">
              <span className="k">Expected dividend</span>
              <span className="v pos">{formatUGX(shareholding.expectedDividend)}</span>
            </div>
            {shareholding.dividendRate ? (
              <div className="mrow">
                <span className="k">Dividend rate</span>
                <span className="v">{shareholding.dividendRate}</span>
              </div>
            ) : null}
            {shareholding.yearJoined || shareholding.memberSince ? (
              <div className="mrow">
                <span className="k">Year joined</span>
                <span className="v">{shareholding.yearJoined || shareholding.memberSince}</span>
              </div>
            ) : null}
          </div>
        </div>

        <div className="modal-foot">
          <button type="button" className="btn btn-outline" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="btn btn-equity-solid"
            onClick={() => addToast('Shareholding PDF download is still under development')}
          >
            <Download size={16} />
            Download PDF
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
