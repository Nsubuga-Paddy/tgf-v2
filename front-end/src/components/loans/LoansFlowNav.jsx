import { Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'

export default function LoansFlowNav({ backTo = '/loans', backLabel = 'Back to Member Loans', children }) {
  return (
    <div className="loans-flow-nav">
      <Link to={backTo} className="loans-back-link">
        <ChevronLeft size={16} />
        {backLabel}
      </Link>
      {children}
    </div>
  )
}

export function LoansStepper({ steps, current }) {
  return (
    <ol className="loans-stepper" aria-label="Progress">
      {steps.map((step, index) => {
        const stepNum = index + 1
        const done = stepNum < current
        const active = stepNum === current
        return (
          <li
            key={step.id}
            className={`loans-step ${done ? 'done' : ''} ${active ? 'active' : ''}`}
          >
            <span className="loans-step-dot">{done ? '✓' : stepNum}</span>
            <span className="loans-step-label">{step.label}</span>
          </li>
        )
      })}
    </ol>
  )
}
