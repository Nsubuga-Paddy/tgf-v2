import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronDown,
  ChevronRight,
  CircleHelp,
  DoorOpen,
  Inbox,
  Landmark,
  ListChecks,
  Pencil,
  PlayCircle,
  Send,
  University,
  User,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { EditBankModal, EditPersonalModal } from '../components/ProfileEditModals'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

const EMPTY_PROFILE = {
  firstName: '',
  lastName: '',
  fullName: '',
  username: '',
  email: '',
  accountNumber: '',
  memberSince: '',
  whatsapp: '',
  nationalId: '',
  address: '',
  birthdate: '',
  bio: '',
  isVerified: false,
  bankName: '',
  bankAccountNumber: '',
  bankAccountName: '',
}

function Accordion({ id, title, icon: Icon, openId, setOpenId, children }) {
  const open = openId === id
  return (
    <div className={`profile-accordion ${open ? 'open' : ''}`}>
      <button
        type="button"
        className="profile-accordion-head"
        aria-expanded={open}
        onClick={() => setOpenId(open ? null : id)}
      >
        <span>
          <Icon size={16} />
          {title}
        </span>
        <ChevronDown size={16} className="profile-chevron" />
      </button>
      {open ? <div className="profile-accordion-body">{children}</div> : null}
    </div>
  )
}

function InfoRow({ label, value, tip }) {
  return (
    <div className="profile-info-row">
      <span className="profile-info-label">
        {label}
        {tip ? (
          <button type="button" className="profile-tip-btn" title={tip} aria-label={tip}>
            <CircleHelp size={13} />
          </button>
        ) : null}
      </span>
      <span className="profile-info-value">{value || '—'}</span>
    </div>
  )
}

