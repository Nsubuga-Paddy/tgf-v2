/** Public Help Center — accessible without login. */

export const HELP_CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'general', label: 'General & platform' },
  { id: 'profile', label: 'Profile & account' },
  { id: 'savings_52', label: '52 Weeks Saving Challenge' },
  { id: 'fixed_savings', label: 'Fixed Savings' },
  { id: 'gwc', label: 'Generational Wealth (GWC)' },
  { id: 'cgf', label: 'Commercial Goat Farming' },
  { id: 'cooperative', label: 'Cooperative Shareholding' },
  { id: 'mesu', label: 'MESU Academy' },
  { id: 'real_estate', label: 'Real Estate' },
  { id: 'other', label: 'Other' },
]

export const HELP_VIDEOS = [
  {
    id: 'hv1',
    title: 'Getting started with the MCS portal',
    description:
      'A walkthrough of signing up, logging in, and finding your way around the member dashboard.',
    category: 'general',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv2',
    title: 'Complete your profile and bank details',
    description:
      'Learn how to update personal information, WhatsApp number, and bank account details used for withdrawals.',
    category: 'profile',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv3',
    title: 'Join the 52 Weeks Saving Challenge',
    description:
      'How to enroll, track weekly savings, and request transfers to your main account when cycles mature.',
    category: 'savings_52',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv4',
    title: 'Fixed Savings Account basics',
    description:
      'Understand lock periods, interest, and how fixed savings appear in your portfolio.',
    category: 'fixed_savings',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv5',
    title: 'Generational Wealth Creation contributions',
    description:
      'See how GWC contributions work and where to track your progress in the portal.',
    category: 'gwc',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv6',
    title: 'Commercial Goat Farming overview',
    description:
      'Learn how goat units, sales, and cash-out requests work for CGF members.',
    category: 'cgf',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv7',
    title: 'Cooperative shareholding explained',
    description:
      'Share tiers, dividends, certificates, and how to read your shareholding statement.',
    category: 'cooperative',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv8',
    title: 'Real Estate projects for members',
    description:
      'How to request access, view project balances, and submit withdrawal requests.',
    category: 'real_estate',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv9',
    title: 'Requesting project access',
    description:
      'Step-by-step guide to requesting access to MCS groups and tracking admin review.',
    category: 'profile',
    youtubeId: 'dQw4w9WgXcQ',
  },
  {
    id: 'hv10',
    title: 'Withdrawing from your main account',
    description:
      'How main account withdrawals are requested and paid to your registered bank account.',
    category: 'general',
    youtubeId: 'dQw4w9WgXcQ',
  },
]

export function youtubeThumb(id) {
  return `https://img.youtube.com/vi/${id}/hqdefault.jpg`
}

export function youtubeEmbed(id) {
  return `https://www.youtube-nocookie.com/embed/${id}`
}
