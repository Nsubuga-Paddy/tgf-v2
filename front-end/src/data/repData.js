/** Real Estate Projects — member-facing demo data aligned with Django models. */

export const REP_ACCOUNT = {
  accountNumber: 'MCSTGF-NS0042',
}

export const REP_PROJECTS = [
  {
    id: 'namayumba-estate',
    name: 'Namayumba Estate',
    location: 'Namayumba, Wakiso',
    description:
      'A cooperative land acquisition project creating serviced residential plots for participating members.',
    status: 'running',
    startDate: '15 Jan 2026',
    endDate: '15 Dec 2027',
    minimumInvestment: 'From UGX 5,000,000',
    membersCount: 24,
    userHasAccess: true,
    membershipState: 'joined',
    showInNavigation: true,
    landSize: 12.5,
    landSizeUnit: 'acres',
    vendorTotalAmount: 180_000_000,
    operationalCosts: 22_000_000,
    completedMembersCount: 14,
    completedPaymentsTotal: 112_000_000,
    incompleteMembersCount: 10,
    partialPaymentsTotal: 38_500_000,
    userTotalPaid: 8_000_000,
    userPendingBalance: 2_000_000,
    userPaymentCompleted: false,
    transactions: [
      {
        id: 'rep-tx-3',
        date: '18 Jul 2026',
        amount: 2_000_000,
        acquisitionQuantity: 0.25,
        acquisitionUnit: 'acres',
        balanceAfter: 2_000_000,
        paymentStatus: 'partial',
        type: 'payment',
      },
      {
        id: 'rep-tx-2',
        date: '20 Apr 2026',
        amount: 3_000_000,
        acquisitionQuantity: 0.35,
        acquisitionUnit: 'acres',
        balanceAfter: 4_000_000,
        paymentStatus: 'partial',
        type: 'payment',
      },
      {
        id: 'rep-tx-1',
        date: '20 Jan 2026',
        amount: 3_000_000,
        acquisitionQuantity: 0.4,
        acquisitionUnit: 'acres',
        balanceAfter: 7_000_000,
        paymentStatus: 'partial',
        type: 'payment',
      },
    ],
  },
  {
    id: 'mukono-commercial-hub',
    name: 'Mukono Commercial Hub',
    location: 'Mukono Municipality',
    description:
      'A mixed-use commercial property project for rental-income and long-term capital growth.',
    status: 'running',
    startDate: '1 Mar 2026',
    endDate: '30 Jun 2028',
    minimumInvestment: 'From UGX 10,000,000',
    membersCount: 16,
    userHasAccess: false,
    membershipState: 'available',
    showInNavigation: true,
    transactions: [],
  },
  {
    id: 'kira-residential-plots',
    name: 'Kira Residential Plots',
    location: 'Kira, Wakiso',
    description:
      'Completed cooperative purchase and subdivision of residential plots for members.',
    status: 'closed',
    startDate: '10 Feb 2024',
    endDate: '30 Nov 2025',
    minimumInvestment: 'UGX 6,000,000',
    membersCount: 31,
    userHasAccess: true,
    membershipState: 'joined',
    showInNavigation: false,
    landSize: 8,
    landSizeUnit: 'acres',
    vendorTotalAmount: 120_000_000,
    operationalCosts: 15_000_000,
    completedMembersCount: 31,
    completedPaymentsTotal: 135_000_000,
    incompleteMembersCount: 0,
    partialPaymentsTotal: 0,
    userTotalPaid: 6_000_000,
    userPendingBalance: 0,
    userPaymentCompleted: true,
    transactions: [
      {
        id: 'kira-tx-1',
        date: '30 Oct 2025',
        amount: 6_000_000,
        acquisitionQuantity: 1,
        acquisitionUnit: 'plot',
        balanceAfter: 0,
        paymentStatus: 'full',
        type: 'payment',
      },
    ],
  },
  {
    id: 'entebbe-lakeside-residences',
    name: 'Entebbe Lakeside Residences',
    location: 'Entebbe, Wakiso',
    description:
      'A planned residential development near Lake Victoria. Submit interest for allocation updates.',
    status: 'upcoming',
    startDate: '1 Feb 2027',
    endDate: '30 Jun 2029',
    minimumInvestment: 'From UGX 12,000,000',
    membersCount: 0,
    userHasAccess: false,
    membershipState: 'interest-available',
    showInNavigation: false,
    transactions: [],
  },
]

export const REP_RUNNING_PROJECTS = REP_PROJECTS.filter((project) => project.status === 'running')
export const REP_CLOSED_PROJECTS = REP_PROJECTS.filter((project) => project.status === 'closed')
export const REP_UPCOMING_PROJECTS = REP_PROJECTS.filter((project) => project.status === 'upcoming')

export function getRepProject(projectId) {
  return REP_PROJECTS.find((project) => project.id === projectId)
}
