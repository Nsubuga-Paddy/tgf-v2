/** Commercial Goat Farming — member demo data */

export const CGF_ACCOUNT = {
  accountNumber: 'MCSTGF-NS0042',
}

export const CGF_SUMMARY = {
  totalGoats: 3,
  totalInvested: 1_800_000,
  totalPaid: 1_800_000,
  totalBalance: 0,
  totalExpectedKids: 6,
  nextMaturityDate: '14 Jul 2027',
}

/** Farm holdings (UserFarmAccount-style) */
export const CGF_FARM_ACCOUNTS = [
  {
    id: 'fa1',
    farmName: 'Namayumba Goat Farm',
    farmLocation: 'Wakiso, Uganda',
    currentGoats: 3,
    expectedKids: 6,
    createdAt: '2026-05-14',
  },
]

export const CGF_PURCHASES = [
  {
    id: 1,
    farmName: 'Namayumba Goat Farm',
    packageName: 'Standard Package',
    totalAmount: 1_800_000,
    amountPaid: 1_800_000,
    balanceDue: 0,
    status: 'allocated',
    statusLabel: 'Goats Allocated',
    goatsAllocated: 3,
    goatCount: 3,
    purchaseDate: '14 May 2026',
    kidsPerGoat: 2,
  },
]

export const CGF_PAYMENTS = [
  {
    id: 101,
    paymentDate: '14 May 2026',
    receiptNumber: 'RCPT-20260514-CGF001',
    amount: 1_200_000,
    paymentMethod: 'Bank transfer',
    packageName: 'Standard Package',
    farmName: 'Namayumba Goat Farm',
    purchaseStatus: 'allocated',
    notes: 'Initial deposit for Standard Package',
    processedBy: 'System',
    processedDate: '14 May 2026',
  },
  {
    id: 102,
    paymentDate: '28 May 2026',
    receiptNumber: 'RCPT-20260528-CGF002',
    amount: 600_000,
    paymentMethod: 'Mobile money',
    packageName: 'Standard Package',
    farmName: 'Namayumba Goat Farm',
    purchaseStatus: 'allocated',
    notes: 'Balance payment — goats allocated',
    processedBy: 'System',
    processedDate: '28 May 2026',
  },
]

export const CGF_PACKAGES = [
  {
    id: 'starter',
    name: 'Starter Package',
    icon: 'seedling',
    goatCount: 2,
    price: 2_200_000,
    kidsPerGoat: 2,
    summary: 'Get 6 goats in 14 months (2 original + 4 kids)',
    features: [
      '2 Female goats (UGX 600,000 each)',
      'Expected 4 kids born in 5 months',
      'Professional farm management',
      'Monthly health checkups',
      'Regular progress reports',
    ],
  },
  {
    id: 'premium',
    name: 'Premium Package',
    icon: 'crown',
    goatCount: 4,
    price: 3_400_000,
    kidsPerGoat: 2,
    summary: 'Get 12 goats in 14 months (4 original + 8 kids)',
    features: [
      '4 Female goats (UGX 600,000 each)',
      'Expected 8 kids born in 5 months',
      'Professional farm management',
      'Weekly health checkups',
      'Detailed progress reports',
      'Priority support',
    ],
  },
]

export const CGF_CURRENT_INVESTMENTS = CGF_PURCHASES.map((p) => ({
  id: p.id,
  packageName: p.packageName,
  investmentDate: p.purchaseDate,
  amount: p.totalAmount,
  status: p.statusLabel,
  statusColor: p.status === 'allocated' ? 'success' : p.status === 'partial' ? 'warning' : 'info',
  expectedReturns: p.goatCount + p.goatCount * p.kidsPerGoat,
}))

export const CGF_BREEDING_INFO = {
  cycle: 'Set per package (14 or 18 months)',
  kidsPerBirth: 'Configurable per package (default 2 per goat)',
  gestation: '5 months',
  maturityAge: 'Based on the package cycle duration',
  expectedRoi: 'Kids can be sold or kept for breeding',
  nextGeneration: 'Maturity follows the package terms',
}

export const MARKET_PRICE_PER_KID = 400_000
export const KIDS_PER_GOAT_PER_YEAR = 3

