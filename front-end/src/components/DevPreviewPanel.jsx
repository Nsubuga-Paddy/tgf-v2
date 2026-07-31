import { useState } from 'react'
import { FlaskConical, X } from 'lucide-react'
import { useMember } from '../context/MemberContext'

export default function DevPreviewPanel() {
  const [open, setOpen] = useState(false)
  const {
    isShareholder,
    setShareholderPreview,
    bereavementSubscribed,
    setBereavementPreview,
    retirementSubscribed,
    setRetirementPreview,
    hasMaturedProjects,
    setMaturedProjectsPreview,
  } = useMember()

  return (
    <div className="dev-preview">
      {open ? (
        <div className="dev-panel wide">
          <div className="dev-panel-head">
            <h5>Preview states</h5>
            <button
              type="button"
              className="dev-close"
              aria-label="Close preview panel"
              onClick={() => setOpen(false)}
            >
              <X size={14} />
            </button>
          </div>

          <p className="dev-label">Shareholding</p>
          <div className="dev-row">
            <button
              type="button"
              className={`dev-opt ${isShareholder ? 'active' : ''}`}
              onClick={() => setShareholderPreview(true)}
            >
              Shareholder
            </button>
            <button
              type="button"
              className={`dev-opt ${!isShareholder ? 'active' : ''}`}
              onClick={() => setShareholderPreview(false)}
            >
              No shares
            </button>
          </div>

          <p className="dev-label">Bereavement Fund</p>
          <div className="dev-row">
            <button
              type="button"
              className={`dev-opt ${bereavementSubscribed ? 'active' : ''}`}
              onClick={() => setBereavementPreview(true)}
            >
              Subscribed
            </button>
            <button
              type="button"
              className={`dev-opt ${!bereavementSubscribed ? 'active' : ''}`}
              onClick={() => setBereavementPreview(false)}
            >
              Not subscribed
            </button>
          </div>

          <p className="dev-label">Retirement Scheme</p>
          <div className="dev-row">
            <button
              type="button"
              className={`dev-opt ${retirementSubscribed ? 'active' : ''}`}
              onClick={() => setRetirementPreview(true)}
            >
              Subscribed
            </button>
            <button
              type="button"
              className={`dev-opt ${!retirementSubscribed ? 'active' : ''}`}
              onClick={() => setRetirementPreview(false)}
            >
              Not subscribed
            </button>
          </div>

          <p className="dev-label">Matured Projects</p>
          <div className="dev-row">
            <button
              type="button"
              className={`dev-opt ${hasMaturedProjects ? 'active' : ''}`}
              onClick={() => setMaturedProjectsPreview(true)}
            >
              Has matured
            </button>
            <button
              type="button"
              className={`dev-opt ${!hasMaturedProjects ? 'active' : ''}`}
              onClick={() => setMaturedProjectsPreview(false)}
            >
              None matured
            </button>
          </div>

          <p className="dev-note">
            Dev only — switch member states while designing the dashboard.
          </p>
        </div>
      ) : null}

      <button
        type="button"
        className="dev-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <FlaskConical size={16} />
        Preview
      </button>
    </div>
  )
}
