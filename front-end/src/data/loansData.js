/**
 * Loan demo data and helpers for the member Loans frontend flow.
 * Replace with API payloads when the loans backend is wired up.
 */

export const MAX_BORROWING_LIMIT = 10_000_000
export const LOAN_INSURANCE_FEE_RATE = 0.01
export const LOAN_PROCESSING_FEE = 20_000

export const LOAN_POLICY = {
  rateDisplay: '1.5% per month on principal',
  termDisplay: '3 – 24 months',
  minAmount: 100_000,
  maxAmount: MAX_BORROWING_LIMIT,
  insuranceFeeRate: LOAN_INSURANCE_FEE_RATE,
  processingFee: LOAN_PROCESSING_FEE,
  basis:
    'Loans are assessed against your savings history, shareholding, and cooperative standing. The maximum borrowing limit is UGX 10,000,000. Interest is charged monthly on the principal amount. On approval, 1% insurance and a UGX 20,000 processing fee are deducted before the net amount is credited to Main Account.',
  points: [
    'Repay from available Main Account balance.',
    'Pay by bank transfer to the MCS account — then share your receipt with MCS staff to update your loan.',
    'Interest and schedules are shown on each active loan.',
    'Overdue loans may affect future eligibility until cleared.',
  ],
}

export function loanDisbursementBreakdown(amount) {
  const principal = Math.max(0, Math.round(Number(amount) || 0))
  const insuranceFee = Math.round(principal * LOAN_INSURANCE_FEE_RATE)
  const processingFee = principal > 0 ? LOAN_PROCESSING_FEE : 0
  const totalDeductions = insuranceFee + processingFee
  const netDisbursedAmount = Math.max(0, principal - totalDeductions)
  return {
    principal,
    insuranceFee,
    processingFee,
    totalDeductions,
    netDisbursedAmount,
  }
}

/** How members can repay an active MCS loan. */
export const LOAN_REPAYMENT_METHODS = [
  {
    id: 'main_account',
    label: 'Main Account',
    shortLabel: 'Main Account',
    description: 'Transfer from your MCS Main Account balance.',
    memberInitiated: true,
    cta: 'Repay now',
  },
  {
    id: 'bank_transfer',
    label: 'Bank transfer',
    shortLabel: 'Bank transfer',
    description:
      'Transfer to the MCS bank account below. After payment, share your bank receipt with MCS staff. They will verify the deposit and update your loan balance.',
    memberInitiated: false,
  },
]

export const MCS_LOAN_PAYMENT_DETAILS = {
  accountName: 'MUSHANA FINANCE',
  bankAccount: '01071118922629',
  bankName: 'DFCU Bank',
  branch: 'Jinja Road',
}

export const LOAN_PURPOSES = [
  { id: 'business', label: 'Business expansion', description: 'Stock, equipment, or working capital' },
  { id: 'education', label: 'Education', description: 'School fees or training costs' },
  { id: 'medical', label: 'Medical / emergency', description: 'Urgent health or family needs' },
  { id: 'housing', label: 'Housing', description: 'Rent, construction, or improvements' },
  { id: 'agriculture', label: 'Agriculture', description: 'Farm inputs, livestock, or harvest support' },
  { id: 'other', label: 'Other', description: 'Explain in your application notes' },
]

export const LOAN_TERM_OPTIONS = [
  { months: 3, label: '3 months' },
  { months: 6, label: '6 months' },
  { months: 12, label: '12 months' },
  { months: 18, label: '18 months' },
  { months: 24, label: '24 months' },
]

export const APPLICATION_STATUS_LABELS = {
  submitted: 'Submitted',
  under_review: 'Under review',
  approved: 'Approved',
  rejected: 'Rejected',
  disbursed: 'Disbursed',
}

export const APPLICATION_STATUS_ORDER = [
  'submitted',
  'under_review',
  'approved',
  'disbursed',
]

export function purposeLabel(purposeId) {
  return LOAN_PURPOSES.find((p) => p.id === purposeId)?.label || purposeId
}

