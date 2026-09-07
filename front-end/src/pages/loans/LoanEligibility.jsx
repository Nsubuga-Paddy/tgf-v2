import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle2, FileText, Loader2 } from 'lucide-react'
import AppShell from '../../components/layout/AppShell'
import LoansFlowNav from '../../components/loans/LoansFlowNav'
import { FactorIcon, eligibilityTone } from '../../components/loans/loanUi'
import { useLoans } from '../../context/LoansContext'
import { formatUGX } from '../../utils/format'
import { MAX_BORROWING_LIMIT } from '../../data/loansData'

export default function LoanEligibility() {
  const navigate = useNavigate()
  const { eligibility, runEligibilityCheck } = useLoans()
  const [checking, setChecking] = useState(true)
  const [result, setResult] = useState(null)

  useEffect(() => {
    let cancelled = false
    const timer = window.setTimeout(() => {
      runEligibilityCheck().then((next) => {
        if (!cancelled) {
          setResult(next)
          setChecking(false)
        }
      })
    }, 1400)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [runEligibilityCheck])

  const data = result || eligibility
  const tone = eligibilityTone(data.status)

  return (
    <AppShell title="Check loan eligibility">
      <div className="loans-page loans-flow-page">
        <LoansFlowNav />

        {checking ? (
          <div className="loans-checking-card">
            <Loader2 size={32} className="loans-spinner" />
            <h2>Checking your eligibility</h2>
            <p>Reviewing membership, shareholding, savings, and repayment history…</p>
          </div>
        ) : (
          <>
            <header className="loans-flow-hero">
              <CheckCircle2 size={28} className={`loans-flow-hero-icon ${tone}`} />
              <div>
                <h2>{data.statusLabel}</h2>
                <p>{data.summary}</p>
              </div>
            </header>

            {data.estimatedMaxAmount != null ? (
              <div className="loans-limit-banner">
                <small>{data.estimatedMaxLabel}</small>
                <strong>{formatUGX(data.estimatedMaxAmount)}</strong>
                <span className="loans-limit-cap-banner">
                  Maximum per member: {formatUGX(MAX_BORROWING_LIMIT)}
                </span>
              </div>
            ) : null}

            <section className="loans-section">
              <div className="loans-section-head">
                <div>
                  <h2>Eligibility factors</h2>
                  <p>
                    {data.isStaff
                      ? `Staff checklist · Interest 1% per month on principal`
                      : 'What MCS considers when assessing loan applications'}
                  </p>
                </div>
              </div>
              <ul className="loans-factors loans-factors-flow">
                {data.factors.map((factor) => (
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
            </section>

            {!data.applyEnabled && data.blockers?.length ? (
              <section className="loans-eligibility-blockers" aria-labelledby="loan-blockers-title">
                <div>
                  <AlertCircle size={18} />
                  <h2 id="loan-blockers-title">Why you cannot apply yet</h2>
                </div>
                <ul>
                  {data.blockers.map((blocker) => (
                    <li key={blocker.id}>
                      <b>{blocker.label}</b>
                      <span>{blocker.detail}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <div className="loans-flow-actions">
              <button type="button" className="btn btn-outline" onClick={() => navigate('/loans')}>
                Back to loans home
              </button>
              {data.applyEnabled ? (
                <Link to="/loans/apply" className="btn btn-primary">
                  <FileText size={15} />
                  Continue to application
                </Link>
              ) : (
                <Link to={data.ctaTo || '/profile'} className="btn btn-primary">
                  {data.ctaLabel || 'Complete required items'}
                </Link>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}
