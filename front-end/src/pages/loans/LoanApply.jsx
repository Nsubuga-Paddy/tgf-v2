import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Banknote, CalendarDays, CheckCircle2, ClipboardList, FileText, MessageSquareText } from 'lucide-react'
import AppShell from '../../components/layout/AppShell'
import LoansFlowNav, { LoansStepper } from '../../components/loans/LoansFlowNav'
import { useLoans } from '../../context/LoansContext'
import {
  LOAN_POLICY,
  LOAN_PURPOSES,
  LOAN_TERM_OPTIONS,
  MAX_BORROWING_LIMIT,
  loanDisbursementBreakdown,
} from '../../data/loansData'
import { formatUGX } from '../../utils/format'

const STEPS = [
  { id: 'details', label: 'Loan details' },
  { id: 'support', label: 'Your plan' },
  { id: 'review', label: 'Review' },
  { id: 'done', label: 'Submitted' },
]

const REPAYMENT_SOURCES = [
  { id: 'main_account', label: 'Main Account', detail: 'Primary repayments from MCS Main Account' },
  { id: 'main_account_and_salary', label: 'Main Account + salary', detail: 'Mix of portal and external income' },
  { id: 'business_income', label: 'Business income', detail: 'Repay from business cash flows' },
]

function parseAmount(raw) {
  const n = Number(String(raw).replace(/,/g, '').trim())
  return Number.isFinite(n) && n > 0 ? n : null
}