export function buildDemoSchedule({
  principal,
  months,
  monthlyRate = 0.015,
  startDate = '2026-03-01',
  paidCount = 0,
}) {
  const p = Number(principal) || 0
  const n = Number(months) || 12
  const monthlyInterest = p * monthlyRate
  const principalPart = p / n
  const installment = principalPart + monthlyInterest
  const rows = []
  let balance = p + monthlyInterest * n
  const [y, m, d] = startDate.split('-').map(Number)
  for (let i = 1; i <= n; i += 1) {
    const principalForRow = i === n ? p - principalPart * (n - 1) : principalPart
    const total = principalForRow + monthlyInterest
    balance = Math.max(0, balance - total)
    const due = new Date(y, m - 1 + i, d || 1)
    const dueLabel = due.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
    let status = 'upcoming'
    if (i <= paidCount) status = 'paid'
    else if (i === paidCount + 1) status = 'due'
    rows.push({
      installment: i,
      dueDate: dueLabel,
      dueIso: due.toISOString(),
      principal: Math.round(principalForRow),
      interest: Math.round(monthlyInterest),
      total: Math.round(total),
      balanceAfter: Math.round(balance),
      status,
    })
  }
  return rows
}

export const DEMO_ACTIVE_LOANS = [
  {
    id: 'loan-business-001',
    reference: 'LN-2026-0042',
    purpose: 'business',
    purposeLabel: 'Business expansion',
    status: 'active',
    principal: 8_000_000,
    outstanding: 5_506_665,
    rateDisplay: '1.5% per month on principal',
    monthlyRate: 0.015,
    termMonths: 12,
    disbursedDate: '1 Feb 2026',
    nextDueDate: '1 Aug 2026',
    nextDueAmount: 786_667,
    installmentAmount: 786_667,
    paidInstallments: 5,
    schedule: buildDemoSchedule({
      principal: 8_000_000,
      months: 12,
      startDate: '2026-03-01',
      paidCount: 5,
    }),
    payments: [
      {
        id: 'pay-1',
        date: '1 Mar 2026',
        amount: 786_667,
        method: 'Main Account',
        reference: 'RP-8A2F1C',
        status: 'completed',
      },
      {
        id: 'pay-2',
        date: '1 Apr 2026',
        amount: 786_667,
        method: 'Bank transfer',
        reference: 'RP-9B3E2D',
        status: 'completed',
      },
      {
        id: 'pay-3',
        date: '1 May 2026',
        amount: 786_667,
        method: 'Main Account',
        reference: 'RP-1C4F3E',
        status: 'completed',
      },
      {
        id: 'pay-4',
        date: '1 Jun 2026',
        amount: 786_667,
        method: 'Main Account',
        reference: 'RP-2D5A4F',
        status: 'completed',
      },
      {
        id: 'pay-5',
        date: '1 Jul 2026',
        amount: 786_667,
        method: 'Bank transfer',
        reference: 'RP-3E6B5A',
        status: 'completed',
      },
    ],
  },
]

export const DEMO_CLOSED_LOANS = [
  {
    id: 'loan-education-2019',
    reference: 'LN-2019-0118',
    purpose: 'education',
    purposeLabel: 'Education',
    closedDate: '15 Dec 2020',
    principal: 2_500_000,
    totalRepaid: 2_875_000,
  },
]

export const DEMO_APPLICATIONS = [
  {
    id: 'app-demo-review',
    reference: 'LA-2026-0091',
    purpose: 'housing',
    purposeLabel: 'Housing',
    amount: 8_000_000,
    termMonths: 18,
    status: 'under_review',
    submittedAt: '2026-08-20T10:30:00',
    notes: 'Top-up for rental deposit and minor renovations.',
    repaymentSource: 'main_account_and_salary',
    timeline: [
      { status: 'submitted', at: '2026-08-20T10:30:00', note: 'Application received online.' },
      { status: 'under_review', at: '2026-08-21T09:00:00', note: 'Assigned to credit committee.' },
    ],
    committeeNote: '',
  },
]

