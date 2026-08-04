import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Archive,
  ArrowRight,
  Building2,
  CalendarCheck,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Info,
  Lock,
  MapPin,
  PlayCircle,
  Receipt,
  RotateCcw,
  UserCheck,
  UserPlus,
  Users,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

function StatusBadge({ status }) {
  const labels = { running: 'Running', closed: 'Closed', upcoming: 'Upcoming' }
  const Icon = status === 'running' ? PlayCircle : status === 'closed' ? CheckCircle2 : Clock3
  return (
    <span className={`rep-status rep-status-${status}`}>
      <Icon size={12} />
      {labels[status]}
    </span>
  )
}

function ProjectCard({ project, onMembership, onInterest, onOpen }) {
  return (
    <article className="rep-project-card">
      <div className="rep-project-top">
        <div>
          <h3>{project.name}</h3>
          <p className="rep-location">
            <MapPin size={13} />
            {project.location}
          </p>
        </div>
        <StatusBadge status={project.status} />
      </div>

      <div className="rep-date-row">
        <span>
          <CalendarDays size={12} />
          {project.status === 'upcoming' ? 'Planned start' : 'Started'}: {project.startDate}
        </span>
        <span>
          <CalendarCheck size={12} />
          {project.status === 'closed' ? 'Closed' : 'Ends'}: {project.endDate}
        </span>
      </div>

      {project.userHasAccess || project.status === 'upcoming' ? (
        project.description ? <p className="rep-description">{project.description}</p> : null
      ) : (
        <p className="rep-restricted">
          <Lock size={13} />
          You do not have access to full details. Request to join for cooperative review.
        </p>
      )}

      {project.userHasAccess && project.status !== 'upcoming' ? (
        <p className="rep-project-meta">
          <Users size={13} />
          {project.membersCount} members
          {project.status === 'running' && project.minimumInvestment
            ? ` · ${project.minimumInvestment}`
            : ' participated'}
        </p>
      ) : null}

      <div className="rep-project-actions">
        {project.status === 'running' ? (
          project.membershipState === 'joined' ? (
            <button type="button" className="btn btn-outline" disabled>
              <UserCheck size={15} />
              You are in this project
            </button>
          ) : project.membershipState === 'pending' ? (
            <button type="button" className="btn btn-outline" disabled>
              <Clock3 size={15} />
              Join request pending
            </button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => onMembership(project)}>
              <UserPlus size={15} />
              Request to join
            </button>
          )
        ) : null}

        {project.status === 'upcoming' ? (
          project.membershipState === 'interested' ? (
            <button type="button" className="btn btn-outline" disabled>
              <CheckCircle2 size={15} />
              Interest submitted
            </button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => onInterest(project)}>
              Submit interest
            </button>
          )
        ) : null}

        {project.status !== 'upcoming' ? (
          <button type="button" className="btn btn-outline" onClick={() => onOpen(project)}>
            View project
            <ArrowRight size={15} />
          </button>
        ) : (
          <span className="rep-interest-note">
            <Info size={13} />
            You will be contacted when allocations open.
          </span>
        )}
      </div>
    </article>
  )
}

function PortfolioStat({ label, value, meta }) {
  return (
    <article className="rep-portfolio-stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {meta ? <p>{meta}</p> : null}
    </article>
  )
}

