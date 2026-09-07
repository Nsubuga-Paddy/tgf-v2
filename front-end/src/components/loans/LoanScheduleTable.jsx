import { LoanStatusBadge } from './loanUi'

export default function LoanScheduleTable({ schedule }) {
  if (!schedule?.length) {
    return <p className="loans-empty-inline">No repayment schedule available.</p>
  }

  return (
    <div className="loans-table-wrap">
      <table className="loans-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Due date</th>
            <th>Principal</th>
            <th>Interest</th>
            <th>Installment</th>
            <th>Balance after</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {schedule.map((row) => (
            <tr key={row.installment} className={`schedule-row-${row.status}`}>
              <td>{row.installment}</td>
              <td>{row.dueDate}</td>
              <td>UGX {row.principal.toLocaleString()}</td>
              <td>UGX {row.interest.toLocaleString()}</td>
              <td>
                <b>UGX {row.total.toLocaleString()}</b>
              </td>
              <td>UGX {row.balanceAfter.toLocaleString()}</td>
              <td>
                <LoanStatusBadge status={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
