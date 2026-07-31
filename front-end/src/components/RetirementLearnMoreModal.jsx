import { createPortal } from 'react-dom'
import { Clock3, Shield, Users, X } from 'lucide-react'
import { useEffect } from 'react'
import { useMember } from '../context/MemberContext'

const RETIREMENT_DETAILS = {
  name: 'Retirement Savings Scheme',
  premium: 'UGX 50,000',
  premiumPeriod: 'Suggested contribution per month',
  summary:
    'A long-term cooperative plan that helps members steadily build a retirement fund, with disciplined monthly contributions and access designed for later life.',
  howItWorks: [
    'Monthly contributions into your retirement pot',
    'Cooperative-managed long-term savings',
    'Access from age 55+',
    'Track growth on your member dashboard',
    'Option to top up anytime',
  ],
  highlights: [
    { label: 'Indicative return', amount: '12% p.a.' },
    { label: 'Minimum entry', amount: 'UGX 50,000 / month' },
    { label: 'Access age', amount: '55+' },
  ],
}

export default function RetirementLearnMoreModal({ open, onClose }) {
  const { addToast } = useMember()

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

  return createPortal(
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal modal-wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="retirement-learn-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon equity">
            <Clock3 size={20} />
          </div>
          <div className="modal-head-text">
            <b id="retirement-learn-title">{RETIREMENT_DETAILS.name}</b>
            <span>
              {RETIREMENT_DETAILS.premiumPeriod} · {RETIREMENT_DETAILS.premium}
            </span>
          </div>
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body protection-modal-body">
          <p className="protection-modal-lead">{RETIREMENT_DETAILS.summary}</p>

          <div className="protection-modal-grid">
            <section>
              <h4>
                <Users size={14} />
                How it works
              </h4>
              <ul>
                {RETIREMENT_DETAILS.howItWorks.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>
                <Shield size={14} />
                Highlights
              </h4>
              <ul className="benefit-amounts">
                {RETIREMENT_DETAILS.highlights.map((item) => (
                  <li key={item.label}>
                    <span>{item.label}</span>
                    <b>{item.amount}</b>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>

        <div className="modal-foot">
          <button type="button" className="btn btn-outline" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => addToast('Retirement Savings Scheme is still under development')}
          >
            <Clock3 size={16} />
            Start saving
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
