import { useState } from 'react'
import AppShell from '../components/layout/AppShell'
import BereavementLearnMoreModal from '../components/BereavementLearnMoreModal'
import ProjectIcon from '../components/ProjectIcon'
import RetirementLearnMoreModal from '../components/RetirementLearnMoreModal'
import { useMember } from '../context/MemberContext'
import { Clock3, FileText, Info, Shield, Wallet } from 'lucide-react'
import { PROTECTION_BENEFITS } from '../data/protectionBenefits'

export default function ProtectionBenefits() {
  const [bereavementOpen, setBereavementOpen] = useState(false)
  const [retirementOpen, setRetirementOpen] = useState(false)
  const { bereavementSubscribed, retirementSubscribed, addToast } = useMember()

  const isSubscribed = (id) =>
    (id === 'bereavement' && bereavementSubscribed) ||
    (id === 'retirement' && retirementSubscribed)

  return (
    <AppShell title="Protection Benefits">
      <div className="protection-page">
        <header className="protection-intro">
          <p>
            These are cooperative protection products. They are not counted as investable
            portfolio capital — they provide cover and long-term security for members and
            families.
          </p>
        </header>

        <div className="protection-grid">
          {PROTECTION_BENEFITS.map((benefit) => {
            const isBereavement = benefit.id === 'bereavement'
            const subscribed = isSubscribed(benefit.id)

            return (
              <article
                key={benefit.id}
                className={`protection-card simple ${subscribed ? 'subscribed' : ''}`}
              >
                <div className="protection-card-head">
                  <div className="protection-card-icon">
                    <ProjectIcon name={benefit.icon} size={20} />
                  </div>
                  <div className="protection-card-titles">
                    <b>{benefit.name}</b>
                    <span>{benefit.tagline}</span>
                  </div>
                  <span className={`protection-status ${subscribed ? 'active' : 'open'}`}>
                    {subscribed ? 'Subscribed' : 'Open to join'}
                  </span>
                </div>

                <p className="protection-summary">
                  {subscribed ? benefit.enrolledSummary : benefit.summary}
                </p>

                {subscribed ? (
                  <div className="protection-enrolled-meta">
                    {benefit.enrolledMeta.map((row) => (
                      <div key={row.label} className="enrolled-meta-row">
                        <span>{row.label}</span>
                        <b>{row.value}</b>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="protection-premium">
                    <div>
                      <small>{benefit.premiumLabel}</small>
                      <strong>{benefit.premium}</strong>
                    </div>
                    <span>{benefit.premiumPeriod}</span>
                  </div>
                )}

                <div className="protection-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => addToast(`${benefit.name} is still under development`)}
                  >
                    {isBereavement ? <Shield size={15} /> : <Clock3 size={15} />}
                    Open project
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => {
                      if (isBereavement) setBereavementOpen(true)
                      else setRetirementOpen(true)
                    }}
                  >
                    {subscribed ? (
                      isBereavement ? (
                        <FileText size={15} />
                      ) : (
                        <Wallet size={15} />
                      )
                    ) : (
                      <Info size={15} />
                    )}
                    {subscribed ? benefit.enrolledSecondary : benefit.ctaSecondary}
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </div>

      <BereavementLearnMoreModal
        open={bereavementOpen}
        onClose={() => setBereavementOpen(false)}
      />
      <RetirementLearnMoreModal
        open={retirementOpen}
        onClose={() => setRetirementOpen(false)}
      />
    </AppShell>
  )
}
