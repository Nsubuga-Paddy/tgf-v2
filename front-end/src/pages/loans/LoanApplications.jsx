import { Link } from 'react-router-dom'
import { FileText, Plus } from 'lucide-react'
import AppShell from '../../components/layout/AppShell'
import LoansFlowNav from '../../components/loans/LoansFlowNav'
import { LoanStatusBadge, formatLoanDateTime } from '../../components/loans/loanUi'
import { useLoans } from '../../context/LoansContext'
import { formatUGX } from '../../utils/format'

export default function LoanApplications() {
  const { applications, eligibility } = useLoans()

  return (
    <AppShell title="Loan applications">
      <div className="loans-page loans-flow-page">
        <LoansFlowNav />

        <div className="loans-section-head loans-applications-head">
          <div>
            <h2>My loan applications</h2>
            <p>Submitted requests and credit committee decisions</p>
          </div>
          {eligibility.applyEnabled ? (
            <Link to="/loans/apply" className="btn btn-primary btn-sm">
              <Plus size={14} />
              New application
            </Link>
          ) : null}
        </div>

        {applications.length === 0 ? (
          <div className="loans-empty-card">
            <FileText size={28} />
            <div>
              <b>No applications yet</b>
              <p>When you apply for a loan, it will appear here with live status updates.</p>
              {eligibility.applyEnabled ? (
                <Link to="/loans/apply" className="btn btn-primary btn-sm">
                  Apply for a loan
                </Link>
              ) : (
                <Link to="/loans/eligibility" className="btn btn-outline btn-sm">
                  Check eligibility
                </Link>
              )}
            </div>
          </div>
        ) : (
          <ul className="loans-applications-list">
            {applications.map((app) => (
              <li key={app.id}>
                <Link to={`/loans/applications/${app.id}`} className="loans-application-card">
                  <div className="loans-application-card-main">
                    <div>
                      <small>{app.reference}</small>
                      <b>{app.purposeLabel}</b>
                    </div>
                    <LoanStatusBadge status={app.status} />
                  </div>
                  <div className="loans-application-card-meta">
                    <span>{formatUGX(app.amount)}</span>
                    <span>{app.termMonths} months</span>
                    <span>Submitted {formatLoanDateTime(app.submittedAt)}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  )
}
