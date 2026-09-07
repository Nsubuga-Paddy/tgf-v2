import { Link, Navigate, useParams } from 'react-router-dom'
import AppShell from '../../components/layout/AppShell'
import LoansFlowNav from '../../components/loans/LoansFlowNav'
import { LoanStatusBadge, formatLoanDateTime } from '../../components/loans/loanUi'
import { useLoans } from '../../context/LoansContext'
import { APPLICATION_STATUS_LABELS } from '../../data/loansData'
import { formatUGX } from '../../utils/format'

const REPAYMENT_LABELS = {
  main_account: 'Main Account',
  main_account_and_salary: 'Main Account + salary',
  business_income: 'Business income',
}

function timelineSteps(application) {
  const isRejected = application.status === 'rejected'
  const order = isRejected
    ? ['submitted', 'under_review', 'rejected']
    : ['submitted', 'under_review', 'approved', 'disbursed']

  const currentIndex = order.indexOf(application.status)
  const resolvedIndex = currentIndex >= 0 ? currentIndex : 0

  return order.map((status, index) => {
    const event = application.timeline.find((t) => t.status === status)
    let state = 'upcoming'
    if (index < resolvedIndex) state = 'done'
    else if (index === resolvedIndex) state = 'current'

    return {
      status,
      label: APPLICATION_STATUS_LABELS[status] || status,
      state,
      at: event?.at,
      note: event?.note,
    }
  })
}

export default function LoanApplicationDetail() {
  const { applicationId } = useParams()
  const { getApplication, loansLoading } = useLoans()
  const application = getApplication(applicationId)

  if (!application && loansLoading) {
    return (
      <AppShell title="Application status">
        <div className="loans-page loans-flow-page">
          <LoansFlowNav backTo="/loans/applications" backLabel="Back to applications" />
          <p className="loans-empty-inline">Loading application...</p>
        </div>
      </AppShell>
    )
  }

  if (!application) {
    return <Navigate to="/loans/applications" replace />
  }

  const steps = timelineSteps(application)

  return (
    <AppShell title="Application status">
      <div className="loans-page loans-flow-page">
        <LoansFlowNav backTo="/loans/applications" backLabel="Back to applications" />

        <header className="loans-detail-hero">
          <div>
            <small>{application.reference}</small>
            <h2>{application.purposeLabel}</h2>
            <p>Submitted {formatLoanDateTime(application.submittedAt)}</p>
          </div>
          <LoanStatusBadge status={application.status} />
        </header>

        <div className="loans-detail-metrics">
          <div>
            <span>Amount requested</span>
            <b>{formatUGX(application.amount)}</b>
          </div>
          <div>
            <span>Estimated deductions</span>
            <b>{formatUGX(application.fees?.totalDeductions || 0)}</b>
          </div>
          <div>
            <span>Net credited if approved</span>
            <b>{formatUGX(application.fees?.netDisbursedAmount || application.amount)}</b>
          </div>
          <div>
            <span>Term</span>
            <b>{application.termMonths} months</b>
          </div>
          <div>
            <span>Repayment plan</span>
            <b>{REPAYMENT_LABELS[application.repaymentSource] || application.repaymentSource}</b>
          </div>
        </div>

        <section className="loans-section">
          <div className="loans-section-head">
            <div>
              <h2>Application progress</h2>
              <p>Credit committee workflow</p>
            </div>
          </div>
          <ol className="loans-timeline">
            {steps.map((step) => (
              <li key={step.status} className={`loans-timeline-item ${step.state}`}>
                <span className="loans-timeline-dot" />
                <div>
                  <b>{step.label}</b>
                  {step.at ? <small>{formatLoanDateTime(step.at)}</small> : null}
                  {step.note ? <p>{step.note}</p> : null}
                </div>
              </li>
            ))}
          </ol>
        </section>

        {application.notes ? (
          <section className="loans-section">
            <div className="loans-section-head">
              <div>
                <h2>Your notes</h2>
              </div>
            </div>
            <p className="loans-notes-block">{application.notes}</p>
          </section>
        ) : null}

        {application.committeeNote ? (
          <section className="loans-section">
            <div className="loans-section-head">
              <div>
                <h2>Committee message</h2>
              </div>
            </div>
            <p className="loans-notes-block">{application.committeeNote}</p>
          </section>
        ) : (
          <p className="loans-committee-hint">
            MCS will post committee notes here when your application is reviewed.
          </p>
        )}

        {application.status === 'disbursed' ? (
          <div className="loans-flow-actions">
            <Link to="/loans" className="btn btn-primary">
              View active loans
            </Link>
          </div>
        ) : null}
      </div>
    </AppShell>
  )
}
