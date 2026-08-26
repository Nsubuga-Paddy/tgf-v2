import { useEffect, useMemo, useState } from 'react'
import {
  ArrowLeftRight,
  Building2,
  CheckCircle2,
  FolderOpen,
  LayoutGrid,
  Banknote,
  RefreshCw,
  Sparkles,
  Truck,
  Users,
  X,
  Zap,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PROJECT_TAKE_ACTIONS } from '../data/memberData'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'
import ProjectIcon from './ProjectIcon'

const ACTION_ICONS = {
  transfer: ArrowLeftRight,
  users: Users,
  dashboard: LayoutGrid,
  cash: Banknote,
  truck: Truck,
  exchange: ArrowLeftRight,
  building: Building2,
  retain: RefreshCw,
}

function parseAmountInput(raw) {
  if (raw == null || String(raw).trim() === '') return null
  const cleaned = String(raw).replace(/,/g, '').trim()
  const n = Number(cleaned)
  if (!Number.isFinite(n) || n <= 0) return null
  return Math.round(n)
}

export default function MaturedProjects() {
  const navigate = useNavigate()
  const { authFetch } = useAuth()
  const { maturedProjects, addToast, reloadDashboard } = useMember()
  const [actionProject, setActionProject] = useState(null)
  const [redeemProject, setRedeemProject] = useState(null)
  const [redeemDepositId, setRedeemDepositId] = useState('')
  const [redeemAmount, setRedeemAmount] = useState('')
  const [transferring, setTransferring] = useState(false)

  const redeemDeposits = useMemo(
    () => redeemProject?.redeemDeposits || [],
    [redeemProject],
  )

  const selectedRedeemCap = useMemo(() => {
    if (!redeemProject) return 0
    const match = redeemDeposits.find((d) => d.depositId === redeemDepositId)
    if (match) return Number(match.redeemable || 0)
    return Number(redeemProject.availableAmount || 0)
  }, [redeemProject, redeemDeposits, redeemDepositId])

  useEffect(() => {
    if (!redeemProject) return
    const first =
      redeemProject.depositId ||
      redeemDeposits[0]?.depositId ||
      ''
    setRedeemDepositId(first)
    const cap =
      redeemDeposits.find((d) => d.depositId === first)?.redeemable ??
      redeemProject.availableAmount
    setRedeemAmount(String(Math.round(Number(cap || 0))))
  }, [redeemProject, redeemDeposits])

  const openProject = (project) => {
    if (project.projectId === '52wsc') {
      navigate('/projects/52wsc')
      return
    }
    if (project.projectId === 'gwc') {
      navigate('/projects/gwc')
      return
    }
    if (project.projectId === 'cgf') {
      navigate('/projects/cgf')
      return
    }
    if (project.projectId === 'rep' || String(project.projectId || '').startsWith('rep-')) {
      const match = String(project.projectId).match(/^rep-(\d+)$/)
      if (match) {
        navigate(`/projects/rep/${match[1]}`)
        return
      }
      navigate('/projects/rep')
      return
    }
    addToast(`${project.shortName} is still under development`)
  }

  const actionKey = actionProject?.projectId?.startsWith?.('rep-')
    ? 'rep'
    : actionProject?.projectId
  const takeActions = actionProject ? PROJECT_TAKE_ACTIONS[actionKey] || [] : []

  const openRedeemModal = (project) => {
    setActionProject(null)
    setRedeemProject(project)
  }

  const closeRedeemModal = () => {
    if (transferring) return
    setRedeemProject(null)
    setRedeemDepositId('')
    setRedeemAmount('')
  }

  const submitRedeem = async () => {
    if (!redeemProject || transferring) return
    const depositId = redeemDepositId || redeemProject.depositId
    if (!depositId) {
      addToast('Select a GWC deposit to redeem from.')
      return
    }
    const amount = parseAmountInput(redeemAmount)
    if (amount == null) {
      addToast('Enter a valid amount greater than zero.')
      return
    }
    if (amount > selectedRedeemCap) {
      addToast(
        `Amount cannot exceed redeemable interest (${formatUGX(selectedRedeemCap)}).`,
      )
      return
    }
    setTransferring(true)
    try {
      const payload = await authFetch('/api/projects/gwc/redeem-interest/', {
        method: 'POST',
        body: { depositId, amount },
      })
      addToast(
        payload.detail ||
          'Redeemable interest was credited to your Main Account.',
      )
      setRedeemProject(null)
      setRedeemDepositId('')
      setRedeemAmount('')
      await reloadDashboard({ silent: true })
    } catch (err) {
      addToast(err.message || 'Could not redeem GWC interest.')
    } finally {
      setTransferring(false)
    }
  }

  const runAction = async (action) => {
    if (!actionProject || transferring) return
    if (action.id === 'open-gwc') {
      setActionProject(null)
      navigate('/projects/gwc')
      return
    }
    if (actionProject.projectId === 'gwc' && action.id === 'redeem-interest') {
      openRedeemModal(actionProject)
      return
    }
    if (actionProject.projectId === 'cgf' && action.id === 'transfer-main') {
      setTransferring(true)
      try {
        const payload = await authFetch('/api/projects/cgf/transfer-to-main/', {
          method: 'POST',
          body: {},
        })
        addToast(
          payload.detail ||
            'Matured CGF value was credited to your Main Account.',
        )
        setActionProject(null)
        await reloadDashboard({ silent: true })
      } catch (err) {
        addToast(err.message || 'Could not transfer matured CGF funds.')
      } finally {
        setTransferring(false)
      }
      return
    }
    if (actionProject.projectId === '52wsc') {
      if (action.id === 'open-52wsc' || action.id === 'open') {
        setActionProject(null)
        navigate('/projects/52wsc')
        return
      }
      const endpoint =
        action.id === 'start-new-cycle'
          ? '/api/projects/52wsc/start-new-cycle/'
          : action.id === 'transfer-main' || action.id === 'transfer-all'
            ? '/api/projects/52wsc/transfer-all/'
            : action.id === 'transfer-pot'
              ? '/api/projects/52wsc/transfer-pot/'
              : null
      if (!endpoint) {
        setActionProject(null)
        navigate('/projects/52wsc')
        return
      }
      setTransferring(true)
      try {
        const payload = await authFetch(endpoint, { method: 'POST', body: {} })
        addToast(payload.detail || '52WSC maturity action completed.')
        setActionProject(null)
        await reloadDashboard({ silent: true })
      } catch (err) {
        addToast(err.message || 'Could not complete 52WSC maturity action.')
      } finally {
        setTransferring(false)
      }
      return
    }
    addToast(`${action.label} is still under development`)
    setActionProject(null)
  }

  const isGwcRedeemCard = (project) =>
    project.projectId === 'gwc' &&
    (project.actionKind === 'redeem_interest' || Number(project.availableAmount) > 0)

  return (
    <section className="section matured-section" id="matured-projects">
      <div className="section-head">
        <div>
          <h2>Matured projects</h2>
          <p className="section-note">Open the project or take the next maturity action</p>
        </div>
        <span className="count">{maturedProjects.length}</span>
      </div>

      {maturedProjects.length === 0 ? (
        <div className="matured-empty">
          <div className="matured-empty-icon">
            <Sparkles size={24} />
          </div>
          <div>
            <b>No matured projects yet</b>
            <p>
              When any project reaches maturity, it will appear here so you can open it and take
              the next available action.
            </p>
          </div>
        </div>
      ) : (
        <div className="matured-list">
          {maturedProjects.map((project) => (
            <article key={project.id} className="matured-card">
              <div className="matured-card-head">
                <div className="pcard-icon">
                  <ProjectIcon name={project.icon} />
                </div>
                <div className="matured-title">
                  <b>{project.name}</b>
                  <span>{project.cycleLine}</span>
                </div>
                <span className="matured-badge">
                  <CheckCircle2 size={13} />
                  {isGwcRedeemCard(project) ? 'Interest ready' : 'Matured'}
                </span>
              </div>

              <div className="matured-amount">
                <small>
                  {isGwcRedeemCard(project)
                    ? 'Redeemable interest'
                    : 'Available at maturity'}
                </small>
                <strong>{formatUGX(project.availableAmount)}</strong>
                <span>
                  {isGwcRedeemCard(project)
                    ? `As of ${project.maturedOn || 'today'}`
                    : `Matured on ${project.maturedOn}`}
                </span>
              </div>

              <div className="matured-breakdown">
                <div>
                  <span>Principal</span>
                  <b>{formatUGX(project.principal)}</b>
                </div>
                <div>
                  <span>{isGwcRedeemCard(project) ? 'Interest earned' : 'Earnings'}</span>
                  <b>{formatUGX(project.earnings)}</b>
                </div>
              </div>

              <p className="matured-next">{project.nextBestAction}</p>

              <div className="matured-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => openProject(project)}
                >
                  <FolderOpen size={15} />
                  Open
                </button>
                {isGwcRedeemCard(project) ? (
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => openRedeemModal(project)}
                  >
                    <ArrowLeftRight size={15} />
                    Redeem interest
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => setActionProject(project)}
                  >
                    <Zap size={15} />
                    Take action
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {actionProject ? (
        <div
          className="take-action-backdrop"
          role="presentation"
          onClick={() => setActionProject(null)}
        >
          <div
            className="take-action-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="take-action-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="take-action-head">
              <div>
                <h3 id="take-action-title">Take action · {actionProject.shortName}</h3>
                <p>{actionProject.name}</p>
              </div>
              <button
                type="button"
                className="nav-icon-btn"
                aria-label="Close"
                onClick={() => setActionProject(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="take-action-body">
              <p className="take-action-lead">
                {actionProject.projectId === 'cgf'
                  ? 'Transfer the matured CGF value to your Main Account. You can then request a withdrawal from Main Account.'
                  : 'Choose what to do with this matured cycle. Cash leaves MCS only from your main account after a transfer.'}
              </p>
              {takeActions.length === 0 ? (
                <p className="take-action-empty">No actions configured for this project yet.</p>
              ) : (
                <ul className="take-action-list">
                  {takeActions.map((action) => {
                    const Icon = ACTION_ICONS[action.icon] || Zap
                    return (
                      <li key={action.id}>
                        <button
                          type="button"
                          className="take-action-option"
                          onClick={() => runAction(action)}
                          disabled={transferring}
                        >
                          <span className="take-action-option-icon">
                            <Icon size={18} />
                          </span>
                          <span className="take-action-option-copy">
                            <b>
                              {transferring && action.id === 'transfer-main'
                                ? 'Transferring…'
                                : action.label}
                            </b>
                            <small>
                              {actionProject.projectId === 'cgf' && actionProject.availableAmount
                                ? `${action.description} · Available ${formatUGX(actionProject.availableAmount)}`
                                : action.description}
                            </small>
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {redeemProject ? (
        <div
          className="take-action-backdrop"
          role="presentation"
          onClick={closeRedeemModal}
        >
          <div
            className="take-action-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="gwc-redeem-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="take-action-head">
              <div>
                <h3 id="gwc-redeem-title">Redeem GWC interest</h3>
                <p>Transfer to Main Account · full or partial</p>
              </div>
              <button
                type="button"
                className="nav-icon-btn"
                aria-label="Close"
                onClick={closeRedeemModal}
                disabled={transferring}
              >
                <X size={18} />
              </button>
            </div>
            <div className="take-action-body">
              <p className="take-action-lead">
                Available now: <strong>{formatUGX(selectedRedeemCap)}</strong>. Enter the full
                amount or a smaller partial amount.
              </p>

              {redeemDeposits.length > 1 ? (
                <label className="gwc-redeem-field">
                  <span>Deposit</span>
                  <select
                    value={redeemDepositId}
                    onChange={(e) => {
                      const id = e.target.value
                      setRedeemDepositId(id)
                      const cap =
                        redeemDeposits.find((d) => d.depositId === id)?.redeemable || 0
                      setRedeemAmount(String(Math.round(Number(cap))))
                    }}
                    disabled={transferring}
                  >
                    {redeemDeposits.map((d) => (
                      <option key={d.depositId} value={d.depositId}>
                        {d.depositId} · {formatUGX(d.redeemable)}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p className="gwc-redeem-deposit-ref">
                  Deposit: <strong>{redeemDepositId || redeemProject.depositId || '—'}</strong>
                </p>
              )}

              <label className="gwc-redeem-field">
                <span>Amount (UGX)</span>
                <input
                  type="text"
                  inputMode="numeric"
                  value={redeemAmount}
                  onChange={(e) => setRedeemAmount(e.target.value)}
                  disabled={transferring}
                  placeholder="Enter amount"
                />
              </label>

              <div className="gwc-redeem-actions">
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  disabled={transferring || selectedRedeemCap <= 0}
                  onClick={() =>
                    setRedeemAmount(String(Math.round(Number(selectedRedeemCap || 0))))
                  }
                >
                  Use full amount
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={transferring}
                  onClick={submitRedeem}
                >
                  <ArrowLeftRight size={15} />
                  {transferring ? 'Transferring…' : 'Transfer to Main Account'}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