function ProjectSelector({ projects, selectedId, onSelect }) {
  if (!projects.length) return null
  return (
    <div className="rep-project-selector">
      <div className="rep-selector-scroll" role="tablist" aria-label="Your real estate projects">
        {projects.map((project) => (
          <button
            key={project.id}
            type="button"
            role="tab"
            aria-selected={String(project.id) === String(selectedId)}
            className={`rep-selector-chip ${
              String(project.id) === String(selectedId) ? 'active' : ''
            }`}
            onClick={() => onSelect(project.id)}
          >
            <b>{project.name}</b>
            <span>{project.location || project.status}</span>
          </button>
        ))}
      </div>
      <label className="rep-selector-mobile">
        <span>Select real estate project</span>
        <select value={selectedId || ''} onChange={(e) => onSelect(e.target.value)}>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}

function SelectedProjectPanel({
  project,
  detailProject,
  userStats,
  transactions,
  detailLoading,
  detailError,
  refundSubmitting,
  onOpen,
  onRefund,
}) {
  if (!project) {
    return (
      <div className="rep-portfolio-empty">
        <Building2 size={24} />
        <h3>No real estate project selected</h3>
        <p>Select a project above to see your position and project details.</p>
      </div>
    )
  }

  const current = detailProject || project
  const latestTransactions = transactions.slice(0, 3)
  const refundable = Number(userStats.refundableAmount || 0)
  const totalBudget =
    current.totalBudget ??
    ((current.vendorTotalAmount || 0) + (current.operationalCosts || 0) || 0)

  return (
    <section className="rep-selected-panel">
      <div className="rep-selected-hero">
        <div>
          <span className="rep-selected-kicker">Selected project</span>
          <h3>{current.name}</h3>
          <p className="rep-location">
            <MapPin size={13} />
            {current.location || 'Location not set'}
          </p>
          {current.description ? <p className="rep-selected-desc">{current.description}</p> : null}
        </div>
        <div className="rep-selected-meta">
          <StatusBadge status={current.status} />
          <span>
            <CalendarDays size={13} />
            {current.startDate || 'Start not set'}
          </span>
          <span>
            <CalendarCheck size={13} />
            {current.endDate || 'End not set'}
          </span>
        </div>
      </div>

      {detailLoading ? <p className="rep-status-line compact">Loading selected project…</p> : null}
      {detailError && !detailLoading ? (
        <p className="rep-status-line compact danger-text">{detailError}</p>
      ) : null}

      <div className="rep-portfolio-stats">
        <PortfolioStat
          label="Your total paid"
          value={formatUGX(userStats.totalPaid || 0)}
          meta="Payments and approved adjustments recorded for you."
        />
        <PortfolioStat
          label="Balance remaining"
          value={userStats.pendingBalance == null ? '—' : formatUGX(userStats.pendingBalance)}
          meta="Amount still unpaid before land title processing can start."
        />
        <PortfolioStat
          label="Payment status"
          value={userStats.projectStatusLabel || (userStats.paymentCompleted ? 'Completed' : 'In progress')}
          meta={
            userStats.paymentCompleted
              ? 'You are fully paid. Title processing can be handled by the cooperative.'
              : 'You can continue payment or request a no-penalty refund.'
          }
        />
        <PortfolioStat
          label="Refundable amount"
          value={formatUGX(refundable)}
          meta="No penalties are deducted. Pending refund requests reduce this figure."
        />
        <PortfolioStat
          label="Pending refund"
          value={formatUGX(userStats.pendingRefundTotal || 0)}
          meta={
            Number(userStats.pendingRefundTotal || 0) > 0
              ? 'Held while a staff member contacts you to confirm, then credits Main Account after approval.'
              : 'No refund request is currently awaiting review.'
          }
        />
        <PortfolioStat
          label="Project budget"
          value={totalBudget ? formatUGX(totalBudget) : '—'}
          meta="Vendor amount plus operational costs."
        />
      </div>

      <div className="rep-selected-bottom">
        <div className="rep-mini-ledger">
          <div className="rep-mini-head">
            <h4>
              <Receipt size={16} />
              Recent activity
            </h4>
            <button type="button" className="rep-link-btn" onClick={() => onOpen(project)}>
              View all
              <ArrowRight size={14} />
            </button>
          </div>
          {latestTransactions.length ? (
            <ul>
              {latestTransactions.map((tx) => (
                <li key={tx.id}>
                  <span>{tx.date}</span>
                  <b>{formatUGX(tx.amount)}</b>
                  <em>
                    {tx.type === 'refund'
                      ? 'Refund'
                      : tx.paymentStatus === 'full'
                        ? 'Fully paid'
                        : 'Partial'}
                  </em>
                </li>
              ))}
            </ul>
          ) : (
            <p>No transactions recorded for you on this project yet.</p>
          )}
        </div>

        <div className="rep-selected-actions">
          <button type="button" className="btn btn-primary" onClick={() => onOpen(project)}>
            Open full project
            <ArrowRight size={15} />
          </button>
          <button
            type="button"
            className="btn btn-outline"
            disabled={detailLoading || refundSubmitting}
            onClick={() => onRefund(project, refundable)}
          >
            <RotateCcw size={15} />
            {refundSubmitting ? 'Submitting refund…' : 'Request refund'}
          </button>
          {userStats.paymentCompleted ? (
            <p className="rep-transfer-note">Fully paid projects move toward land title processing.</p>
          ) : userStats.latestRefundStatus === 'pending' || userStats.latestRefundStatus === 'approved' ? (
            <p className="rep-transfer-note">
              Refund of {formatUGX(userStats.pendingRefundTotal || 0)} is held. A staff member
              will get in touch with you to confirm this request before it is credited to your
              Main Account.
            </p>
          ) : refundable <= 0 ? (
            <p className="rep-transfer-note">No refundable amount is currently available.</p>
          ) : (
            <p className="rep-transfer-note">
              Request a full no-penalty refund of {formatUGX(refundable)} to your Main Account.
              Bank details must be complete on your profile.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}

function ProjectSection({
  tone,
  kicker,
  title,
  description,
  projects,
  emptyText,
  onMembership,
  onInterest,
  onOpen,
}) {
  const Icon = tone === 'running' ? Building2 : tone === 'closed' ? Archive : Clock3
  return (
    <section className="rep-section">
      <div className="rep-section-head">
        <div>
          <span className={`rep-kicker rep-kicker-${tone}`}>{kicker}</span>
          <h2>
            <Icon size={18} />
            {title}
          </h2>
          <p>{description}</p>
        </div>
        <span className="rep-section-count">
          {projects.length} project{projects.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="rep-section-body">
        {projects.length ? (
          <div className="rep-project-grid">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onMembership={onMembership}
                onInterest={onInterest}
                onOpen={onOpen}
              />
            ))}
          </div>
        ) : (
          <p className="rep-empty">{emptyText}</p>
        )}
      </div>
    </section>
  )
}

export default function RealEstateDashboard() {
  const navigate = useNavigate()
  const { authFetch } = useAuth()
  const { member, addToast, reloadDashboard } = useMember()
  const [accountNumber, setAccountNumber] = useState(member.accountNumber || '—')
  const [runningProjects, setRunningProjects] = useState([])
  const [closedProjects, setClosedProjects] = useState([])
  const [upcomingProjects, setUpcomingProjects] = useState([])
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [selectedDetail, setSelectedDetail] = useState(null)
  const [selectedUserStats, setSelectedUserStats] = useState({
    totalPaid: 0,
    pendingBalance: null,
    paymentCompleted: false,
    refundableAmount: 0,
    pendingRefundTotal: 0,
    projectStatus: '',
    projectStatusLabel: '',
    latestRefundStatus: '',
    latestRefundStatusDisplay: '',
  })
  const [selectedTransactions, setSelectedTransactions] = useState([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [detailRefreshKey, setDetailRefreshKey] = useState(0)
  const [refundSubmitting, setRefundSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const allProjects = useMemo(
    () => [...runningProjects, ...closedProjects, ...upcomingProjects],
    [runningProjects, closedProjects, upcomingProjects],
  )
  const memberProjects = useMemo(
    () => allProjects.filter((project) => project.userHasAccess),
    [allProjects],
  )
  const selectedProject = useMemo(
    () =>
      allProjects.find((project) => String(project.id) === String(selectedProjectId)) ||
      memberProjects[0] ||
      null,
    [allProjects, memberProjects, selectedProjectId],
  )

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    authFetch('/api/projects/rep/')
      .then((payload) => {
        if (!alive) return
        setAccountNumber(payload.member?.accountNumber || member.accountNumber || '—')
        setRunningProjects(payload.runningProjects || [])
        setClosedProjects(payload.closedProjects || [])
        setUpcomingProjects(payload.upcomingProjects || [])
        const joined = [
          ...(payload.runningProjects || []),
          ...(payload.closedProjects || []),
          ...(payload.upcomingProjects || []),
        ].filter((project) => project.userHasAccess)
        setSelectedProjectId((current) => current || (joined[0]?.id ? String(joined[0].id) : ''))
      })
      .catch((err) => {
        if (!alive) return
        const message = err.message || 'Could not load Real Estate projects.'
        setError(message)
        addToast(message)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [authFetch, addToast, member.accountNumber])

  useEffect(() => {
    if (!selectedProject?.id || !selectedProject.userHasAccess) {
      setSelectedDetail(null)
      setSelectedUserStats({
        totalPaid: 0,
        pendingBalance: null,
        paymentCompleted: false,
        refundableAmount: 0,
        pendingRefundTotal: 0,
        projectStatus: '',
        projectStatusLabel: '',
        latestRefundStatus: '',
        latestRefundStatusDisplay: '',
      })
      setSelectedTransactions([])
      setDetailError('')
      return undefined
    }
    let alive = true
    setDetailLoading(true)
    setDetailError('')
    authFetch(`/api/projects/rep/${selectedProject.id}/`)
      .then((payload) => {
        if (!alive) return
        setSelectedDetail(payload.project || null)
        setSelectedUserStats({
          totalPaid: payload.user?.totalPaid || 0,
          pendingBalance: payload.user?.pendingBalance ?? null,
          paymentCompleted: Boolean(payload.user?.paymentCompleted),
          refundableAmount: payload.user?.refundableAmount || 0,
          pendingRefundTotal: payload.user?.pendingRefundTotal || 0,
          projectStatus: payload.user?.projectStatus || '',
          projectStatusLabel: payload.user?.projectStatusLabel || '',
          latestRefundStatus: payload.user?.latestRefundStatus || '',
          latestRefundStatusDisplay: payload.user?.latestRefundStatusDisplay || '',
        })
        setSelectedTransactions(payload.transactions || [])
      })
      .catch((err) => {
        if (!alive) return
        const message = err.message || 'Could not load selected real estate project.'
        setDetailError(message)
        addToast(message)
        setSelectedDetail(null)
        setSelectedTransactions([])
      })
      .finally(() => {
        if (alive) setDetailLoading(false)
      })
    return () => {
      alive = false
    }
  }, [authFetch, addToast, selectedProject, detailRefreshKey])

  const requestMembership = (project) => {
    addToast(`Request to join ${project.name} is still under development`)
  }

  const submitInterest = (project) => {
    addToast(`Submit interest for ${project.name} is still under development`)
  }

  const requestRefund = (project, amount) => {
    if (refundSubmitting) return
    if (selectedUserStats.paymentCompleted) {
      addToast('Fully paid projects move to land title processing, not refund.')
      return
    }
    if (selectedUserStats.latestRefundStatus === 'pending' || selectedUserStats.latestRefundStatus === 'approved') {
      addToast('Your refund request is already awaiting administrator processing.')
      return
    }
    if (!Number(amount || 0)) {
      addToast('No refundable amount is currently available for this project.')
      return
    }
    setRefundSubmitting(true)
    authFetch(`/api/projects/rep/${project.id}/refund/`, {
      method: 'POST',
      body: {
        amount,
        reason: 'Unable to complete Real Estate project payment',
      },
    })
      .then((payload) => {
        addToast(
          payload.detail ||
            'Refund request submitted. A staff member will get in touch with you to confirm this request before it is processed.',
        )
        setDetailRefreshKey((key) => key + 1)
        if (typeof reloadDashboard === 'function') {
          reloadDashboard({ silent: true })
        }
      })
      .catch((err) => {
        addToast(err.message || 'Could not submit refund request.')
      })
      .finally(() => {
        setRefundSubmitting(false)
      })
  }

  const openProject = (project) => navigate(`/projects/rep/${project.id}`)

  return (
    <AppShell title="Real Estate Projects">
      <div className="rep-page">
        <section className="rep-hero">
          <div>
            <h2>
              {member.firstName}&apos;s <span>Real Estate</span> Projects
            </h2>
            <p>Track payments, refund eligibility, and land title processing.</p>
          </div>
          <div className="rep-account">
            <small>Account Number</small>
            <strong>{accountNumber}</strong>
          </div>
        </section>

        {loading ? <p className="rep-status-line">Loading real estate projects…</p> : null}
        {error && !loading ? <p className="rep-status-line danger-text">{error}</p> : null}

        <section className="rep-section rep-portfolio-section">
          <div className="rep-section-head">
            <div>
              <span className="rep-kicker rep-kicker-running">Your portfolio</span>
              <h2>
                <Building2 size={18} />
                Real estate project selector
              </h2>
              <p>
                Real estate appears as one portfolio on your main dashboard. Select a project here
                to view its details and your personal position.
              </p>
            </div>
            <span className="rep-section-count">
              {memberProjects.length} joined project{memberProjects.length === 1 ? '' : 's'}
            </span>
          </div>
          <div className="rep-section-body">
            <ProjectSelector
              projects={memberProjects}
              selectedId={selectedProject?.id || ''}
              onSelect={(id) => setSelectedProjectId(String(id))}
            />
            <SelectedProjectPanel
              project={selectedProject}
              detailProject={selectedDetail}
              userStats={selectedUserStats}
              transactions={selectedTransactions}
              detailLoading={detailLoading}
              detailError={detailError}
              refundSubmitting={refundSubmitting}
              onOpen={openProject}
              onRefund={requestRefund}
            />
          </div>
        </section>

        <ProjectSection
          tone="running"
          kicker="Running projects"
          title="Running real estate opportunities"
          description="Browse active projects. Your joined projects are managed through the selector above."
          projects={runningProjects.filter((project) => !project.userHasAccess)}
          emptyText="There are currently no running cooperative real estate projects."
          onMembership={requestMembership}
          onInterest={submitInterest}
          onOpen={openProject}
        />

        <ProjectSection
          tone="closed"
          kicker="Closed projects"
          title="Completed and closed projects"
          description="Review closed projects that are not already in your portfolio selector."
          projects={closedProjects.filter((project) => !project.userHasAccess)}
          emptyText="No closed projects to display yet."
          onMembership={requestMembership}
          onInterest={submitInterest}
          onOpen={openProject}
        />

        <ProjectSection
          tone="upcoming"
          kicker="Upcoming projects"
          title="Upcoming real estate opportunities"
          description="Submit interest in planned projects so the team can prepare member allocations."
          projects={upcomingProjects}
          emptyText="There are no upcoming projects published yet."
          onMembership={requestMembership}
          onInterest={submitInterest}
          onOpen={openProject}
        />
      </div>
    </AppShell>
  )
}
