import { useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import {
  ArrowUpFromLine,
  Building2,
  CalendarClock,
  ChevronDown,
  Percent,
  Receipt,
  WalletCards,
  Zap,
} from 'lucide-react'
import AppShell from '../../components/layout/AppShell'
import LoanExternalPayDetails from '../../components/loans/LoanExternalPayDetails'
import LoanScheduleTable from '../../components/loans/LoanScheduleTable'
import LoansFlowNav from '../../components/loans/LoansFlowNav'
import RepayFromMainModal from '../../components/loans/RepayFromMainModal'
import { LoanStatusBadge } from '../../components/loans/loanUi'
import { useLoans } from '../../context/LoansContext'
import { useMember } from '../../context/MemberContext'
import { formatUGX } from '../../utils/format'

export default function LoanFacilityDetail() {
  const { loanId } = useParams()
  const { getLoan, submitLoanRepayment, repaymentMethods, loansLoading } = useLoans()
  const { mainAccount } = useMember()
  const loan = getLoan(loanId)
  const [tab, setTab] = useState('schedule')
  const [mainRepayOpen, setMainRepayOpen] = useState(false)
  const [bankDetailsOpen, setBankDetailsOpen] = useState(false)
  const mainAccountMethod = repaymentMethods.find((method) => method.id === 'main_account')
  const bankTransferMethod = repaymentMethods.find((method) => method.id === 'bank_transfer')

  if (!loan && loansLoading) {
    return (
      <AppShell title="Loan details">
        <div className="loans-page loans-flow-page">
          <LoansFlowNav />
          <p className="loans-empty-inline">Loading loan details...</p>
        </div>
      </AppShell>
    )
  }

  if (!loan) {
    return <Navigate to="/loans" replace />
  }

  return (
    <AppShell title="Loan details">
      <div className="loans-page loans-flow-page">
        <LoansFlowNav />

        <header className="loans-detail-hero">
          <div>
            <small>{loan.reference}</small>
            <h2>{loan.purposeLabel || loan.purpose}</h2>
            <p>Disbursed {loan.disbursedDate}</p>
          </div>
          <LoanStatusBadge status={loan.status} />
        </header>

        <div className="loans-detail-metrics">
          <div className="loans-detail-metric-card highlight">
            <div className="loans-detail-metric-icon">
              <WalletCards size={18} />
            </div>
            <div>
              <span>Outstanding</span>
              <b>{formatUGX(loan.outstanding)}</b>
            </div>
          </div>
          <div className="loans-detail-metric-card">
            <div className="loans-detail-metric-icon">
              <ArrowUpFromLine size={18} />
            </div>
            <div>
              <span>Original principal</span>
              <b>{formatUGX(loan.principal)}</b>
            </div>
          </div>
          <div className="loans-detail-metric-card">
            <div className="loans-detail-metric-icon">
              <WalletCards size={18} />
            </div>
            <div>
              <span>Net credited</span>
              <b>{formatUGX(loan.netDisbursedAmount || loan.principal)}</b>
            </div>
          </div>
          <div className="loans-detail-metric-card">
            <div className="loans-detail-metric-icon">
              <Receipt size={18} />
            </div>
            <div>
              <span>Upfront deductions</span>
              <b>{formatUGX(loan.totalDeductions || 0)}</b>
            </div>
          </div>
          <div className="loans-detail-metric-card">
            <div className="loans-detail-metric-icon">
              <Percent size={18} />
            </div>
            <div>
              <span>Interest rate</span>
              <b>{loan.rateDisplay}</b>
            </div>
          </div>
          <div className="loans-detail-metric-card">
            <div className="loans-detail-metric-icon">
              <CalendarClock size={18} />
            </div>
            <div>
              <span>Next installment</span>
              <b>
                {loan.nextDueDate || '—'}
                {loan.nextDueAmount ? ` · ${formatUGX(loan.nextDueAmount)}` : ''}
              </b>
            </div>
          </div>
        </div>

        <section className="loans-section" aria-labelledby="loans-repay-methods-title">
          <div className="loans-section-head">
            <div>
              <h2 id="loans-repay-methods-title">Repayment options</h2>
              <p>
                Repay instantly from Main Account, or pay offline by bank transfer
              </p>
            </div>
          </div>

          <div className="loans-repay-stack">
            {mainAccountMethod ? (
              <article className="loans-main-repay-bar">
                <div className="loans-main-repay-copy">
                  <div className="loans-repay-method-icon">
                    <ArrowUpFromLine size={18} />
                  </div>
                  <div>
                    <div className="loans-main-repay-title">
                      <b>{mainAccountMethod.label}</b>
                      <span className="loans-instant-badge">
                        <Zap size={12} />
                        Instant
                      </span>
                    </div>
                    <p>{mainAccountMethod.description}</p>
                  </div>
                </div>
                <div className="loans-main-repay-action">
                  <span>
                    Available <b>{formatUGX(mainAccount?.available || 0)}</b>
                  </span>
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={() => setMainRepayOpen(true)}
                  >
                    {mainAccountMethod.cta}
                  </button>
                </div>
              </article>
            ) : null}

            {bankTransferMethod ? (
              <article className="loans-bank-transfer-panel">
                <div className="loans-bank-transfer-summary">
                  <div className="loans-bank-transfer-head">
                    <div className="loans-repay-method-icon">
                      <Building2 size={18} />
                    </div>
                    <div>
                      <b>{bankTransferMethod.label}</b>
                      <span className="loans-admin-badge">Staff records payment</span>
                    </div>
                  </div>
                  <p>{bankTransferMethod.description}</p>
                </div>

                <button
                  type="button"
                  className={`loans-bank-details-toggle ${bankDetailsOpen ? 'open' : ''}`}
                  aria-expanded={bankDetailsOpen}
                  onClick={() => setBankDetailsOpen((open) => !open)}
                >
                  <span>{bankDetailsOpen ? 'Hide account details' : 'View account details'}</span>
                  <ChevronDown size={16} />
                </button>

                {bankDetailsOpen ? (
                  <LoanExternalPayDetails methodId={bankTransferMethod.id} loanReference={loan.reference} />
                ) : null}
              </article>
            ) : null}
          </div>
        </section>

        <div className="loans-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'schedule'}
            className={tab === 'schedule' ? 'active' : ''}
            onClick={() => setTab('schedule')}
          >
            Repayment schedule
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'payments'}
            className={tab === 'payments' ? 'active' : ''}
            onClick={() => setTab('payments')}
          >
            Payment history
          </button>
        </div>

        {tab === 'schedule' ? (
          <section className="loans-section">
            <div className="loans-section-head">
              <div>
                <h2>Installment plan</h2>
                <p>
                  {loan.paidInstallments || 0} of {loan.termMonths} installments paid
                </p>
              </div>
            </div>
            <LoanScheduleTable schedule={loan.schedule} />
          </section>
        ) : (
          <section className="loans-section">
            <div className="loans-section-head">
              <div>
                <h2>Payments received</h2>
                <p>Repayments recorded on this loan by MCS staff or from your Main Account</p>
              </div>
            </div>

            {loan.payments?.length ? (
              <ul className="loans-payments-list">
                {loan.payments.map((payment) => (
                  <li key={payment.id} className="loans-payment-item">
                    <div>
                      <Receipt size={16} />
                      <div>
                        <b>{formatUGX(payment.amount)}</b>
                        <span>
                          {payment.date} · {payment.method}
                        </span>
                      </div>
                    </div>
                    <small>
                      {payment.reference}
                      {payment.outstandingAfter !== undefined
                        ? ` · Outstanding after: ${formatUGX(payment.outstandingAfter)}`
                        : ''}
                    </small>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="loans-empty-inline">No payments recorded yet.</p>
            )}
          </section>
        )}
      </div>

      <RepayFromMainModal
        open={mainRepayOpen}
        onClose={() => setMainRepayOpen(false)}
        loan={loan}
        available={mainAccount?.available || 0}
        onSubmit={(amount) =>
          submitLoanRepayment({
            loanId: loan.id,
            amount,
            availableMain: mainAccount?.available || 0,
          })
        }
      />
    </AppShell>
  )
}