export default function Profile() {
  const { authFetch } = useAuth()
  const {
    isShareholder: memberIsShareholder,
    shareholding: memberShareholding,
    profile: memberProfile,
    reloadDashboard,
  } = useMember()
  const [openId, setOpenId] = useState('personal')
  const [profile, setProfile] = useState(memberProfile || EMPTY_PROFILE)
  const [grantedProjects, setGrantedProjects] = useState([])
  const [requestableProjects, setRequestableProjects] = useState([])
  const [accessRequests, setAccessRequests] = useState([])
  const [actionRequests, setActionRequests] = useState([])
  const [profileShareholding, setProfileShareholding] = useState(memberShareholding)
  const [selectedProjects, setSelectedProjects] = useState([])
  const [accessNote, setAccessNote] = useState('')
  const [editPersonalOpen, setEditPersonalOpen] = useState(false)
  const [editBankOpen, setEditBankOpen] = useState(false)
  const [localToast, setLocalToast] = useState(null)

  useEffect(() => {
    if (memberProfile) setProfile(memberProfile)
  }, [memberProfile])

  useEffect(() => {
    if (memberShareholding) setProfileShareholding(memberShareholding)
  }, [memberShareholding])

  useEffect(() => {
    let alive = true
    authFetch('/api/profile/')
      .then((data) => {
        if (!alive) return
        setProfile(data.profile || EMPTY_PROFILE)
        setGrantedProjects(data.grantedProjects || [])
        setRequestableProjects(data.requestableProjects || [])
        setAccessRequests(data.projectAccessRequests || [])
        setActionRequests(data.actionRequests || [])
        if (data.shareholding) setProfileShareholding(data.shareholding)
      })
      .catch((error) => flash(error.message || 'Could not load profile data.'))
    return () => {
      alive = false
    }
  }, [authFetch])

  const flash = (msg) => {
    setLocalToast(msg)
    window.setTimeout(() => setLocalToast(null), 2600)
  }

  const isShareholder =
    Boolean(profileShareholding?.isShareholder) || Boolean(memberIsShareholder)

  const shareholdingRows = useMemo(() => {
    const sh = profileShareholding || {}
    if (!isShareholder) {
      const message =
        sh.displayState === 'pending_setup'
          ? 'You have Cooperative Shareholding access, but your shareholding record has not been set up yet. Please contact the office.'
          : 'You have no cooperative shares on record. If you are a shareholder, contact the office to request access and registration.'
      return { state: 'none', message }
    }

    const sharesLabel = sh.sharesHeldDisplay || String(sh.sharesHeld || 0)
    const eligibleLabel = sh.dividendEligibleDisplay || String(sh.dividendEligible || 0)
    const tierLabel = `${sh.tierEmoji ? `${sh.tierEmoji} ` : ''}${sh.tier || 'Shareholder'}`
    const rows = [
      { label: 'Tier', value: tierLabel },
      {
        label: 'Shares held',
        value: sharesLabel,
        tip: 'Cooperative share categories',
      },
      { label: 'Portfolio value', value: formatUGX(sh.portfolioValue || 0) },
      {
        label: 'Eligible for this dividend',
        value: `${eligibleLabel} shares · ${formatUGX(sh.dividendEligibleValue || 0)}`,
      },
    ]
    if (sh.newEraShares > 0) {
      rows.push({
        label: `New shares (UGX ${(sh.newSharePurchasePrice || 0).toLocaleString()} lots)`,
        value: `${sh.newEraSharesDisplay || sh.newEraShares} · ${formatUGX(sh.newEraValue || 0)}`,
      })
    }
    if (sh.dividendRate) {
      rows.push({ label: 'Dividend rate', value: sh.dividendRate })
    }
    rows.push({
      label: "This cycle's dividend",
      value: formatUGX(sh.expectedDividend || 0),
      tip: 'How dividends work',
    })
    if (sh.yearJoined || sh.memberSince) {
      rows.push({ label: 'Year joined', value: String(sh.yearJoined || sh.memberSince) })
    }
    if (sh.certificateStatus) {
      rows.push({ label: 'Certificate', value: sh.certificateStatus })
    }
    return { state: 'full', rows }
  }, [isShareholder, profileShareholding])

  const toggleProject = (id) => {
    setSelectedProjects((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  const submitAccessRequest = (e) => {
    e.preventDefault()
    if (selectedProjects.length === 0) {
      flash('Select at least one project')
      return
    }
    flash('Project access requests are still under development')
  }

  return (
    <AppShell title="My Profile">
      <div className="profile-page">
        <div className="profile-layout">
          <div className="profile-main">
            <Link className="help-quick-card" to="/help">
              <div className="help-quick-icon">
                <PlayCircle size={20} />
              </div>
              <div className="help-quick-text">
                <strong>Help Center</strong>
                <span>Video tutorials for every MCS project</span>
              </div>
              <ChevronRight size={16} className="help-quick-chevron" />
            </Link>

            <section className="profile-info-card">
              <h2 className="profile-info-title">Profile Information</h2>

              <Accordion
                id="personal"
                title="Personal Information"
                icon={User}
                openId={openId}
                setOpenId={setOpenId}
              >
                <InfoRow label="Name" value={profile.fullName} />
                <InfoRow label="Username" value={`@${profile.username}`} />
                <InfoRow label="Email" value={profile.email} />
                <InfoRow label="Account Number" value={profile.accountNumber} />
                <InfoRow label="Member Since" value={profile.memberSince} />
                <InfoRow label="WhatsApp" value={profile.whatsapp} />
                <InfoRow label="National ID" value={profile.nationalId} />
                <InfoRow label="Address" value={profile.address} />
                <InfoRow label="Birthdate" value={profile.birthdate} />
                <div className="profile-section-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => setEditPersonalOpen(true)}
                  >
                    <Pencil size={14} />
                    Edit
                  </button>
                </div>
              </Accordion>

              {profile.isVerified ? (
                <Accordion
                  id="access"
                  title="Project Access"
                  icon={DoorOpen}
                  openId={openId}
                  setOpenId={setOpenId}
                >
                  <div className="profile-info-row stacked">
                    <span className="profile-info-label">Your approved groups</span>
                    <div className="granted-project-tags">
                      {grantedProjects.map((name) => (
                        <span key={name} className="granted-project-tag">
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>

                  <p className="project-access-note">
                    Request access to another MCS group you belong to or want to join. Each request
                    is reviewed by an administrator.
                  </p>

                  <form className="project-access-form" onSubmit={submitAccessRequest}>
                    <div className="project-checklist">
                      {requestableProjects.map((project) => (
                        <label key={project.id} className="project-check">
                          <input
                            type="checkbox"
                            checked={selectedProjects.includes(project.id)}
                            onChange={() => toggleProject(project.id)}
                          />
                          <span>{project.name}</span>
                        </label>
                      ))}
                    </div>
                    <textarea
                      className="project-access-textarea"
                      placeholder="Optional note for the administrator"
                      value={accessNote}
                      onChange={(e) => setAccessNote(e.target.value)}
                      rows={3}
                    />
                    <div className="profile-section-actions">
                      <button type="submit" className="btn btn-primary btn-sm">
                        <Send size={14} />
                        Request access
                      </button>
                    </div>
                  </form>

                  {accessRequests.length > 0 ? (
                    <div className="access-requests-block">
                      <span className="profile-info-label block">Your requests</span>
                      {accessRequests.map((req) => (
                        <div key={req.id} className="access-request-row">
                          <div className="access-request-top">
                            <strong>{req.project}</strong>
                            <span className={`access-status ${req.status}`}>{req.statusDisplay}</span>
                          </div>
                          <div className="access-request-date">{req.createdAt}</div>
                          {req.status === 'rejected' && req.adminNotes ? (
                            <div className="access-reject-reason">
                              <strong>Reason:</strong> {req.adminNotes}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </Accordion>
              ) : null}

              <Accordion
                id="shares"
                title="Cooperative Shareholding"
                icon={Landmark}
                openId={openId}
                setOpenId={setOpenId}
              >
                {shareholdingRows.state === 'full' ? (
                  shareholdingRows.rows.map((row) => (
                    <InfoRow key={row.label} label={row.label} value={row.value} tip={row.tip} />
                  ))
                ) : (
                  <p className="project-access-note">{shareholdingRows.message}</p>
                )}
              </Accordion>

              <Accordion
                id="bank"
                title="Bank Account Details"
                icon={University}
                openId={openId}
                setOpenId={setOpenId}
              >
                <InfoRow label="Bank Name" value={profile.bankName} />
                <InfoRow label="Account Number" value={profile.bankAccountNumber} />
                <InfoRow label="Account Name" value={profile.bankAccountName} />
                <div className="profile-section-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => setEditBankOpen(true)}
                  >
                    <Pencil size={14} />
                    Edit
                  </button>
                </div>
              </Accordion>
            </section>
          </div>

          <aside className="action-requests-panel">
            <h2 className="panel-title">
              <ListChecks size={18} />
              Action Requests
            </h2>
            <div className="action-requests-list">
              {actionRequests.length === 0 ? (
                <div className="action-requests-empty">
                  <Inbox size={28} />
                  No action requests yet
                  <div>Requests from 52WSC, CGF, and Real Estate will appear here</div>
                </div>
              ) : (
                actionRequests.map((req) => (
                  <article key={req.id} className={`action-request-card tone-${req.tone}`}>
                    <div className="action-request-header">
                      <span className="action-request-type">{req.typeLabel}</span>
                      <span className={`action-request-project ${req.tone || 'coop'}`}>
                        {req.project}
                      </span>
                    </div>
                    <div className="action-request-detail">{req.detail}</div>
                    <div className="action-request-footer">
                      <span className="action-request-date">{req.createdAt}</span>
                      <span className={`action-request-status ${req.status}`}>
                        {req.statusDisplay}
                      </span>
                    </div>
                  </article>
                ))
              )}
            </div>
          </aside>
        </div>
      </div>

      <EditPersonalModal
        open={editPersonalOpen}
        onClose={() => setEditPersonalOpen(false)}
        profile={profile}
        onSave={async (next) => {
          const data = await authFetch('/api/profile/', { method: 'PATCH', body: next })
          setProfile(data.profile)
          await reloadDashboard()
          flash('Personal information updated')
        }}
      />
      <EditBankModal
        open={editBankOpen}
        onClose={() => setEditBankOpen(false)}
        profile={profile}
        onSave={async (next) => {
          const data = await authFetch('/api/profile/', { method: 'PATCH', body: next })
          setProfile(data.profile)
          await reloadDashboard()
          flash('Bank details updated')
        }}
      />

      {localToast ? <div className="toast">{localToast}</div> : null}
    </AppShell>
  )
}
