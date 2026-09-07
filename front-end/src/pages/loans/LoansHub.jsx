import { Link } from 'react-router-dom'
import { useState } from 'react'
import {
  AlertCircle,
  ArrowRight,
  ArrowUpFromLine,
  CalendarClock,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  FileText,
  HandCoins,
  History,
  Info,
  Wallet,
} from 'lucide-react'
import AppShell from '../../components/layout/AppShell'
import RepayFromMainModal from '../../components/loans/RepayFromMainModal'
import LoanExternalPayDetails from '../../components/loans/LoanExternalPayDetails'
import { FactorIcon, LoanStatusBadge, eligibilityTone, formatLoanDateTime } from '../../components/loans/loanUi'
import { useLoans } from '../../context/LoansContext'
import { useMember } from '../../context/MemberContext'
import { LOAN_POLICY, LOAN_REPAYMENT_METHODS, MAX_BORROWING_LIMIT } from '../../data/loansData'
import { formatUGX } from '../../utils/format'

export default function LoansHub() {
  const { mainAccount } = useMember()
  const { eligibility, activeLoans, closedLoans, applications, submitLoanRepayment } = useLoans()
  const [repayLoanId, setRepayLoanId] = useState(null)
  const [policyBankDetailsOpen, setPolicyBankDetailsOpen] = useState(false)
  const repayLoan = activeLoans.find((loan) => loan.id === repayLoanId) || null

  const summary = {
    outstanding: activeLoans.reduce((sum, loan) => sum + Number(loan.outstanding || 0), 0),
    activeCount: activeLoans.length,
    nextDue: activeLoans.find((loan) => loan.nextDueDate),
    hasOverdue: activeLoans.some((loan) => loan.status === 'overdue'),
    pendingApps: applications.filter((a) =>
      ['submitted', 'under_review', 'approved'].includes(a.status),
    ).length,
  }

  const eligibilityToneClass = eligibilityTone(eligibility.status)

  return (
    <AppShell title="Member Loans">
      <div className="loans-page">
        <header className="loans-intro">
          <p>
            Cooperative credit for members. Check eligibility, apply for a loan, track applications,
            and manage repayments — separate from your investment projects.
          </p>
        </header>

        <div className="loans-quick-actions">
          <Link to="/loans/eligibility" className="loans-quick-card">
            <CircleHelp size={20} />
            <div>
              <b>Check eligibility</b>
              <span>See your borrowing limit and criteria</span>
            </div>
            <ArrowRight size={16} />
          </Link>
          <Link
            to="/loans/apply"
            className={`loans-quick-card primary ${eligibility.applyEnabled ? '' : 'disabled'}`}
            aria-disabled={!eligibility.applyEnabled}
            onClick={(e) => {
              if (!eligibility.applyEnabled) e.preventDefault()
            }}
          >
            <FileText size={20} />
            <div>
              <b>Apply for a loan</b>
              <span>Submit to the credit committee</span>
            </div>
            <ArrowRight size={16} />
          </Link>
          <Link to="/loans/applications" className="loans-quick-card">
            <ClipboardList size={20} />
            <div>
              <b>My applications</b>
              <span>
                {summary.pendingApps > 0
                  ? `${summary.pendingApps} in progress`
                  : 'Track status & decisions'}
              </span>
            </div>
            <ArrowRight size={16} />
          </Link>
        </div>

        <section className="loans-section" aria-labelledby="loans-eligibility-title">
          <div className="loans-section-head">
            <div>
              <h2 id="loans-eligibility-title">Loan eligibility</h2>
              <p>
                {eligibility.checkedAt
                  ? `Last checked ${formatLoanDateTime(eligibility.checkedAt)}`
                  : 'Based on your current member profile'}
              </p>
            </div>
            <span className={`loans-eligibility-pill ${eligibilityToneClass}`}>
              {eligibility.statusLabel}
            </span>
          </div>

          <article className={`loans-eligibility-card ${eligibilityToneClass}`}>
            <div className="loans-eligibility-main">
              <div className="loans-eligibility-icon">
                <HandCoins size={22} />
              </div>
              <div>
                <p className="loans-eligibility-summary">{eligibility.summary}</p>
                {eligibility.estimatedMaxAmount != null ? (
                  <div className="loans-eligibility-limit">
                    <small>{eligibility.estimatedMaxLabel}</small>
                    <strong>{formatUGX(eligibility.estimatedMaxAmount)}</strong>
                    <span className="loans-limit-cap">
                      Hard cap: {formatUGX(MAX_BORROWING_LIMIT)} per member
                    </span>
                  </div>
                ) : null}
              </div>
            </div>

            <ul className="loans-factors">
              {eligibility.factors.map((factor) => (
                <li
                  key={factor.id}
                  className={
                    factor.met === true ? 'met' : factor.met === false ? 'unmet' : 'pending'
                  }
                >
                  <FactorIcon met={factor.met} />
                  <div>
                    <b>{factor.label}</b>
                    <span>{factor.detail}</span>
                  </div>
                </li>
              ))}
            </ul>

            <div className="loans-eligibility-actions">
              <Link to="/loans/eligibility" className="btn btn-outline">
                <CircleHelp size={15} />
                Re-check eligibility
              </Link>
              {eligibility.applyEnabled ? (
                <Link to="/loans/apply" className="btn btn-primary">
                  <FileText size={15} />
                  Apply for a loan
                </Link>
              ) : (
                <button type="button" className="btn btn-primary" disabled>
                  <FileText size={15} />
                  Apply for a loan
                </button>
              )}
            </div>
          </article>
        </section>

        {summary.activeCount > 0 ? (
          <div className="loans-summary-strip">
            <div className="loans-summary-item">
              <small>Total outstanding</small>
              <strong>{formatUGX(summary.outstanding)}</strong>
            </div>
            <div className="loans-summary-item">
              <small>Active loans</small>
              <strong>{summary.activeCount}</strong>
            </div>
            {summary.nextDue ? (
              <div className="loans-summary-item">
                <small>Next payment due</small>
                <strong>
                  {summary.nextDue.nextDueDate}
                  {summary.nextDue.nextDueAmount
                    ? ` · ${formatUGX(summary.nextDue.nextDueAmount)}`
                    : ''}
                </strong>
              </div>
            ) : null}
            {summary.hasOverdue ? (
              <div className="loans-summary-alert">
                <AlertCircle size={16} />
                You have an overdue payment
              </div>
            ) : null}
          </div>
        ) : null}

        <section className="loans-section" aria-labelledby="loans-active-title">
          <div className="loans-section-head">
            <div>
              <h2 id="loans-active-title">My active loans</h2>
              <p>Repayment schedules and Main Account repayments</p>
            </div>
          </div>

          {activeLoans.length === 0 ? (
            <div className="loans-empty-card">
              <Wallet size={28} />
              <div>
                <b>No active loans</b>
                <p>Approved and disbursed loans appear here with schedules and repayment options.</p>
              </div>
            </div>
          ) : (
            <div className="loans-list">
              {activeLoans.map((loan) => (
                <article key={loan.id} className="loans-card">
                  <div className="loans-card-head">
                    <div>
                      <small>{loan.reference}</small>
                      <h3>{loan.purposeLabel || loan.purpose}</h3>
                    </div>
                    <LoanStatusBadge status={loan.status} />
                  </div>
                  <div className="loans-card-metrics">
                    <div>
                      <span>Outstanding</span>
                      <b>{formatUGX(loan.outstanding)}</b>
                    </div>
                    <div>
                      <span>Interest rate</span>
                      <b>{loan.rateDisplay}</b>
                    </div>
                    <div>
                      <span>Next due</span>
                      <b>
                        {loan.nextDueDate || '—'}
                        {loan.nextDueAmount ? ` · ${formatUGX(loan.nextDueAmount)}` : ''}
                      </b>
                    </div>
                  </div>
                  <div className="loans-card-actions">
                    <Link to={`/loans/facility/${loan.id}`} className="btn btn-primary btn-sm">
                      <CalendarClock size={14} />
                      View loan & schedule
                    </Link>
                    <button
                      type="button"
                      className="btn btn-outline btn-sm"
                      onClick={() => setRepayLoanId(loan.id)}
                    >
                      <ArrowUpFromLine size={14} />
                      Pay loan
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}

          {activeLoans.length > 0 ? (
            <p className="loans-main-hint">
              <Info size={14} />
              Main Account available: {formatUGX(mainAccount?.available || 0)}
            </p>
          ) : null}
        </section>

        {applications.length > 0 ? (
          <section className="loans-section" aria-labelledby="loans-apps-preview">
            <div className="loans-section-head">
              <div>
                <h2 id="loans-apps-preview">Recent applications</h2>
                <p>Latest loan requests and committee decisions</p>
              </div>
              <Link to="/loans/applications" className="btn btn-outline btn-sm">
                View all
              </Link>
            </div>
            <ul className="loans-applications-preview">
              {applications.slice(0, 3).map((app) => (
                <li key={app.id}>
                  <Link to={`/loans/applications/${app.id}`} className="loans-application-row">
                    <div>
                      <b>{app.reference}</b>
                      <span>
                        {app.purposeLabel} · {formatUGX(app.amount)} · {app.termMonths} months
                      </span>
                    </div>
                    <LoanStatusBadge status={app.status} />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="loans-section" aria-labelledby="loans-history-title">
          <div className="loans-section-head">
            <div>
              <h2 id="loans-history-title">Loan history</h2>
              <p>Fully paid and closed facilities</p>
            </div>
          </div>

          {closedLoans.length === 0 ? (
            <div className="loans-empty-card subtle">
              <History size={24} />
              <div>
                <b>No closed loans yet</b>
                <p>Paid-off loans remain visible here for your records.</p>
              </div>
            </div>
          ) : (
            <ul className="loans-history-list">
              {closedLoans.map((loan) => (
                <li key={loan.id} className="loans-history-item">
                  <div>
                    <b>{loan.purposeLabel || loan.purpose}</b>
                    <span>
                      {loan.reference} · Closed {loan.closedDate}
                    </span>
                  </div>
                  <div>
                    <span>Total repaid</span>
                    <b>{formatUGX(loan.totalRepaid)}</b>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="loans-section" aria-labelledby="loans-policy-title">
          <div className="loans-section-head">
            <div>
              <h2 id="loans-policy-title">How MCS loans work</h2>
              <p>Policy summary — full terms from the cooperative</p>
            </div>
          </div>

          <article className="loans-policy-card">
            <div className="loans-policy-metrics">
              <div>
                <small>Typical rate</small>
                <strong>{LOAN_POLICY.rateDisplay}</strong>
              </div>
              <div>
                <small>Term range</small>
                <strong>{LOAN_POLICY.termDisplay}</strong>
              </div>
            </div>
            <p>{LOAN_POLICY.basis}</p>
            <ul>
              {LOAN_POLICY.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>

            <div className="loans-repay-methods loans-repay-methods-compact">
              {LOAN_REPAYMENT_METHODS.map((method) => (
                <div key={method.id} className="loans-repay-method-card compact">
                  <b>{method.label}</b>
                  <p>{method.description}</p>
                  {method.id === 'bank_transfer' ? (
                    <>
                      <button
                        type="button"
                        className={`loans-bank-details-toggle ${policyBankDetailsOpen ? 'open' : ''}`}
                        aria-expanded={policyBankDetailsOpen}
                        onClick={() => setPolicyBankDetailsOpen((open) => !open)}
                      >
                        <span>
                          {policyBankDetailsOpen ? 'Hide account details' : 'View account details'}
                        </span>
                        <ChevronDown size={16} />
                      </button>
                      {policyBankDetailsOpen ? <LoanExternalPayDetails methodId={method.id} /> : null}
                    </>
                  ) : null}
                </div>
              ))}
            </div>

            <Link className="loans-help-link" to="/help">
              <CircleHelp size={16} />
              Visit Help Center for guidance
            </Link>
          </article>
        </section>
      </div>

      <RepayFromMainModal
        open={Boolean(repayLoan)}
        onClose={() => setRepayLoanId(null)}
        loan={repayLoan}
        available={mainAccount?.available || 0}
        onSubmit={(amount) =>
          submitLoanRepayment({
            loanId: repayLoan.id,
            amount,
            availableMain: mainAccount?.available || 0,
          })
        }
      />
    </AppShell>
  )
}
