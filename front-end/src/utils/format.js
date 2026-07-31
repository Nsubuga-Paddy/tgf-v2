export function formatUGX(amount) {
  return new Intl.NumberFormat('en-UG', {
    style: 'currency',
    currency: 'UGX',
    maximumFractionDigits: 0,
  }).format(Math.round(Math.abs(amount)))
}

export function formatSignedUGX(amount) {
  const sign = amount >= 0 ? '+' : '−'
  return `${sign}${formatUGX(amount)}`
}

export function formatCompactUGX(amount) {
  const n = Math.abs(amount)
  if (n >= 1_000_000) return `UGX ${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`
  if (n >= 1_000) return `UGX ${(n / 1_000).toFixed(0)}K`
  return formatUGX(n)
}

export function greetingForNow(date = new Date()) {
  const h = date.getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export function formatTxDate(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return String(iso)
  return new Intl.DateTimeFormat('en-UG', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
