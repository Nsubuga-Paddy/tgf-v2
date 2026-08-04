/** Profile page mock — left column + action requests (no middle My Projects column). */

export const PROFILE = {
  firstName: 'Sarah',
  lastName: 'Nakato',
  fullName: 'Sarah Nakato',
  username: 'sarah.nakato',
  email: 'sarah.nakato@email.com',
  accountNumber: 'MCSTGF-NS0042',
  memberSince: 'March 12, 2021',
  whatsapp: '+256700111222',
  nationalId: 'CM990123456789',
  address: 'Namayumba, Wakiso District, Uganda',
  birthdate: 'Mar 15, 1992',
  bio: 'MCS member focused on long-term family wealth and cooperative growth.',
  isVerified: true,
  bankName: 'Stanbic Bank',
  bankAccountNumber: '9030012345678',
  bankAccountName: 'Sarah Nakato',
}

export const GRANTED_PROJECTS = [
  '52 Weeks Saving Challenge',
  'Generational Wealth Creation',
  'Commercial Goat Farming',
  'Real Estate Projects',
]

export const REQUESTABLE_PROJECTS = [
  { id: 'fsa', name: 'Fixed Savings Account' },
  { id: 'clubs', name: 'Clubs Account' },
  { id: 'coffee', name: 'Coffee Farming' },
  { id: 'cocoa', name: 'Cocoa Farming' },
]

export const PROJECT_ACCESS_REQUESTS = [
  {
    id: 'par1',
    project: 'Clubs Account',
    status: 'pending',
    statusDisplay: 'Pending',
    createdAt: 'Jul 18, 2026',
    adminNotes: '',
  },
  {
    id: 'par2',
    project: 'Fixed Savings Account',
    status: 'rejected',
    statusDisplay: 'Rejected',
    createdAt: 'Jun 02, 2026',
    adminNotes: 'Please complete KYC documents at the office first.',
  },
]

export const ACTION_REQUESTS = [
  {
    id: 'ar1',
    typeLabel: 'Main account withdrawal',
    project: 'MAIN',
    detail: 'Withdrawal request of UGX 500,000 to Stanbic ****5678',
    createdAt: 'Jul 20, 2026',
    status: 'pending',
    statusDisplay: 'Pending',
    tone: 'main',
  },
  {
    id: 'ar2',
    typeLabel: 'Transfer to main',
    project: '52WSC',
    detail: 'Transfer matured savings UGX 310,000 to main account',
    createdAt: 'Jul 19, 2026',
    status: 'pending',
    statusDisplay: 'Pending',
    tone: 'wsc',
  },
  {
    id: 'ar3',
    typeLabel: 'Main account withdrawal',
    project: 'MAIN',
    detail: 'Withdrawal request of UGX 300,000 reversed by admin correction',
    createdAt: 'Jul 10, 2026',
    status: 'reversed',
    statusDisplay: 'Reversed',
    tone: 'main',
  },
  {
    id: 'ar4',
    typeLabel: 'Project withdraw',
    project: 'REP',
    detail: 'Withdraw UGX 1,000,000 from Namayumba project balance',
    createdAt: 'Jun 28, 2026',
    status: 'processed',
    statusDisplay: 'Processed',
    tone: 'rep',
  },
  {
    id: 'ar5',
    typeLabel: 'Project access',
    project: 'CLUBS',
    detail: 'Access request for Clubs Account',
    createdAt: 'Jul 18, 2026',
    status: 'pending',
    statusDisplay: 'Pending',
    tone: 'coop',
  },
]