export function computeDemoEligibility({
  isVerified,
  profile,
  shareholding,
  myProjects,
  mainAccount,
  activeLoans,
}) {
  const missingPersonal = []
  if (!profile?.firstName) missingPersonal.push('first name')
  if (!profile?.lastName) missingPersonal.push('last name')
  if (!profile?.email) missingPersonal.push('email')
  if (!profile?.whatsapp) missingPersonal.push('WhatsApp number')
  if (!profile?.nationalId) missingPersonal.push('National ID')
  if (!profile?.birthdate) missingPersonal.push('date of birth')
  const personalReady = missingPersonal.length === 0
  const bankReady = Boolean(
    profile?.bankName && profile?.bankAccountNumber && profile?.bankAccountName,
  )
  const hasActiveProjects = (myProjects?.length || 0) > 0
  const hasShares = Number(shareholding?.portfolioValue || 0) > 0
  const qualifyingSavings = 1_200_000
  const hasSavings =
    Number(mainAccount?.posted || 0) >= qualifyingSavings ||
    (myProjects || []).some((project) => Number(project.invested || 0) >= qualifyingSavings)
  const hasOverdue = (activeLoans || []).some((l) => l.status === 'overdue')
  const hardBlockers = []
  if (!isVerified) {
    hardBlockers.push({
      id: 'membership',
      label: 'Platform verification is pending',
      detail: 'Your MCS account must be verified before you can submit a loan application.',
      ctaLabel: 'View verification status',
      ctaTo: '/verification-pending',
    })
  }
  if (!personalReady) {
    hardBlockers.push({
      id: 'personal',
      label: 'Complete your personal details',
      detail: `Missing: ${missingPersonal.join(', ')}.`,
      ctaLabel: 'Complete your profile',
      ctaTo: '/profile',
    })
  }
  if (!bankReady) {
    hardBlockers.push({
      id: 'bank',
      label: 'Add your bank account details',
      detail: 'Bank name, account number, and account name are required for loan disbursement records.',
      ctaLabel: 'Complete bank details',
      ctaTo: '/profile',
    })
  }
  if (!hasActiveProjects) {
    hardBlockers.push({
      id: 'active_projects',
      label: 'No active MCS project access',
      detail: 'You need at least one active MCS project/access relationship before applying.',
      ctaLabel: 'View project access',
      ctaTo: '/profile',
    })
  }

  const factors = [
    {
      id: 'membership',
      label: 'Verified MCS membership',
      met: Boolean(isVerified),
      detail: isVerified ? 'Your account is verified' : 'Complete verification first',
    },
    {
      id: 'personal',
      label: 'Complete personal details',
      met: personalReady,
      detail: personalReady ? 'Required personal details are complete' : `Missing: ${missingPersonal.join(', ')}`,
    },
    {
      id: 'bank',
      label: 'Bank account details',
      met: bankReady,
      detail: bankReady ? 'Bank details on file for disbursement' : 'Add bank name, account number, and account name',
    },
    {
      id: 'active_projects',
      label: 'Active MCS project access',
      met: hasActiveProjects,
      detail: hasActiveProjects ? 'You have active MCS project access' : 'Join or request access to an MCS project',
    },
    {
      id: 'shares',
      label: 'Cooperative shareholding',
      met: hasShares,
      detail: hasShares
        ? `Portfolio value ${formatCompact(shareholding.portfolioValue)}`
        : 'No shareholding on record yet',
    },
    {
      id: 'savings',
      label: 'Savings history and balance',
      met: hasSavings,
      detail: hasSavings
        ? 'You meet the UGX 1,200,000 savings requirement'
        : 'Requires about 1 year of savings and at least UGX 1,200,000',
    },
    {
      id: 'repayment',
      label: 'Good repayment history',
      met: !hasOverdue,
      detail: hasOverdue ? 'Clear overdue loan payments first' : 'No overdue MCS loans',
    },
    {
      id: 'profile',
      label: 'Committee review',
      met: null,
      detail: 'Savings, shareholding, and repayment history guide committee decisions.',
    },
  ]

  const coreReady = hardBlockers.length === 0
  let status = 'not_eligible'
  let statusLabel = 'Not eligible yet'
  let applyEnabled = false

  if (coreReady && hasShares && hasSavings && !hasOverdue) {
    status = 'eligible'
    statusLabel = 'Eligible to apply'
    applyEnabled = true
  } else if (coreReady) {
    status = 'may_qualify'
    statusLabel = 'You may apply — committee review required'
    applyEnabled = true
  } else if (isVerified) {
    status = 'not_eligible'
    statusLabel = 'Not ready to apply'
    applyEnabled = false
  }

  const shareCap = Number(shareholding?.portfolioValue || 0) * 0.6
  const savingsCap = Number(mainAccount?.posted || 0) + 2_000_000
  const rawCap = Math.max(shareCap, savingsCap, 3_000_000)
  const estimatedMaxAmount = Math.max(0, Math.min(MAX_BORROWING_LIMIT, Math.round(rawCap)))
  const firstBlocker = hardBlockers[0]

  return {
    status,
    statusLabel,
    summary:
      status === 'eligible'
        ? `You meet MCS lending criteria. You may apply for up to ${formatCompact(MAX_BORROWING_LIMIT)} subject to committee approval.`
        : status === 'may_qualify'
          ? 'You can submit a loan application. Savings, shareholding, and repayment history will be reviewed by the committee.'
          : 'Complete the required items below before applying for cooperative credit.',
    estimatedMaxAmount:
      estimatedMaxAmount > 0 ? Math.min(estimatedMaxAmount, MAX_BORROWING_LIMIT) : null,
    estimatedMaxLabel: 'Maximum borrowing limit',
    applyEnabled,
    applyMessage:
      applyEnabled
        ? 'Submit an application for credit committee review.'
        : 'Complete the hard-blocking items before applying.',
    blockers: hardBlockers,
    ctaLabel: firstBlocker?.ctaLabel || 'Continue to application',
    ctaTo: firstBlocker?.ctaTo || '/loans/apply',
    factors,
    checkedAt: new Date().toISOString(),
  }
}

