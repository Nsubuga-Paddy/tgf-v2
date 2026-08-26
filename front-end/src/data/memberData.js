/** Demo member — personal portfolio only (not group totals). */

export const MEMBER = {
  firstName: 'Sarah',
  fullName: 'Sarah Nakato',
  initials: 'SN',
  accountNumber: 'MCSTGF-NS0042',
  isVerified: true,
  isShareholder: true,
}

/** Main MCS bank account for this member */
export const MAIN_ACCOUNT = {
  available: 3_450_000,
  posted: 3_850_000,
  pendingWithdrawal: 500_000,
}

/**
 * Lifetime MCS activity for this member (all-time, not current balances).
 * totalInvestedEver = everything they have ever put into MCS.
 * totalWithdrawnEver = everything they have ever withdrawn out of MCS.
 */
export const LIFETIME = {
  totalInvestedEver: 28_650_000,
  totalWithdrawnEver: 4_200_000,
}

/** Cooperative shares held by this member */
export const SHAREHOLDING = {
  sharesHeld: 50,
  portfolioValue: 5_000_000,
  dividendEligible: 48,
  expectedDividend: 720_000,
  dividendRate: '8%',
  certificateStatus: 'Issued',
  certificateNumber: 'MCS-SH-0042',
  memberSince: 2021,
  electionOpen: true,
  electionDeadline: '31 Dec 2026',
  equityBadge: 'Shareholder',
  tier: 'Elite Tier',
  totalDividendsEarned: 1_370_000,
}

export const SHARE_STATEMENT = [
  {
    id: 'sh1',
    title: 'Purchased 10 shares',
    meta: '14 Mar 2024',
    ref: 'SH-000042',
    amount: -1_000_000,
    category: 'invest',
  },
  {
    id: 'sh2',
    title: '2024 dividend paid',
    meta: 'Credited to main account · 18 Feb 2025',
    ref: 'DIV-000041',
    amount: 720_000,
    category: 'in',
  },
  {
    id: 'sh3',
    title: '2025 dividend paid',
    meta: 'Credited to main account · 20 Feb 2026',
    ref: 'DIV-000077',
    amount: 650_000,
    category: 'in',
  },
]

/** Open requests awaiting admin action for this member */
export const PENDING_REQUESTS = [
  { id: 'pr1', label: 'Main account withdrawal', detail: 'UGX 500,000' },
  { id: 'pr3', label: 'Transfer to main · 52WSC', detail: 'UGX 310,000 matured' },
]

/**
 * Projects this member is enrolled in.
 * Each has its own maturity / cycle line — personal figures only.
 */
/**
 * Active (not matured) projects — dashboard shows Open only.
 * Contribution / transfer controls live on the project page.
 */
export const MY_PROJECTS = [
  {
    id: '52wsc',
    name: '52 Weeks Saving Challenge',
    shortName: '52WSC',
    icon: 'piggy',
    invested: 2_860_000,
    status: 'Active',
    cycleLine: 'Week 31 of 52 · matures Dec 2026',
    progress: 60,
    stats: [
      { label: 'This year', value: 'UGX 2.86M' },
      { label: 'Interest', value: '15% p.a.' },
    ],
  },
  {
    id: 'gwc',
    name: 'Generational Wealth Creation',
    shortName: 'GWC',
    icon: 'heart',
    invested: 5_000_000,
    status: 'Active',
    cycleLine: '2 deposits · next maturity 15 Sep 2026',
    progress: 72,
    stats: [
      { label: 'Principal', value: 'UGX 5.0M' },
      { label: 'Accrued', value: 'UGX 412K' },
    ],
  },
  {
    id: 'cgf',
    name: 'Commercial Goat Farming',
    shortName: 'CGF',
    icon: 'goat',
    invested: 1_800_000,
    status: 'In cycle',
    cycleLine: '3 goats · cycle ends ~14 months',
    progress: 45,
    stats: [
      { label: 'Goats', value: '3' },
      { label: 'Expected kids', value: '4–6' },
    ],
  },
  {
    id: 'rep',
    name: 'Real Estate Projects',
    shortName: 'REP',
    icon: 'building',
    invested: 8_000_000,
    status: 'Active',
    cycleLine: 'Namayumba plot · multi-year hold',
    progress: 38,
    stats: [
      { label: 'Paid in', value: 'UGX 8.0M' },
      { label: 'Projects', value: '1' },
    ],
  },
]

