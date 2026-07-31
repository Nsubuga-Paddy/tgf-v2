import { useEffect, useState } from 'react'
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
  UserCheck,
  UserPlus,
  Users,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'

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
  const { member, addToast } = useMember()
  const [accountNumber, setAccountNumber] = useState(member.accountNumber || '—')
  const [runningProjects, setRunningProjects] = useState([])
  const [closedProjects, setClosedProjects] = useState([])
  const [upcomingProjects, setUpcomingProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  const requestMembership = (project) => {
    addToast(`Request to join ${project.name} is still under development`)
  }

  const submitInterest = (project) => {
    addToast(`Submit interest for ${project.name} is still under development`)
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
            <p>Track your real estate investments and project performance.</p>
          </div>
          <div className="rep-account">
            <small>Account Number</small>
            <strong>{accountNumber}</strong>
          </div>
        </section>

        {loading ? <p className="rep-status-line">Loading real estate projects…</p> : null}
        {error && !loading ? <p className="rep-status-line danger-text">{error}</p> : null}

        <ProjectSection
          tone="running"
          kicker="Running projects"
          title="Cooperative real estate portfolio"
          description="Join an active cooperative project that fits your goals. Restricted details open after membership approval."
          projects={runningProjects}
          emptyText="There are currently no running cooperative real estate projects."
          onMembership={requestMembership}
          onInterest={submitInterest}
          onOpen={openProject}
        />

        <ProjectSection
          tone="closed"
          kicker="Closed projects"
          title="Completed and closed projects"
          description="Review projects that have reached completion or been closed by the cooperative."
          projects={closedProjects}
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
