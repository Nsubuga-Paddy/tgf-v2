import { MCS_LOAN_PAYMENT_DETAILS } from '../../data/loansData'

export default function LoanExternalPayDetails({ methodId, loanReference }) {
  if (methodId !== 'bank_transfer') return null

  return (
    <dl className="loans-mcs-pay-details loans-mcs-pay-details-inline">
      <div>
        <dt>Account name</dt>
        <dd>{MCS_LOAN_PAYMENT_DETAILS.accountName}</dd>
      </div>
      <div>
        <dt>Account number</dt>
        <dd>{MCS_LOAN_PAYMENT_DETAILS.bankAccount}</dd>
      </div>
      <div>
        <dt>Bank</dt>
        <dd>{MCS_LOAN_PAYMENT_DETAILS.bankName}</dd>
      </div>
      <div>
        <dt>Branch</dt>
        <dd>{MCS_LOAN_PAYMENT_DETAILS.branch}</dd>
      </div>
      {loanReference ? (
        <div>
          <dt>Your loan reference</dt>
          <dd>{loanReference}</dd>
        </div>
      ) : null}
    </dl>
  )
}
