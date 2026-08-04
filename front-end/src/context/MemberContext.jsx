import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'

const MemberContext = createContext(null)

const EMPTY_MEMBER = {
  firstName: 'Member',
  fullName: 'Member',
  initials: 'MC',
  accountNumber: '',
  isVerified: false,
  isShareholder: false,
}

const EMPTY_MAIN_ACCOUNT = {
  available: 0,
  posted: 0,
  pendingWithdrawal: 0,
}

const EMPTY_LIFETIME = {
  totalInvestedEver: 0,
  totalWithdrawnEver: 0,
}

const EMPTY_SHAREHOLDING = {
  isShareholder: false,
  displayState: 'no_access',
  sharesHeld: 0,
  sharesHeldDisplay: '0',
  portfolioValue: 0,
  dividendEligible: 0,
  dividendEligibleDisplay: '0',
  dividendEligibleValue: 0,
  expectedDividend: 0,
  dividendRate: '',
  dividendRatePercent: 0,
  certificateStatus: '',
  certificateNumber: '',
  memberSince: '',
  yearJoined: '',
  electionOpen: false,
  electionDeadline: '',
  equityBadge: '',
  tier: '',
  tierEmoji: '',
  newEraShares: 0,
  newEraSharesDisplay: '0',
  newEraValue: 0,
  newSharePurchasePrice: 0,
  legacyValuePerShare: 0,
  totalDividendsEarned: 0,
  issuancePeriodName: '',
  canClaimDividend: false,
  claimableDividend: 0,
  dividendClaimPending: false,
  dividendClaimStatus: '',
  dividendClaimStatusDisplay: '',
  dividendClaimBlockReason: '',
  dividendClaimBlockMessage: '',
}

const EMPTY_TOTALS = {
  totalPortfolio: 0,
  invested: 0,
  pendingWithheld: 0,
}

export function MemberProvider({ children }) {
  const { authFetch, isAuthenticated } = useAuth()
  const [dashboard, setDashboard] = useState(null)
  const [otherProjects, setOtherProjects] = useState([])
  const [toast, setToast] = useState(null)
  const [bereavementSubscribed, setBereavementSubscribed] = useState(false)
  const [retirementSubscribed, setRetirementSubscribed] = useState(false)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [dashboardError, setDashboardError] = useState('')

  const loadDashboard = useCallback(async ({ silent = false } = {}) => {
    if (!isAuthenticated) {
      setDashboard(null)
      setOtherProjects([])
      return
    }
    if (!silent) {
      setDashboardLoading(true)
      setDashboardError('')
    }
    try {
      const data = await authFetch('/api/dashboard/')
      setDashboard(data)
      setOtherProjects(data.otherProjects || [])
      if (silent) setDashboardError('')
    } catch (error) {
      if (!silent) {
        setDashboardError(error.message || 'Could not load member dashboard.')
      }
    } finally {
      if (!silent) setDashboardLoading(false)
    }
  }, [authFetch, isAuthenticated])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (!isAuthenticated) return undefined

    const poll = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      loadDashboard({ silent: true })
    }

    const timer = window.setInterval(poll, 20000)
    return () => window.clearInterval(timer)
  }, [isAuthenticated, loadDashboard])

  const member = dashboard?.member || EMPTY_MEMBER
  const mainAccount = dashboard?.mainAccount || EMPTY_MAIN_ACCOUNT
  const lifetime = dashboard?.lifetime || EMPTY_LIFETIME
  const shareholding = dashboard?.shareholding || EMPTY_SHAREHOLDING
  const isShareholder = Boolean(member.isShareholder)
  const myProjects = dashboard?.myProjects || []
  const pendingRequestsFromApi = dashboard?.pendingRequests || []
  const actionRequests = dashboard?.actionRequests || []
  const transactions = dashboard?.transactions || []
  const totals = dashboard?.totals || EMPTY_TOTALS
  const profile = dashboard?.profile || null

  const pendingRequests = useMemo(() => {
    const accessPending = otherProjects
      .filter((p) => p.requestStatus === 'pending')
      .map((p) => ({
        id: `access-${p.id}`,
        label: `Project access · ${p.name}`,
        detail: 'Awaiting review',
        project: 'Platform',
        status: 'pending',
        statusDisplay: 'Pending',
        tone: 'coop',
      }))
    // Avoid double-counting access requests already present from the API list.
    const apiIds = new Set(pendingRequestsFromApi.map((item) => item.id))
    return [
      ...pendingRequestsFromApi,
      ...accessPending.filter((item) => !apiIds.has(item.id)),
    ]
  }, [otherProjects, pendingRequestsFromApi])

  const requestAccess = useCallback(
    async (projectId, memberNotes = '') => {
      const project = otherProjects.find((p) => p.id === projectId)
      const data = await authFetch('/api/project-access/', {
        method: 'POST',
        body: {
          projectIds: [projectId],
          memberNotes: memberNotes || '',
        },
      })
      await loadDashboard({ silent: true })
      const first = (data?.messages || [])[0]
      setToast(
        first?.text ||
          (data?.ok
            ? `Access request submitted for ${project?.name || 'project'}.`
            : 'No new project request was submitted.'),
      )
      window.setTimeout(() => setToast(null), 3200)
      return data
    },
    [authFetch, loadDashboard, otherProjects],
  )

  const toggleShareholderPreview = useCallback(() => {
    setToast('Preview controls are disabled when using live member data.')
    window.setTimeout(() => setToast(null), 2800)
  }, [])

  const setShareholderPreview = useCallback((value) => {
    void value
  }, [])

  const setBereavementPreview = useCallback((value) => {
    setBereavementSubscribed(Boolean(value))
  }, [])

  const setRetirementPreview = useCallback((value) => {
    setRetirementSubscribed(Boolean(value))
  }, [])

  const setMaturedProjectsPreview = useCallback((value) => {
    void value
  }, [])

  const dismissToast = useCallback(() => setToast(null), [])

  const addToast = useCallback((message) => {
    setToast(message)
    window.setTimeout(() => setToast(null), 2800)
  }, [])

  const value = useMemo(
    () => ({
      member,
      mainAccount,
      lifetime,
      shareholding,
      isShareholder,
      bereavementSubscribed,
      retirementSubscribed,
      myProjects,
      maturedProjects: [],
      hasMaturedProjects: false,
      otherProjects,
      pendingRequests,
      actionRequests,
      transactions,
      totals,
      profile,
      dashboardLoading,
      dashboardError,
      reloadDashboard: loadDashboard,
      requestAccess,
      toggleShareholderPreview,
      setShareholderPreview,
      setBereavementPreview,
      setRetirementPreview,
      setMaturedProjectsPreview,
      addToast,
      toast,
      dismissToast,
    }),
    [
      member,
      mainAccount,
      lifetime,
      isShareholder,
      bereavementSubscribed,
      retirementSubscribed,
      shareholding,
      myProjects,
      otherProjects,
      pendingRequests,
      actionRequests,
      transactions,
      totals,
      profile,
      dashboardLoading,
      dashboardError,
      loadDashboard,
      requestAccess,
      toggleShareholderPreview,
      setShareholderPreview,
      setBereavementPreview,
      setRetirementPreview,
      setMaturedProjectsPreview,
      addToast,
      toast,
      dismissToast,
    ],
  )

  return <MemberContext.Provider value={value}>{children}</MemberContext.Provider>
}

export function useMember() {
  const ctx = useContext(MemberContext)
  if (!ctx) throw new Error('useMember must be used within MemberProvider')
  return ctx
}