export default function LoanApply() {
  const navigate = useNavigate()
  const { eligibility, submitApplication } = useLoans()
  const [step, setStep] = useState(1)
  const [purpose, setPurpose] = useState('')
  const [amount, setAmount] = useState('')
  const [termMonths, setTermMonths] = useState(12)
  const [repaymentSource, setRepaymentSource] = useState('main_account')
  const [notes, setNotes] = useState('')
  const [submittedApp, setSubmittedApp] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const parsedAmount = parseAmount(amount)
  const maxAmount = Math.min(
    eligibility.estimatedMaxAmount || MAX_BORROWING_LIMIT,
    MAX_BORROWING_LIMIT,
  )

  const amountError = useMemo(() => {
    if (!parsedAmount) return ''
    if (parsedAmount < LOAN_POLICY.minAmount) {
      return `Minimum loan amount is ${formatUGX(LOAN_POLICY.minAmount)}.`
    }
    if (parsedAmount > maxAmount) {
      return `Amount exceeds your estimated limit of ${formatUGX(maxAmount)}.`
    }
    return ''
  }, [parsedAmount, maxAmount])

  const canStep1 = Boolean(purpose && parsedAmount && !amountError)
  const canStep2 = Boolean(repaymentSource)
  const selectedPurpose = LOAN_PURPOSES.find((p) => p.id === purpose)
  const feeBreakdown = loanDisbursementBreakdown(parsedAmount || 0)
  const monthlyRate = Number(eligibility.suggestedMonthlyRate || 0.015)
  const monthlyInterest = Math.round((parsedAmount || 0) * monthlyRate)
  const principalPart = termMonths > 0 ? Math.round((parsedAmount || 0) / termMonths) : 0
  const estimatedInstallment = parsedAmount ? principalPart + monthlyInterest : 0
  const estimatedTotalInterest = parsedAmount ? monthlyInterest * termMonths : 0
  const estimatedTotalRepayable = parsedAmount ? (parsedAmount || 0) + estimatedTotalInterest : 0

  const submit = async () => {
    if (submitting) return
    setSubmitting(true)
    setSubmitError('')
    try {
      const app = await submitApplication({
        purpose,
        amount: parsedAmount,
        termMonths,
        repaymentSource,
        notes,
      })
      setSubmittedApp(app)
      setStep(4)
    } catch (error) {
      setSubmitError(error.message || 'Could not submit loan application.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!eligibility.applyEnabled && step < 4) {
    return (
      <AppShell title="Apply for a loan">
        <div className="loans-page loans-flow-page">
          <LoansFlowNav />
          <div className="loans-empty-card">
            <FileText size={28} />
            <div>
              <b>Not eligible to apply yet</b>
              <p>Complete the eligibility requirements before submitting an application.</p>
              <Link to="/loans/eligibility" className="btn btn-primary btn-sm">
                Check eligibility
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell title="Apply for a loan">
      <div className="loans-page loans-flow-page">
        <LoansFlowNav />
        <LoansStepper steps={STEPS} current={step} />

        {step === 1 ? (
          <section className="loans-form-card loans-apply-details-card">
            <div className="loans-form-card-head">
              <div className="loans-form-card-icon">
                <ClipboardList size={20} />
              </div>
              <div>
                <h2>Loan details</h2>
                <p className="loans-form-lead">
                  Tell MCS how much you need, what it is for, and your preferred repayment period.
                </p>
              </div>
            </div>

            <div className="loans-apply-policy-strip">
              <div>
                <small>Minimum</small>
                <b>{formatUGX(LOAN_POLICY.minAmount)}</b>
              </div>
              <div>
                <small>Your assessed limit</small>
                <b>{formatUGX(maxAmount)}</b>
              </div>
              <div>
                <small>Maximum</small>
                <b>{formatUGX(MAX_BORROWING_LIMIT)}</b>
              </div>
              <div>
                <small>Interest</small>
                <b>{eligibility.rateDisplay || LOAN_POLICY.rateDisplay}</b>
              </div>
            </div>

            <div className="loans-apply-fields-panel">
              <label className="field loans-apply-purpose-field">
                <span>
                  <ClipboardList size={14} />
                  Purpose
                </span>
                <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
                  <option value="">Select purpose</option>
                  {LOAN_PURPOSES.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
                {selectedPurpose ? <small>{selectedPurpose.description}</small> : null}
              </label>

              <label className="field loans-apply-amount-field">
                <span>
                  <Banknote size={14} />
                  Amount requested
                </span>
                <div className="loans-apply-amount-input">
                  <span>UGX</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="e.g. 5000000"
                  />
                </div>
                <small>
                  Enter an amount between {formatUGX(LOAN_POLICY.minAmount)} and {formatUGX(maxAmount)}.
                </small>
                {amountError ? <span className="form-error">{amountError}</span> : null}
              </label>

              <div className="loans-apply-term-field">
                <span className="loans-apply-term-label">
                  <CalendarDays size={14} />
                  Repayment term
                </span>
                <div className="loans-apply-term-options">
                  {LOAN_TERM_OPTIONS.map((opt) => {
                    const selected = Number(termMonths) === opt.months
                    return (
                      <button
                        key={opt.months}
                        type="button"
                        className={`loans-apply-term-option ${selected ? 'selected' : ''}`}
                        onClick={() => setTermMonths(opt.months)}
                      >
                        <b>{opt.months}</b>
                        <span>months</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {parsedAmount && !amountError ? (
              <div className="loans-apply-fee-card">
                <div>
                  <small>Requested principal</small>
                  <b>{formatUGX(feeBreakdown.principal)}</b>
                  <span>This is the amount used for interest and repayment.</span>
                </div>
                <div>
                  <small>Insurance fee (1%)</small>
                  <b>{formatUGX(feeBreakdown.insuranceFee)}</b>
                  <span>Deducted once before disbursement.</span>
                </div>
                <div>
                  <small>Processing fee</small>
                  <b>{formatUGX(feeBreakdown.processingFee)}</b>
                  <span>Fixed loan processing charge.</span>
                </div>
                <div className="highlight">
                  <small>Net credited if approved</small>
                  <b>{formatUGX(feeBreakdown.netDisbursedAmount)}</b>
                  <span>Amount that will enter your Main Account.</span>
                </div>
              </div>
            ) : null}

            <div className="loans-flow-actions">
              <button type="button" className="btn btn-outline" onClick={() => navigate('/loans')}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!canStep1}
                onClick={() => setStep(2)}
              >
                Continue
              </button>
            </div>
          </section>
        ) : null}

        {step === 2 ? (
          <section className="loans-form-card loans-apply-details-card">
            <div className="loans-form-card-head">
              <div className="loans-form-card-icon">
                <MessageSquareText size={20} />
              </div>
              <div>
                <h2>Repayment plan</h2>
                <p className="loans-form-lead">
                  Share how you expect to repay and give the committee helpful context.
                </p>
              </div>
            </div>

            <div className="loans-apply-fields-panel">
              <div>
                <span className="loans-apply-term-label">Preferred repayment source</span>
                <div className="loans-radio-group loans-repayment-source-group">
                  {REPAYMENT_SOURCES.map((item) => (
                    <label key={item.id} className={`loans-radio-card ${repaymentSource === item.id ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="repaymentSource"
                        value={item.id}
                        checked={repaymentSource === item.id}
                        onChange={() => setRepaymentSource(item.id)}
                      />
                      <div>
                        <b>{item.label}</b>
                        <span>{item.detail}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <label className="field loans-apply-notes-field">
                <span>
                  <MessageSquareText size={14} />
                  Additional explanation
                </span>
                <textarea
                  rows={6}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Explain how the loan will be used and any supporting context."
                />
                <small>
                  Optional, but useful for the credit committee when reviewing your application.
                </small>
              </label>
            </div>

            <div className="loans-flow-actions">
              <button type="button" className="btn btn-outline" onClick={() => setStep(1)}>
                Back
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!canStep2}
                onClick={() => setStep(3)}
              >
                Review application
              </button>
            </div>
          </section>
        ) : null}

        {step === 3 ? (
          <section className="loans-form-card">
            <h2>Review & submit</h2>
            <p className="loans-form-lead">
              Your application will be reviewed by the MCS credit committee. You can track status
              online after submitting.
            </p>

            <dl className="loans-review-list">
              <div>
                <dt>Purpose</dt>
                <dd>{selectedPurpose?.label}</dd>
              </div>
              <div>
                <dt>Amount</dt>
                <dd>{formatUGX(parsedAmount)}</dd>
              </div>
              <div>
                <dt>Insurance fee (1%)</dt>
                <dd>{formatUGX(feeBreakdown.insuranceFee)}</dd>
              </div>
              <div>
                <dt>Processing fee</dt>
                <dd>{formatUGX(feeBreakdown.processingFee)}</dd>
              </div>
              <div>
                <dt>Net credited if approved</dt>
                <dd>{formatUGX(feeBreakdown.netDisbursedAmount)}</dd>
              </div>
              <div>
                <dt>Term</dt>
                <dd>{termMonths} months</dd>
              </div>
              <div>
                <dt>Estimated monthly installment</dt>
                <dd>{formatUGX(estimatedInstallment)}</dd>
              </div>
              <div>
                <dt>Estimated total repayable</dt>
                <dd>{formatUGX(estimatedTotalRepayable)}</dd>
              </div>
              <div>
                <dt>Repayment source</dt>
                <dd>{REPAYMENT_SOURCES.find((r) => r.id === repaymentSource)?.label}</dd>
              </div>
              {notes ? (
                <div>
                  <dt>Notes</dt>
                  <dd>{notes}</dd>
                </div>
              ) : null}
            </dl>

            <p className="loans-review-disclaimer">
              By submitting, you confirm the information is accurate. If approved, insurance and
              processing fees are deducted upfront from the approved amount, while repayment is
              calculated on the approved principal plus interest.
            </p>
            {submitError ? <p className="form-error">{submitError}</p> : null}

            <div className="loans-flow-actions">
              <button type="button" className="btn btn-outline" onClick={() => setStep(2)} disabled={submitting}>
                Back
              </button>
              <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
                {submitting ? 'Submitting…' : 'Submit application'}
              </button>
            </div>
          </section>
        ) : null}

        {step === 4 && submittedApp ? (
          <section className="loans-success-card">
            <CheckCircle2 size={40} className="loans-success-icon" />
            <h2>Application submitted</h2>
            <p>
              Reference <b>{submittedApp.reference}</b> has been sent to the credit committee. You
              will be notified when the status changes.
            </p>
            <dl className="loans-review-list compact">
              <div>
                <dt>Amount</dt>
                <dd>{formatUGX(submittedApp.amount)}</dd>
              </div>
              <div>
                <dt>Estimated deductions</dt>
                <dd>{formatUGX(submittedApp.fees?.totalDeductions || feeBreakdown.totalDeductions)}</dd>
              </div>
              <div>
                <dt>Net credited if approved</dt>
                <dd>
                  {formatUGX(
                    submittedApp.fees?.netDisbursedAmount || feeBreakdown.netDisbursedAmount,
                  )}
                </dd>
              </div>
              <div>
                <dt>Term</dt>
                <dd>{submittedApp.termMonths} months</dd>
              </div>
            </dl>
            <div className="loans-flow-actions">
              <Link to="/loans" className="btn btn-outline">
                Loans home
              </Link>
              <Link to={`/loans/applications/${submittedApp.id}`} className="btn btn-primary">
                Track application
              </Link>
            </div>
          </section>
        ) : null}
      </div>
    </AppShell>
  )
}
