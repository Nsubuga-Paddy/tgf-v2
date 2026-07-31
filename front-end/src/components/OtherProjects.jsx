import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Hourglass, Lock, Send, X } from 'lucide-react'
import { useMember } from '../context/MemberContext'
import ProjectIcon from './ProjectIcon'

function statusLabel(availability) {
  if (availability === 'coming_soon') return 'Launching soon'
  if (availability === 'closed') return 'Closed'
  if (availability === 'pending') return 'Request under review'
  return 'No access'
}

export default function OtherProjects() {
  const { otherProjects, requestAccess, addToast } = useMember()
  const [active, setActive] = useState(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!active) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape' && !submitting) setActive(null)
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [active, submitting])

  const openRequest = (project) => {
    setNotes('')
    setActive(project)
  }

  const submitRequest = async (e) => {
    e.preventDefault()
    if (!active || submitting) return
    setSubmitting(true)
    try {
      await requestAccess(active.id, notes.trim())
      setActive(null)
    } catch (error) {
      addToast(error.message || 'Could not submit access request.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="section" id="discover">
      <div className="section-head">
        <div>
          <h2>Other projects</h2>
          <p className="section-note">Projects you can request to join</p>
        </div>
      </div>

      {otherProjects.length === 0 ? (
        <p className="section-note">No other projects to discover right now.</p>
      ) : (
        <div className="discover-list">
          {otherProjects.map((project) => {
            const availability = project.availability || 'request'
            const canRequest = Boolean(project.canRequest) || availability === 'request'
            return (
              <article
                key={project.id}
                className={`dcard ${canRequest ? 'avail' : ''}`}
              >
                {availability === 'coming_soon' ? (
                  <span className="status-tag st-soon dcard-soon">Coming soon</span>
                ) : null}

                <div className="dcard-body">
                  <div className="dcard-top">
                    <div className="dcard-icon">
                      <ProjectIcon name={project.icon} />
                    </div>
                    <div className="dcard-titles">
                      <b>{project.name}</b>
                      <span className="lock-chip">
                        <Lock size={11} />
                        {statusLabel(availability)}
                      </span>
                    </div>
                  </div>

                  <p className="dcard-desc">
                    {project.summary || 'More details coming soon.'}
                  </p>

                  <div className="dfacts">
                    {project.rate ? (
                      <div className="dfact">
                        <span className="k">Rate</span>
                        <span className="v rate">{project.rate}</span>
                      </div>
                    ) : null}
                    {project.minEntry ? (
                      <div className="dfact">
                        <span className="k">Minimum</span>
                        <span className="v">{project.minEntry}</span>
                      </div>
                    ) : null}
                    {project.cycle ? (
                      <div className="dfact">
                        <span className="k">Cycle</span>
                        <span className="v">{project.cycle}</span>
                      </div>
                    ) : null}
                  </div>

                  {project.wasRejected ? (
                    <p className="dcard-rejected-note">
                      A previous request was rejected. You can request again if the
                      project is open.
                    </p>
                  ) : null}
                </div>

                <div className="dcard-foot">
                  {canRequest ? (
                    <button
                      type="button"
                      className="btn btn-primary btn-block"
                      onClick={() => openRequest(project)}
                    >
                      <Send size={15} />
                      Request access
                    </button>
                  ) : availability === 'pending' ? (
                    <span className="req-pending">
                      <Hourglass size={15} />
                      Under review
                    </span>
                  ) : availability === 'coming_soon' ? (
                    <button type="button" className="btn btn-outline btn-block" disabled>
                      Coming soon
                    </button>
                  ) : (
                    <button type="button" className="btn btn-outline btn-block" disabled>
                      <Lock size={15} />
                      Closed
                    </button>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}

      {active
        ? createPortal(
            <div
              className="modal-overlay"
              onClick={submitting ? undefined : () => setActive(null)}
              role="presentation"
            >
              <div
                className="modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="request-access-title"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="modal-head">
                  <div className="modal-head-icon">
                    <Send size={20} />
                  </div>
                  <div className="modal-head-text">
                    <b id="request-access-title">Request project access</b>
                    <span>{active.name}</span>
                  </div>
                  <button
                    type="button"
                    className="modal-close"
                    aria-label="Close"
                    onClick={() => setActive(null)}
                    disabled={submitting}
                  >
                    <X size={18} />
                  </button>
                </div>

                <form onSubmit={submitRequest}>
                  <div className="modal-body profile-form-body">
                    <p className="withdraw-hint">
                      Send a request to join this project. An administrator will review
                      it and grant access if you qualify.
                    </p>
                    <label className="profile-field full">
                      <span>Message to administrator (optional)</span>
                      <textarea
                        rows={3}
                        placeholder="Tell us why you'd like to join..."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        disabled={submitting}
                      />
                    </label>
                  </div>
                  <div className="modal-foot">
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => setActive(null)}
                      disabled={submitting}
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      {submitting ? 'Sending…' : 'Send request'}
                    </button>
                  </div>
                </form>
              </div>
            </div>,
            document.body,
          )
        : null}
    </section>
  )
}