/**
 * Take-action options mirror MCS profile.html project action buttons.
 * Cash-out from project cycles uses transfer to main (withdraw is main-account only).
 */
export const PROJECT_TAKE_ACTIONS = {
  '52wsc': [
    {
      id: 'start-new-cycle',
      label: 'Start new cycle with BF',
      description:
        'Use leftover balance brought forward as the opening balance for your next 52-week cycle',
      icon: 'retain',
    },
    {
      id: 'transfer-main',
      label: 'Transfer everything to main account',
      description:
        'Move amount saved + interest earned + balance brought forward to your Main Account',
      icon: 'transfer',
    },
  ],
  gwc: [
    {
      id: 'open-gwc',
      label: 'Open GWC dashboard',
      description: 'View deposits, the interest ledger, and maturity details',
      icon: 'dashboard',
    },
    {
      id: 'redeem-interest',
      label: 'Redeem interest',
      description:
        'Transfer redeemable monthly interest to Main Account (full or partial amount)',
      icon: 'transfer',
    },
  ],
  cgf: [
    {
      id: 'transfer-main',
      label: 'Transfer money to main account for withdrawal',
      description:
        'Cash out the matured portion and credit your Main Account so you can withdraw',
      icon: 'transfer',
    },
  ],
  rep: [
    {
      id: 'withdraw-rep',
      label: 'Withdraw from Real Estate',
      description: 'Request available real-estate balance to your main account',
      icon: 'cash',
    },
    {
      id: 'transfer-gwc',
      label: 'Transfer to GWC',
      description: 'Move available real-estate funds into Generational Wealth Creation',
      icon: 'users',
    },
    {
      id: 'transfer-namayumba',
      label: 'Transfer to Namayumba estate',
      description: 'Move funds into the Namayumba estate project',
      icon: 'building',
    },
  ],
}

export const MATURED_PROJECTS = [
  {
    id: 'matured-52wsc-2026',
    projectId: '52wsc',
    name: '52 Weeks Saving Challenge',
    shortName: '52WSC',
    icon: 'piggy',
    maturedOn: '6 Jan 2027',
    cycleLine: 'Cycle 1 · 2026 · personal start 7 Jan 2026',
    principal: 13_780_000,
    earnings: 412_500,
    availableAmount: 14_277_500,
    nextBestAction:
      'Start a new cycle with BF (UGX 85,000) or transfer everything to Main Account',
  },
  {
    id: 'matured-gwc-deposit',
    projectId: 'gwc',
    name: 'Generational Wealth Creation',
    shortName: 'GWC',
    icon: 'heart',
    maturedOn: '30 Jun 2026',
    cycleLine: 'Deposit batch #GWC-204 matured',
    principal: 1_500_000,
    earnings: 185_000,
    availableAmount: 1_685_000,
    nextBestAction: 'Transfer matured returns to main account or open GWC dashboard',
  },
  {
    id: 'matured-cgf-cycle',
    projectId: 'cgf',
    name: 'Commercial Goat Farming',
    shortName: 'CGF',
    icon: 'goat',
    maturedOn: '14 Jul 2026',
    cycleLine: '14-month cycle at Namayumba Goat Farm completed',
    principal: 1_800_000,
    earnings: 0,
    availableAmount: 1_800_000,
    nextBestAction: 'Transfer money to main account for withdrawal',
  },
]

/**
 * Existing MCS projects this member is NOT in.
 * Shown as other opportunities — not "coming soon".
 */
