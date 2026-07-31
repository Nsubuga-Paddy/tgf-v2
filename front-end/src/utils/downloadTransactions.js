function csvEscape(value) {
  const str = String(value ?? '')
  if (/[",\n]/.test(str)) return `"${str.replace(/"/g, '""')}"`
  return str
}

export function downloadTransactionsCsv(transactions, member) {
  const headers = ['Date', 'Title', 'Details', 'Direction', 'Amount (UGX)', 'Reference']
  const rows = transactions.map((tx) => {
    const when = tx.at ? new Date(tx.at) : null
    const dateValue =
      when && !Number.isNaN(when.getTime()) ? when.toISOString() : tx.meta || ''
    return [
      dateValue,
      tx.title || tx.label || 'Transaction',
      tx.meta || '',
      Number(tx.amount) >= 0 ? 'Credit' : 'Debit',
      Math.abs(Number(tx.amount) || 0),
      tx.ref ?? '',
    ]
  })

  const csv = [headers, ...rows].map((row) => row.map(csvEscape).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const stamp = new Date().toISOString().slice(0, 10)
  const account = (member?.accountNumber || 'main-account').replace(/[^\w-]+/g, '_')
  link.href = url
  link.download = `MCS_${account}_transactions_${stamp}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
