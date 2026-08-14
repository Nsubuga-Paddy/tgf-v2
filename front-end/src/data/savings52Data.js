/**
 * 52WSC design fixtures — frontend preview only (no backend yet).
 *
 * Scenario: member finished a personal 52-week cycle that started on their
 * first 2026 deposit. Full ladder was covered, interest accrued daily at 15%
 * annualized, and a leftover BF remains after week 52.
 */

export const SAVINGS_52_MEMBER = {
  accountNumber: 'MCSTGF-NS0042',
  targetAmount: 13_780_000,
  currentYearDeposits: 2_860_000,
  progressPercentage: 20.75,
  balanceBroughtForward: 40_000,
  weeksCompleted: 18,
  nextWeekToCover: 19,
  totalWeeks: 52,
  cycleComplete: false,
  cycleStartDate: '7 Jan 2026',
  fixedSavings: {
    totalInvested: 1_500_000,
    totalInterestExpected: 225_000,
    dailyUnfixedInterest: 558.9,
    unfixedInterestEarnedYtd: 72_000,
    latestMaturityDate: 'Sep 15, 2026',
  },
  weeklyTarget: {
    currentWeek: 30,
    requiredSavings: 300_000,
    remainingWeeks: 22,
  },
}

/** Matured cycle waiting for member decision (BF present). */
export const SAVINGS_52_MATURED_PREVIEW = {
  accountNumber: 'MCSTGF-NS0042',
  targetAmount: 13_780_000,
  currentYearDeposits: 13_865_000,
  progressPercentage: 100,
  balanceBroughtForward: 85_000,
  weeksCompleted: 52,
  nextWeekToCover: 53,
  totalWeeks: 52,
  cycleComplete: true,
  cycleStartDate: '7 Jan 2026',
  cycleEndDate: '6 Jan 2027',
  cycleMaturedOn: '6 Jan 2027',
  cycleLabel: 'Cycle 1 · 2026',
  maturedCycle: {
    id: 'preview-cycle-1',
    label: 'Cycle 1 · 2026',
    startDate: '7 Jan 2026',
    maturedOn: '6 Jan 2027',
    weeksCompleted: 52,
    /** Amount applied to the 52-week ladder (principal saved in cycle) */
    amountSaved: 13_780_000,
    /** 15% annualized, daily accrual for days money was held */
    interestEarned: 412_500,
    /** Leftover after week 52 was fully covered */
    balanceBroughtForward: 85_000,
    status: 'awaiting_decision',
  },
  fixedSavings: {
    totalInvested: 0,
    totalInterestExpected: 0,
    dailyUnfixedInterest: 0,
    unfixedInterestEarnedYtd: 412_500,
    latestMaturityDate: '—',
  },
  weeklyTarget: {
    currentWeek: 52,
    requiredSavings: 520_000,
    remainingWeeks: 0,
  },
}

export const SAVINGS_52_INVESTMENTS = [
  {
    id: 'inv-1',
    startDate: 'Feb 10, 2026',
    amount: 1_000_000,
    interestRate: '15%',
    interestEarned: 62_400,
    expectedInterest: 150_000,
    maturityDate: 'Feb 10, 2027',
    status: 'Fixed',
  },
  {
    id: 'inv-2',
    startDate: 'Apr 18, 2026',
    amount: 500_000,
    interestRate: '15%',
    interestEarned: 18_800,
    expectedInterest: 75_000,
    maturityDate: 'Apr 18, 2027',
    status: 'Fixed',
  },
]

export const SAVINGS_52_TRANSACTIONS = [
  {
    id: 'tx-1',
    date: 'Jul 18, 2026',
    type: 'Deposit',
    typeKey: 'deposit',
    amount: 310_000,
    runningTotal: 2_860_000,
    weeksCovered: 'Week 17, Week 18',
    receipt: '52WSC-2026-018',
    balanceForward: 40_000,
  },
  {
    id: 'tx-2',
    date: 'Jul 04, 2026',
    type: 'Deposit',
    typeKey: 'deposit',
    amount: 290_000,
    runningTotal: 2_550_000,
    weeksCovered: 'Week 15, Week 16',
    receipt: '52WSC-2026-016',
    balanceForward: 30_000,
  },
  {
    id: 'tx-3',
    date: 'Jun 20, 2026',
    type: 'Transfer to GWC',
    typeKey: 'gwc_contribution',
    amount: -250_000,
    runningTotal: 2_260_000,
    weeksCovered: '—',
    receipt: 'GWC-TR-0042',
    balanceForward: null,
  },
  {
    id: 'tx-4',
    date: 'Jun 06, 2026',
    type: 'Deposit',
    typeKey: 'deposit',
    amount: 450_000,
    runningTotal: 2_510_000,
    weeksCovered: 'Week 12, Week 13, Week 14',
    receipt: '52WSC-2026-014',
    balanceForward: 20_000,
  },
  {
    id: 'tx-5',
    date: 'May 16, 2026',
    type: 'Withdrawal',
    typeKey: 'withdrawal',
    amount: -200_000,
    runningTotal: 2_060_000,
    weeksCovered: '—',
    receipt: 'WDR-0042',
    balanceForward: null,
  },
]

export const SAVINGS_52_MATURED_TRANSACTIONS = [
  {
    id: 'mtx-1',
    date: '6 Jan 2027',
    type: 'Deposit',
    typeKey: 'deposit',
    amount: 605_000,
    runningTotal: 13_865_000,
    weeksCovered: 'Week 52',
    receipt: '52WSC-2026-052',
    balanceForward: 85_000,
  },
  {
    id: 'mtx-2',
    date: '20 Dec 2026',
    type: 'Deposit',
    typeKey: 'deposit',
    amount: 980_000,
    runningTotal: 13_260_000,
    weeksCovered: 'Week 50, Week 51',
    receipt: '52WSC-2026-050',
    balanceForward: 0,
  },
  {
    id: 'mtx-3',
    date: '7 Jan 2026',
    type: 'Deposit',
    typeKey: 'deposit',
    amount: 10_000,
    runningTotal: 10_000,
    weeksCovered: 'Week 1',
    receipt: '52WSC-2026-001',
    balanceForward: 0,
  },
]

export function maturedTotals(cycle) {
  const amountSaved = Number(cycle?.amountSaved) || 0
  const interestEarned = Number(cycle?.interestEarned) || 0
  const balanceBroughtForward = Number(cycle?.balanceBroughtForward) || 0
  return {
    amountSaved,
    interestEarned,
    balanceBroughtForward,
    maturedPot: amountSaved + interestEarned,
    transferAll: amountSaved + interestEarned + balanceBroughtForward,
  }
}
