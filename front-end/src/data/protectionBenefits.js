/** Protection benefits — cover products (not capital growth investments). */

export const PROTECTION_BENEFITS = [
  {
    id: 'bereavement',
    name: 'MCS Bereavement Fund',
    tagline: 'Funeral support for members and their families',
    icon: 'shield',
    premiumLabel: 'Annual premium',
    premium: 'UGX 240,000',
    premiumPeriod: 'per year',
    summary:
      'Funeral support for MCS members and their families. Annual premium UGX 240,000.',
    enrolledSummary:
      'Your family funeral cover is active. Premium is current and dependants on your policy are covered.',
    enrolledMeta: [
      { label: 'Cover status', value: 'Active' },
      { label: 'Premium paid', value: 'UGX 240,000 / 2026' },
      { label: 'Next renewal', value: '12 Jan 2027' },
      { label: 'Dependants listed', value: '9 people' },
    ],
    ctaPrimary: 'Join cover',
    ctaSecondary: 'Learn more',
    enrolledPrimary: 'Manage cover',
    enrolledSecondary: 'View policy',
  },
  {
    id: 'retirement',
    name: 'Retirement Savings Scheme',
    tagline: 'Build a long-term fund for life after work',
    icon: 'clock',
    premiumLabel: 'Suggested contribution',
    premium: 'UGX 50,000',
    premiumPeriod: 'per month',
    summary:
      'A long-term cooperative plan that helps members steadily build a retirement fund, with disciplined monthly contributions and access designed for later life.',
    enrolledSummary:
      'You are actively saving toward retirement. Keep contributing monthly to stay on track for access at age 55+.',
    enrolledMeta: [
      { label: 'Retirement balance', value: 'UGX 3,450,000' },
      { label: 'Monthly contribution', value: 'UGX 50,000' },
      { label: 'Months contributed', value: '48' },
      { label: 'Access age', value: '55+' },
    ],
    ctaPrimary: 'Start saving',
    ctaSecondary: 'Learn more',
    enrolledPrimary: 'Add contribution',
    enrolledSecondary: 'View statement',
  },
]