/** Maturity from purchase/start ISO date + 425 days (~14 months). */
export const CGF_CYCLE_DAYS = 425

export function maturityFromPurchaseDate(startIso, asOf = new Date()) {
  if (!startIso) {
    return { dateLabel: '—', statusLabel: 'No cycle start', tone: 'secondary', progressPct: 0 }
  }
  const start = new Date(startIso)
  if (Number.isNaN(start.getTime())) {
    return { dateLabel: '—', statusLabel: 'Invalid date', tone: 'secondary', progressPct: 0 }
  }
  const matures = new Date(start.getTime() + CGF_CYCLE_DAYS * 24 * 60 * 60 * 1000)
  const options = { year: 'numeric', month: 'short', day: 'numeric' }
  const dateLabel = matures.toLocaleDateString('en-US', options)
  const elapsedMs = asOf.getTime() - start.getTime()
  const progressPct = Math.max(
    0,
    Math.min(100, Math.round((elapsedMs / (CGF_CYCLE_DAYS * 24 * 60 * 60 * 1000)) * 100)),
  )

  if (matures <= asOf) {
    return {
      dateLabel,
      statusLabel: 'Cycle complete',
      tone: 'success',
      progressPct: 100,
    }
  }

  const daysDiff = Math.ceil((matures.getTime() - asOf.getTime()) / (1000 * 3600 * 24))
  if (daysDiff > 365) {
    const years = Math.floor(daysDiff / 365)
    const months = Math.floor((daysDiff % 365) / 30)
    return {
      dateLabel,
      statusLabel: `${years} year${years > 1 ? 's' : ''}${
        months > 0 ? ` ${months} month${months > 1 ? 's' : ''}` : ''
      } remaining`,
      tone: 'warning',
      progressPct,
    }
  }
  if (daysDiff > 30) {
    const months = Math.floor(daysDiff / 30)
    const days = daysDiff % 30
    return {
      dateLabel,
      statusLabel: `${months} month${months > 1 ? 's' : ''}${
        days > 0 ? ` ${days} day${days > 1 ? 's' : ''}` : ''
      } remaining`,
      tone: 'warning',
      progressPct,
    }
  }
  return {
    dateLabel,
    statusLabel: `${daysDiff} day${daysDiff > 1 ? 's' : ''} remaining`,
    tone: 'info',
    progressPct,
  }
}

/** @deprecated Prefer maturityFromPurchaseDate — kept for older call sites. */
export function kiddingFromCreated(createdAtIso, asOf = new Date()) {
  return maturityFromPurchaseDate(createdAtIso, asOf)
}

export function purchaseStatusBadge(status) {
  if (status === 'settled') return 'info'
  if (status === 'allocated') return 'success'
  if (status === 'paid') return 'info'
  if (status === 'partial') return 'warning'
  return 'secondary'
}

export function transactionFromPayment(payment) {
  if (payment.entryType === 'transfer_to_main') {
    return {
      id: payment.id,
      date: payment.paymentDate,
      receiptNo: payment.receiptNumber,
      type: 'Transfer to Main Account',
      typeTone: 'info',
      description: payment.notes || `Matured CGF settlement - ${payment.farmName}`,
      amount: payment.amount,
      status: 'Completed',
      statusTone: 'success',
      paymentMethod: payment.paymentMethod,
      notes: payment.notes,
      processedBy: payment.processedBy,
      processedDate: payment.processedDate,
      reference: payment.receiptNumber,
    }
  }

  let status = 'Pending'
  let statusTone = 'info'
  if (payment.purchaseStatus === 'allocated' || payment.purchaseStatus === 'paid') {
    status = 'Completed'
    statusTone = 'success'
  } else if (payment.purchaseStatus === 'partial') {
    status = 'Partial'
    statusTone = 'warning'
  }
  return {
    id: payment.id,
    date: payment.paymentDate,
    receiptNo: payment.receiptNumber,
    type: 'Investment Payment',
    typeTone: 'success',
    description: `Payment for ${payment.packageName} - ${payment.farmName}`,
    amount: payment.amount,
    status,
    statusTone,
    paymentMethod: payment.paymentMethod,
    notes: payment.notes,
    processedBy: payment.processedBy,
    processedDate: payment.processedDate,
    reference: payment.receiptNumber,
  }
}
