import { createPortal } from 'react-dom'
import { Shield, Users, X } from 'lucide-react'
import { useEffect } from 'react'
import { useMember } from '../context/MemberContext'

const BEREAVEMENT_DETAILS = {
  name: 'MCS Bereavement Fund',
  premium: 'UGX 240,000',
  premiumPeriod: 'Annual premium',
  summary:
    'This benefit is designed to assist with the cost associated with funeral arrangements. The funeral benefit pays out a lump sum in the event of the death of an MCS member or an MCS member’s family.',
  insured: [
    'One MCS member',
    '1 spouse',
    '4 children',
    '2 parents',
    '2 parents-in-law',
  ],
  benefits: [
    { label: 'MCS member', amount: 'UGX 10,000,000' },
    { label: 'Spouse', amount: 'UGX 5,000,000' },
    { label: 'Other dependants', amount: 'UGX 1,000,000' },
  ],
}

export default function BereavementLearnMoreModal({ open, onClose }) {
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
        aria-labelledby="bereavement-learn-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon equity">
            <Shield size={20} />
          </div>
          <div className="modal-head-text">
            <b id="bereavement-learn-title">{BEREAVEMENT_DETAILS.name}</b>
            <span>
              {BEREAVEMENT_DETAILS.premiumPeriod} · {BEREAVEMENT_DETAILS.premium}
            </span>
          </div>
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body protection-modal-body">
          <p className="protection-modal-lead">{BEREAVEMENT_DETAILS.summary}</p>

          <div className="protection-modal-grid">
            <section>
              <h4>
                <Users size={14} />
                Persons insured
              </h4>
              <ul>
                {BEREAVEMENT_DETAILS.insured.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>
                <Shield size={14} />
                Benefits
              </h4>
              <ul className="benefit-amounts">
                {BEREAVEMENT_DETAILS.benefits.map((item) => (
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
            onClick={() => addToast('MCS Bereavement Fund is still under development')}
          >
            <Shield size={16} />
            Join cover
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
