import { useNavigate } from 'react-router-dom'
import { ClipboardList } from 'lucide-react'
import { useMember } from '../context/MemberContext'

export default function PendingActionRequests() {
  const navigate = useNavigate()
  const { actionRequests, pendingRequests } = useMember()
  const rows = (actionRequests && actionRequests.length
    ? actionRequests.filter((req) => (req.status || '').toLowerCase() === 'pending')
    : pendingRequests) || []

  return (
    <section className="section" id="pending-actions">
      <div className="section-head">
        <div>
          <h2>Pending action requests</h2>
          <p className="section-note">Withdrawals, refunds, transfers, and access requests awaiting review</p>
        </div>
        <button type="button" className="btn btn-outline" onClick={() => navigate('/profile')}>
          View all on profile
        </button>
      </div>

      {rows.length === 0 ? (
        <div className="action-requests-empty dashboard-pending-empty">
          <ClipboardList size={22} />
          <div>
            <b>No pending requests</b>
            <p>Submitted refunds are held until a staff member contacts you to confirm, then credits Main Account after approval.</p>
          </div>
        </div>
      ) : (
        <div className="action-requests-list dashboard-pending-list">
          {rows.map((req) => (
            <article key={req.id} className={`action-request-card tone-${req.tone || 'coop'}`}>
              <div className="action-request-header">
                <span className="action-request-type">{req.label || req.typeLabel}</span>
                <span className={`action-request-project ${req.tone || 'coop'}`}>
                  {req.project || 'MCS'}
                </span>
              </div>
              <div className="action-request-detail">{req.detail || 'Awaiting review'}</div>
              <div className="action-request-footer">
                <span className="action-request-date">{req.createdAt || 'Pending'}</span>
                <span className={`action-request-status ${req.status || 'pending'}`}>
                  {req.statusDisplay || 'Pending'}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
