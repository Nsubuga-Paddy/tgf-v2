import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  APPLICATION_STATUS_LABELS,
  LOAN_REPAYMENT_METHODS,
  computeDemoEligibility,
} from '../data/loansData'
import { useAuth } from './AuthContext'
import { useMember } from './MemberContext'

const LoansContext = createContext(null)

function defaultState() {
  return {
    eligibility: null,
    applications: [],
    activeLoans: [],
    closedLoans: [],
    repaymentMethods: LOAN_REPAYMENT_METHODS,
    loading: true,
    error: '',
  }
}

export function LoansProvider({ children }) {
  const { authFetch, isAuthenticated } = useAuth()
  const {
    member,
    profile,
    shareholding,
    myProjects,
    mainAccount,
    reloadDashboard,
    addToast,
  } = useMember()
  const [state, setState] = useState(defaultState)

  const fallbackEligibility = useMemo(
    () =>
      computeDemoEligibility({
        isVerified: member.isVerified,
        profile,
        shareholding,
        myProjects,
        mainAccount,
        activeLoans: state.activeLoans,
      }),
    [member.isVerified, profile, shareholding, myProjects, mainAccount, state.activeLoans],
  )

  const applyPayload = useCallback((payload) => {
    if (!payload) return
    setState((prev) => ({
      ...prev,
      eligibility: payload.eligibility || prev.eligibility,
      applications: payload.applications || prev.applications,
      activeLoans: payload.activeLoans || prev.activeLoans,
      closedLoans: payload.closedLoans || prev.closedLoans,
      repaymentMethods: payload.repaymentMethods || prev.repaymentMethods,
      loading: false,
      error: '',
    }))
  }, [])

  const loadLoans = useCallback(
    async ({ silent = false } = {}) => {
      if (!isAuthenticated) {
        setState(defaultState())
        return null
      }
      if (!silent) {
        setState((prev) => ({ ...prev, loading: true, error: '' }))
      }
      try {
        const payload = await authFetch('/api/projects/loans/')
        applyPayload(payload)
        return payload
      } catch (error) {
        const message = error.message || 'Could not load loans.'
        setState((prev) => ({ ...prev, loading: false, error: message }))
        return null
      }
    },
    [applyPayload, authFetch, isAuthenticated],
  )

  useEffect(() => {
    loadLoans()
  }, [loadLoans])

  const eligibility = state.eligibility || fallbackEligibility

  const runEligibilityCheck = useCallback(async () => {
    try {
      const payload = await authFetch('/api/projects/loans/eligibility/', { method: 'POST' })
      const result = payload.eligibility || payload
      setState((prev) => ({ ...prev, eligibility: result }))
      return result
    } catch {
      setState((prev) => ({ ...prev, eligibility: fallbackEligibility }))
      return fallbackEligibility
    }
  }, [authFetch, fallbackEligibility])

  const submitApplication = useCallback(
    async (payload) => {
      const data = await authFetch('/api/projects/loans/apply/', {
        method: 'POST',
        body: payload,
      })
      applyPayload(data)
      addToast('Loan application submitted for review.')
      return data.application
    },
    [addToast, applyPayload, authFetch],
  )

  const getApplication = useCallback(
    (id) => state.applications.find((app) => String(app.id) === String(id)) || null,
    [state.applications],
  )

  const getLoan = useCallback(
    (id) => state.activeLoans.find((loan) => String(loan.id) === String(id)) || null,
    [state.activeLoans],
  )

  const submitLoanRepayment = useCallback(
    async ({ loanId, amount, notes = '' }) => {
      const data = await authFetch(`/api/projects/loans/facilities/${loanId}/repay/`, {
        method: 'POST',
        body: { amount, notes: notes || undefined },
      })
      applyPayload(data)
      await reloadDashboard({ silent: true })
      addToast(data.message || 'Repayment posted from Main Account. Your loan balance has been updated.')
      return data.repayment
    },
    [addToast, applyPayload, authFetch, reloadDashboard],
  )

  const value = useMemo(
    () => ({
      eligibility,
      runEligibilityCheck,
      applications: state.applications,
      activeLoans: state.activeLoans,
      closedLoans: state.closedLoans,
      repaymentMethods: state.repaymentMethods,
      loansLoading: state.loading,
      loansError: state.error,
      reloadLoans: loadLoans,
      submitApplication,
      getApplication,
      getLoan,
      submitLoanRepayment,
      applicationStatusLabels: APPLICATION_STATUS_LABELS,
    }),
    [
      eligibility,
      runEligibilityCheck,
      state.applications,
      state.activeLoans,
      state.closedLoans,
      state.repaymentMethods,
      state.loading,
      state.error,
      loadLoans,
      submitApplication,
      getApplication,
      getLoan,
      submitLoanRepayment,
    ],
  )

  return <LoansContext.Provider value={value}>{children}</LoansContext.Provider>
}

export function useLoans() {
  const ctx = useContext(LoansContext)
  if (!ctx) throw new Error('useLoans must be used within LoansProvider')
  return ctx
}