function formatCompact(amount) {
  const n = Number(amount) || 0
  return `UGX ${n.toLocaleString('en-UG', { maximumFractionDigits: 0 })}`
}

export function repaymentMethodLabel(methodId) {
  return LOAN_REPAYMENT_METHODS.find((m) => m.id === methodId)?.label || methodId
}

export function applyRepaymentToLoan(loan, amount, { methodLabel, reference, status, dateLabel }) {
  const parsed = Number(amount) || 0
  const instant = status === 'completed'
  const newOutstanding = instant ? Math.max(0, loan.outstanding - parsed) : loan.outstanding
  let paidInstallments = loan.paidInstallments || 0
  let schedule = loan.schedule

  if (instant && parsed >= (loan.installmentAmount || loan.nextDueAmount || 0) * 0.95) {
    paidInstallments += 1
    schedule = buildDemoSchedule({
      principal: loan.principal,
      months: loan.termMonths,
      monthlyRate: loan.monthlyRate || 0.015,
      startDate: '2026-03-01',
      paidCount: paidInstallments,
    })
  }

  const nextDueRow = schedule?.find((row) => row.status === 'due')
  const payment = {
    id: `pay-${Date.now()}`,
    date: dateLabel,
    amount: parsed,
    method: methodLabel,
    reference,
    status,
  }

  return {
    ...loan,
    outstanding: newOutstanding,
    paidInstallments,
    schedule,
    nextDueDate: nextDueRow?.dueDate || loan.nextDueDate,
    nextDueAmount: nextDueRow?.total || loan.nextDueAmount,
    status: newOutstanding <= 0 ? 'closed' : loan.status,
    payments: [payment, ...(loan.payments || [])],
  }
}

export function generateApplicationReference() {
  const n = Math.floor(1000 + Math.random() * 9000)
  return `LA-2026-${n}`
}

export function generateRepaymentReference() {
  return `RP-${Math.random().toString(36).slice(2, 8).toUpperCase()}`
}