export const OTHER_PROJECTS = [
  {
    id: 'fsa',
    name: 'Fixed Savings Account',
    icon: 'lock',
    summary: 'Lock savings for a fixed term and earn a guaranteed higher rate.',
    rate: '10% p.a.',
    minEntry: 'UGX 500,000',
    cycle: '6 – 24 months',
    requestStatus: null, // null | 'pending'
  },
  {
    id: 'clubs',
    name: 'Clubs Account',
    icon: 'users',
    summary: 'Pool resources with other members towards shared goals.',
    rate: '8% p.a.',
    minEntry: 'UGX 20,000 joining',
    cycle: '12 months',
    requestStatus: null,
  },
  {
    id: 'coffee',
    name: 'Coffee Farming',
    icon: 'coffee',
    summary: 'Invest in managed coffee plantations and earn from harvest sales.',
    rate: '18 – 25% / cycle',
    minEntry: 'UGX 2,000,000',
    cycle: 'Seasonal harvest cycles',
    requestStatus: null,
  },
  {
    id: 'cocoa',
    name: 'Cocoa Farming',
    icon: 'seedling',
    summary: 'Participate in cocoa growing projects with strong export demand.',
    rate: '20 – 28% / cycle',
    minEntry: 'UGX 2,500,000',
    cycle: 'Multi-year orchard cycles',
    requestStatus: null,
  },
  {
    id: 'loans',
    name: 'Member Loans',
    icon: 'hand',
    summary: 'Access cooperative credit against your savings and shareholding.',
    rate: 'From 1.5% / month',
    minEntry: 'Based on eligibility',
    cycle: '3 – 24 month terms',
    requestStatus: null,
  },
  {
    id: 'tbills',
    name: 'Treasury Bills',
    icon: 'landmark',
    summary: 'Short-term government securities held through the cooperative.',
    rate: 'Market rate',
    minEntry: 'UGX 1,000,000',
    cycle: '91 – 364 days',
    requestStatus: null,
  },
]

export const TRANSACTIONS = [
  {
    id: 'tx1',
    title: 'Weekly contribution · 52WSC',
    meta: 'Project transfer',
    direction: 'out',
    category: 'invest',
    amount: -310_000,
    at: '2026-07-21T09:14:00',
    ref: 'WSC-0731',
  },
  {
    id: 'tx2',
    title: 'Dividend credit',
    meta: 'Cooperative shares',
    direction: 'in',
    category: 'in',
    amount: 180_000,
    at: '2026-07-18T14:02:00',
    ref: 'DIV-2026-Q2',
  },
  {
    id: 'tx3',
    title: 'GWC interest accrual',
    meta: 'Generational Wealth',
    direction: 'in',
    category: 'in',
    amount: 95_000,
    at: '2026-07-15T11:40:00',
    ref: 'GWC-INT-0715',
  },
  {
    id: 'tx4',
    title: 'Withdrawal to bank',
    meta: 'Stanbic · ****4421',
    direction: 'out',
    category: 'out',
    amount: -500_000,
    at: '2026-07-12T16:22:00',
    ref: 'WD-88421',
  },
  {
    id: 'tx5',
    title: 'Project maturity → Main',
    meta: 'From Fixed deposit (52WSC)',
    direction: 'in',
    category: 'in',
    amount: 1_250_000,
    at: '2026-07-08T10:05:00',
    ref: 'TRF-FD-2405',
  },
  {
    id: 'tx6',
    title: 'Goat package installment',
    meta: 'Commercial Goat Farming',
    direction: 'out',
    category: 'invest',
    amount: -600_000,
    at: '2026-07-03T08:50:00',
    ref: 'CGF-PAY-09',
  },
]

export function portfolioTotals(myProjects = MY_PROJECTS, shares = SHAREHOLDING, main = MAIN_ACCOUNT) {
  // Current money locked in projects only — excludes main-account withdrawable balance
  const investedInProjects = myProjects.reduce((sum, p) => sum + p.invested, 0)
  return {
    invested: investedInProjects,
    projectCount: myProjects.length,
    totalPortfolio: main.posted + investedInProjects + shares.portfolioValue,
  }
}
