import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  ArrowLeft,
  ArrowLeftRight,
  Building2,
  HandCoins,
  Home,
  Landmark,
  PiggyBank,
  Sprout,
  Wallet,
  X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useLoans } from '../context/LoansContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

const DESTINATIONS = [
  {
    id: 'loan_clearance',
    title: 'Clear or reduce a loan',
    detail: 'Repay an active loan directly from Main Account.',
    Icon: HandCoins,
    ready: true,
  },
  {
    id: 'shares',
    title: 'Purchase shares',
    detail: 'Buy additional MCS cooperative shares.',
    Icon: Landmark,
    ready: true,
  },
  {
    id: 'savings_52wsc',
    title: 'Add 52WSC contribution',
    detail: 'Send funds into your 52 Weeks Savings Challenge.',
    Icon: PiggyBank,
    ready: true,
  },
  {
    id: 'gwc',
    title: 'Add GWC contribution',
    detail: 'Minimum deposit is UGX 12,000,000.',
    Icon: Building2,
    ready: true,
  },
  {
    id: 'cgf',
    title: 'Purchase goat farming package',
    detail: 'Buy the current CGF package from Main Account.',
    Icon: Sprout,
    ready: true,
  },
  {
    id: 'real_estate',
    title: 'Pay real estate project',
    detail: 'Contribute to a running MCS real estate opportunity.',
    Icon: Home,
    ready: true,
  },
]

function parseAmount(value) {
  const parsed = Number(String(value).replace(/,/g, '').trim())
  return Number.isFinite(parsed) ? parsed : 0
}

function parseShares(value) {
  const parsed = Number(String(value).replace(/,/g, '').trim())
  return Number.isFinite(parsed) ? parsed : 0
}

function formatShares(value) {
  const qty = Number(value || 0)
  if (!Number.isFinite(qty)) return '0'
  return Number.isInteger(qty) ? String(qty) : qty.toFixed(1)
}

function isHalfShareStep(value) {
  return Number.isFinite(value) && value > 0 && Math.abs(value * 2 - Math.round(value * 2)) < 0.00001
}

function tierForPosition(tiers, shares, value) {
  if (!Array.isArray(tiers) || tiers.length === 0) return null
  let match = tiers[0]
  tiers.forEach((tier) => {
    const minValue = Number(tier.minValue || 0)
    const minShares = Number(tier.minShares || 0)
    if (minValue > 0) {
      if (value >= minValue) match = tier
      return
    }
    if (shares >= minShares) match = tier
  })
  return match
}

function tierRangeLabel(tier, tiers) {
  const minValue = Number(tier?.minValue || 0)
  if (minValue > 0) return `${formatUGX(minValue)}+ portfolio value`

  const minShares = Number(tier?.minShares || 0)
  const nextShareTier = (tiers || []).find(
    (item) => Number(item.minValue || 0) === 0 && Number(item.minShares || 0) > minShares,
  )
  if (!nextShareTier) return `${formatShares(minShares)}+ shares`

  const maxShares = Number(nextShareTier.minShares || 0) - 1
  return `${formatShares(minShares)}-${formatShares(maxShares)} shares`
}

export default function MainAccountProjectsModal({
  open,
  onClose,
  available,
  initialDestination = null,
  initialProjectId = null,
  onSuccess = null,
}) {
  const { authFetch } = useAuth()
  const { activeLoans, loansLoading, reloadLoans, submitLoanRepayment } = useLoans()
  const { addToast, reloadDashboard, shareholding } = useMember()
  const [step, setStep] = useState('choose')
  const [destinationId, setDestinationId] = useState(null)
  const [loanId, setLoanId] = useState('')
  const [amount, setAmount] = useState('')
  const [shareQuantity, setShareQuantity] = useState('')
  const [shareOptions, setShareOptions] = useState(null)
  const [shareOptionsLoading, setShareOptionsLoading] = useState(false)
  const [wscOptions, setWscOptions] = useState(null)
  const [wscOptionsLoading, setWscOptionsLoading] = useState(false)
  const [gwcOptions, setGwcOptions] = useState(null)
  const [gwcOptionsLoading, setGwcOptionsLoading] = useState(false)
  const [cgfOptions, setCgfOptions] = useState(null)
  const [cgfOptionsLoading, setCgfOptionsLoading] = useState(false)
  const [cgfPackageId, setCgfPackageId] = useState('')
  const [cgfQuantity, setCgfQuantity] = useState('1')
  const [repOptions, setRepOptions] = useState(null)
  const [repOptionsLoading, setRepOptionsLoading] = useState(false)
  const [repProjectId, setRepProjectId] = useState('')
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const detailsBodyRef = useRef(null)

  const selected = useMemo(
    () => DESTINATIONS.find((item) => item.id === destinationId) || null,
    [destinationId],
  )
  const isLoanFlow = selected?.id === 'loan_clearance'
  const isShareFlow = selected?.id === 'shares'
  const isWscFlow = selected?.id === 'savings_52wsc'
  const isGwcFlow = selected?.id === 'gwc'
  const isCgfFlow = selected?.id === 'cgf'
  const isRepFlow = selected?.id === 'real_estate'
  const selectedLoan = useMemo(
    () => activeLoans.find((loan) => String(loan.id) === String(loanId)) || null,
    [activeLoans, loanId],
  )

  useEffect(() => {
    if (!open) return
    const hasInitialDestination = DESTINATIONS.some((item) => item.id === initialDestination)
    setStep(hasInitialDestination ? 'details' : 'choose')
    setDestinationId(hasInitialDestination ? initialDestination : null)
    setLoanId('')
    setAmount('')
    setShareQuantity('')
    setWscOptions(null)
    setGwcOptions(null)
    setCgfOptions(null)
    setCgfPackageId('')
    setCgfQuantity('1')
    setRepOptions(null)
    setRepProjectId(initialProjectId ? String(initialProjectId) : '')
    setNote('')
    setSubmitting(false)
    setError('')
  }, [initialDestination, initialProjectId, open])

  useEffect(() => {
    if (!open || !isLoanFlow) return
    reloadLoans({ silent: true })
  }, [open, isLoanFlow, reloadLoans])

  useEffect(() => {
    if (!open || !isShareFlow) return
    let cancelled = false
    ;(async () => {
      setShareOptionsLoading(true)
      setError('')
      try {
        const payload = await authFetch('/api/shareholding/purchase-options/')
        if (!cancelled) setShareOptions(payload)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load share purchase options.')
      } finally {
        if (!cancelled) setShareOptionsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authFetch, isShareFlow, open])

  useEffect(() => {
    if (!open || !isWscFlow) return
    let cancelled = false
    ;(async () => {
      setWscOptionsLoading(true)
      setError('')
      try {
        const payload = await authFetch('/api/projects/52wsc/contribute-options/')
        if (!cancelled) setWscOptions(payload)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load 52WSC contribution options.')
      } finally {
        if (!cancelled) setWscOptionsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authFetch, isWscFlow, open])

  useEffect(() => {
    if (!open || !isGwcFlow) return
    let cancelled = false
    ;(async () => {
      setGwcOptionsLoading(true)
      setError('')
      try {
        const payload = await authFetch('/api/projects/gwc/contribute-options/')
        if (!cancelled) setGwcOptions(payload)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load GWC deposit options.')
      } finally {
        if (!cancelled) setGwcOptionsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authFetch, isGwcFlow, open])

  useEffect(() => {
    if (!open || !isCgfFlow) return
    let cancelled = false
    ;(async () => {
      setCgfOptionsLoading(true)
      setError('')
      try {
        const payload = await authFetch('/api/projects/cgf/purchase-options/')
        if (!cancelled) {
          setCgfOptions(payload)
          setCgfPackageId(payload.defaultPackageId ? String(payload.defaultPackageId) : '')
          setCgfQuantity('1')
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load CGF package options.')
      } finally {
        if (!cancelled) setCgfOptionsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authFetch, isCgfFlow, open])

  useEffect(() => {
    if (!open || !isRepFlow) return
    let cancelled = false
    ;(async () => {
      setRepOptionsLoading(true)
      setError('')
      try {
        const payload = await authFetch('/api/projects/rep/contribute-options/')
        if (!cancelled) {
          setRepOptions(payload)
          const projects = Array.isArray(payload.projects) ? payload.projects : []
          const preferred =
            initialProjectId &&
            projects.some((item) => String(item.id) === String(initialProjectId))
              ? String(initialProjectId)
              : payload.defaultProjectId
                ? String(payload.defaultProjectId)
                : ''
          setRepProjectId(preferred)
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load Real Estate projects.')
      } finally {
        if (!cancelled) setRepOptionsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authFetch, initialProjectId, isRepFlow, open])

  useEffect(() => {
    if (!open || step !== 'details' || !(isCgfFlow || isRepFlow)) return
    const node = detailsBodyRef.current
    if (!node) return
    node.scrollTop = 0
  }, [open, step, isCgfFlow, isRepFlow, cgfPackageId, cgfOptionsLoading, repProjectId, repOptionsLoading])

  useEffect(() => {
    if (!isLoanFlow) return
    if (activeLoans.length === 1) {
      setLoanId(String(activeLoans[0].id))
      return
    }
    if (loanId && !activeLoans.some((loan) => String(loan.id) === String(loanId))) {
      setLoanId('')
    }
  }, [activeLoans, isLoanFlow, loanId])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') {
        if (submitting) return
        if (step === 'details') {
          setStep('choose')
          return
        }
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose, step, submitting])

  if (!open) return null

  const parsedAmount = parseAmount(amount)
  const hasAmount = parsedAmount > 0
  const withinBalance = parsedAmount <= Number(available || 0)
  const outstanding = Number(selectedLoan?.outstanding || 0)
  const withinOutstanding = !isLoanFlow || parsedAmount <= outstanding
  const canSendLoan =
    isLoanFlow &&
    Boolean(selectedLoan) &&
    hasAmount &&
    withinBalance &&
    withinOutstanding &&
    !submitting
  const parsedShares = parseShares(shareQuantity)
  const pricePerShare = Number(shareOptions?.pricePerShare || shareholding?.newSharePurchasePrice || 0)
  const shareCost = parsedShares * pricePerShare
  const hasValidShareStep = isHalfShareStep(parsedShares)
  const shareCostWithinBalance = shareCost <= Number(available || 0)
  const currentShares = Number(shareOptions?.currentShares || shareholding?.sharesHeld || 0)
  const currentPortfolioValue = Number(
    shareOptions?.currentPortfolioValue || shareholding?.portfolioValue || 0,
  )
  const projectedShares = currentShares + (hasValidShareStep ? parsedShares : 0)
  const projectedValue = currentPortfolioValue + (hasValidShareStep ? shareCost : 0)
  const projectedTier = tierForPosition(
    shareOptions?.tierRequirements,
    projectedShares,
    projectedValue,
  )
  const nextTier = shareOptions?.nextTier || null
  const canSendSharePurchase =
    isShareFlow &&
    Boolean(shareOptions) &&
    pricePerShare > 0 &&
    hasValidShareStep &&
    shareCostWithinBalance &&
    !submitting

  const wscAvailable = Number(wscOptions?.availableMain ?? available ?? 0)
  const wscCanContribute = wscOptions?.canContribute !== false
  const wscTarget = Number(wscOptions?.targetAmount || 13_780_000)
  const wscDeposits = Number(wscOptions?.cycleDeposits || 0)
  const projectedWscDeposits = wscDeposits + (hasAmount ? parsedAmount : 0)
  const projectedWscProgress = Math.min((projectedWscDeposits / Math.max(wscTarget, 1)) * 100, 100)
  const canSendWsc =
    isWscFlow &&
    Boolean(wscOptions) &&
    wscCanContribute &&
    hasAmount &&
    parsedAmount <= wscAvailable &&
    !submitting

  const gwcAvailable = Number(gwcOptions?.availableMain ?? available ?? 0)
  const gwcMinimum = Number(gwcOptions?.minimumDeposit || 12_000_000)
  const gwcMonthlyRedeemableThreshold = Number(
    gwcOptions?.monthlyInterestRedeemableThreshold || 120_000_000,
  )
  const gwcMeetsMinimum = parsedAmount >= gwcMinimum
  const gwcGetsMonthlyInterest = parsedAmount >= gwcMonthlyRedeemableThreshold
  const gwcInterestRate = Number(gwcOptions?.interestRate || 25)
  const gwcTenureDays = Number(gwcOptions?.tenureDays || 365)
  const canSendGwc =
    isGwcFlow &&
    Boolean(gwcOptions) &&
    hasAmount &&
    gwcMeetsMinimum &&
    parsedAmount <= gwcAvailable &&
    !submitting

  const cgfAvailable = Number(cgfOptions?.availableMain ?? available ?? 0)
  const cgfPackages = Array.isArray(cgfOptions?.packages) ? cgfOptions.packages : []
  const cgfPackage =
    cgfPackages.find((item) => String(item.id) === String(cgfPackageId)) || cgfPackages[0] || null
  const parsedCgfQuantity = Math.max(1, Math.floor(parseAmount(cgfQuantity) || 1))
  const cgfUnitCost = Number(cgfPackage?.totalCost || 0)
  const cgfTotalCost = parsedCgfQuantity * cgfUnitCost
  const cgfCanPurchase = cgfOptions?.canPurchase !== false && Boolean(cgfPackage)
  const cgfHarvestGoats = Number(cgfPackage?.harvestGoats || 0) * parsedCgfQuantity
  const cgfExpectedCashout = Number(cgfPackage?.expectedCashout || 0) * parsedCgfQuantity
  const cgfGain = Math.max(0, Number(cgfPackage?.expectedCashout || 0) - Number(cgfPackage?.totalCost || 0))
  const canSendCgf =
    isCgfFlow &&
    Boolean(cgfPackage) &&
    cgfCanPurchase &&
    parsedCgfQuantity >= 1 &&
    cgfTotalCost > 0 &&
    cgfTotalCost <= cgfAvailable &&
    !submitting

  const repAvailable = Number(repOptions?.availableMain ?? available ?? 0)
  const repProjects = Array.isArray(repOptions?.projects) ? repOptions.projects : []
  const repProject =
    repProjects.find((item) => String(item.id) === String(repProjectId)) || repProjects[0] || null
  const repCanContribute = repOptions?.canContribute !== false && Boolean(repProject)
  const canSendRep =
    isRepFlow &&
    Boolean(repProject) &&
    repCanContribute &&
    hasAmount &&
    parsedAmount <= repAvailable &&
    !submitting

  const chooseDestination = (item) => {
    setDestinationId(item.id)
    setLoanId(item.id === 'loan_clearance' && activeLoans.length === 1 ? String(activeLoans[0].id) : '')
    setAmount('')
    setShareQuantity('')
    setCgfPackageId('')
    setCgfQuantity('1')
    setRepProjectId('')
    setNote('')
    setError('')
    setStep('details')
  }

  const goBackToOptions = () => {
    if (submitting) return
    setStep('choose')
    setAmount('')
    setShareQuantity('')
    setCgfPackageId('')
    setCgfQuantity('1')
    setRepProjectId('')
    setNote('')
    setError('')
    setLoanId('')
  }

  const setFullOutstanding = () => {
    if (!selectedLoan) return
    setAmount(String(Math.round(Number(selectedLoan.outstanding || 0))))
  }

  const setNextDue = () => {
    if (!selectedLoan) return
    const nextDue = Math.round(Number(selectedLoan.nextDueAmount || selectedLoan.installmentAmount || 0))
    if (nextDue > 0) setAmount(String(nextDue))
  }

  const submitSharePurchase = async (e) => {
    e.preventDefault()
    if (!canSendSharePurchase) return
    setSubmitting(true)
    setError('')
    try {
      const payload = await authFetch('/api/shareholding/purchase-from-main/', {
        method: 'POST',
        body: {
          shares: parsedShares,
          notes: note.trim() || undefined,
        },
      })
      if (payload.purchaseOptions) setShareOptions(payload.purchaseOptions)
      await reloadDashboard({ silent: true })
      if (typeof onSuccess === 'function') await onSuccess(payload)
      addToast(payload.message || 'Share purchase completed from Main Account.')
      onClose()
    } catch (err) {
      setError(err.message || 'Could not complete share purchase.')
    } finally {
      setSubmitting(false)
    }
  }

  const submitWscContribution = async (e) => {
    e.preventDefault()
    if (!canSendWsc) return
    setSubmitting(true)
    setError('')
    try {
      const payload = await authFetch('/api/projects/52wsc/contribute-from-main/', {
        method: 'POST',
        body: {
          amount: parsedAmount,
          notes: note.trim() || undefined,
        },
      })
      if (payload.contributeOptions) setWscOptions(payload.contributeOptions)
      await reloadDashboard({ silent: true })
      if (typeof onSuccess === 'function') await onSuccess(payload)
      addToast(payload.message || '52WSC contribution posted from Main Account.')
      onClose()
    } catch (err) {
      setError(err.message || 'Could not post 52WSC contribution.')
    } finally {
      setSubmitting(false)
    }
  }

  const submitGwcContribution = async (e) => {
    e.preventDefault()
    if (!canSendGwc) return
    setSubmitting(true)
    setError('')
    try {
      const payload = await authFetch('/api/projects/gwc/contribute-from-main/', {
        method: 'POST',
        body: {
          amount: parsedAmount,
          notes: note.trim() || undefined,
        },
      })
      if (payload.contributeOptions) setGwcOptions(payload.contributeOptions)
      await reloadDashboard({ silent: true })
      if (typeof onSuccess === 'function') await onSuccess(payload)
      addToast(payload.message || 'GWC deposit posted from Main Account.')
      onClose()
    } catch (err) {
      setError(err.message || 'Could not post GWC deposit.')
    } finally {
      setSubmitting(false)
    }
  }

  const submitCgfPurchase = async (e) => {
    e.preventDefault()
    if (!canSendCgf || !cgfPackage) return
    setSubmitting(true)
    setError('')
    try {
      const payload = await authFetch('/api/projects/cgf/purchase-from-main/', {
        method: 'POST',
        body: {
          packageId: cgfPackage.id,
          quantity: parsedCgfQuantity,
          notes: note.trim() || undefined,
        },
      })
      if (payload.purchaseOptions) setCgfOptions(payload.purchaseOptions)
      await reloadDashboard({ silent: true })
      if (typeof onSuccess === 'function') await onSuccess(payload)
      addToast(payload.message || 'CGF package purchased from Main Account.')
      onClose()
    } catch (err) {
      setError(err.message || 'Could not purchase CGF package.')
    } finally {
      setSubmitting(false)
    }
  }

  const submitRepContribution = async (e) => {
    e.preventDefault()
    if (!canSendRep || !repProject) return
    setSubmitting(true)
    setError('')
    try {
      const payload = await authFetch('/api/projects/rep/contribute-from-main/', {
        method: 'POST',
        body: {
          projectId: repProject.id,
          amount: parsedAmount,
          notes: note.trim() || undefined,
        },
      })
      if (payload.contributeOptions) setRepOptions(payload.contributeOptions)
      await reloadDashboard({ silent: true })
      if (typeof onSuccess === 'function') await onSuccess(payload)
      addToast(payload.message || 'Real Estate contribution posted from Main Account.')
      onClose()
    } catch (err) {
      setError(err.message || 'Could not post Real Estate contribution.')
    } finally {
      setSubmitting(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!canSendLoan || !selectedLoan) return
    setSubmitting(true)
    setError('')
    try {
      const payload = await submitLoanRepayment({
        loanId: selectedLoan.id,
        amount: parsedAmount,
        notes: note.trim(),
      })
      if (typeof onSuccess === 'function') await onSuccess(payload)
      onClose()
    } catch (err) {
      setError(err.message || 'Could not post loan repayment.')
    } finally {
      setSubmitting(false)
    }
  }

  return createPortal(
    <div className="modal-overlay" onClick={submitting ? undefined : onClose} role="presentation">
      <div
        className="modal modal-wide main-project-transfer-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="main-project-transfer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon">
            <ArrowLeftRight size={20} />
          </div>
          <div className="modal-head-text">
            <b id="main-project-transfer-title">
              {step === 'details' && selected ? selected.title : 'Use Main Account'}
            </b>
            <span>
              {step === 'details'
                ? isLoanFlow
                  ? `Available ${formatUGX(available || 0)} · choose a loan and amount`
                  : isShareFlow
                    ? `Available ${formatUGX(available || 0)} · choose share quantity`
                    : isWscFlow
                      ? `Available ${formatUGX(available || 0)} · enter a contribution amount`
                      : isGwcFlow
                        ? `Available ${formatUGX(available || 0)} · minimum ${formatUGX(gwcMinimum)}`
                        : isCgfFlow
                          ? `Available ${formatUGX(available || 0)} · choose an active CGF package`
                          : isRepFlow
                            ? `Available ${formatUGX(available || 0)} · choose a running project`
                            : `Available ${formatUGX(available || 0)} · coming next`
                : `Available ${formatUGX(available || 0)} · choose where to send funds`}
            </span>
          </div>
          <button
            type="button"
            className="modal-close"
            aria-label="Close"
            onClick={onClose}
            disabled={submitting}
          >
            <X size={18} />
          </button>
        </div>

        {step === 'choose' ? (
          <>
            <div className="modal-body main-project-choose-body">
              <section className="main-project-destination-list" aria-label="Main Account destinations">
                {DESTINATIONS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="main-project-destination"
                    onClick={() => chooseDestination(item)}
                  >
                    <span className="main-project-destination-icon">
                      <item.Icon size={18} />
                    </span>
                    <span>
                      <b>{item.title}</b>
                      <small>
                        {item.ready
                          ? item.detail
                          : `${item.detail} Available in a later update.`}
                      </small>
                    </span>
                  </button>
                ))}
              </section>
            </div>
            <div className="modal-foot">
              <button type="button" className="btn btn-outline" onClick={onClose}>
                Cancel
              </button>
            </div>
          </>
        ) : isLoanFlow ? (
          <form onSubmit={submit}>
            <div className="modal-body main-project-details-body">
              <section className="main-project-transfer-panel">
                <div className="main-project-transfer-summary">
                  <div>
                    <small>Main Account available</small>
                    <strong>{formatUGX(available || 0)}</strong>
                  </div>
                  <div>
                    <small>Active loans</small>
                    <strong>{loansLoading ? 'Checking…' : activeLoans.length}</strong>
                  </div>
                </div>

                {loansLoading && !activeLoans.length ? (
                  <p className="main-project-rule">Checking your active loans…</p>
                ) : null}

                {!loansLoading && activeLoans.length === 0 ? (
                  <p className="main-project-rule warn">
                    You do not have an active loan to repay from Main Account right now.
                  </p>
                ) : null}

                {activeLoans.length > 0 ? (
                  <div className="main-project-loan-picker" role="group" aria-label="Select loan">
                    <span className="main-project-loan-picker-label">Select loan</span>
                    {activeLoans.map((loan) => {
                      const isSelected = String(loan.id) === String(loanId)
                      return (
                        <button
                          key={loan.id}
                          type="button"
                          className={`main-project-loan-option${isSelected ? ' selected' : ''}`}
                          onClick={() => {
                            setLoanId(String(loan.id))
                            setAmount('')
                            setError('')
                          }}
                          disabled={submitting}
                        >
                          <span>
                            <b>{loan.reference}</b>
                            <small>{loan.purposeLabel || loan.purpose}</small>
                          </span>
                          <strong>{formatUGX(loan.outstanding)}</strong>
                        </button>
                      )
                    })}
                  </div>
                ) : null}

                {selectedLoan ? (
                  <>
                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Outstanding</small>
                        <strong>{formatUGX(selectedLoan.outstanding)}</strong>
                      </div>
                      <div>
                        <small>Next installment</small>
                        <strong>
                          {formatUGX(
                            selectedLoan.nextDueAmount || selectedLoan.installmentAmount || 0,
                          )}
                        </strong>
                      </div>
                    </div>

                    <label className="main-project-amount-field">
                      <span>Amount to repay</span>
                      <div className="main-project-amount-input">
                        <span>UGX</span>
                        <input
                          inputMode="numeric"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          placeholder="Enter amount"
                          autoFocus
                          disabled={submitting}
                        />
                      </div>
                    </label>

                    <div className="main-project-amount-shortcuts">
                      <button type="button" className="btn btn-ghost" onClick={setNextDue} disabled={submitting}>
                        Next installment
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={setFullOutstanding}
                        disabled={submitting}
                      >
                        Full outstanding
                      </button>
                    </div>

                    {!withinBalance && hasAmount ? (
                      <p className="main-project-rule warn">
                        Amount exceeds your available Main Account balance.
                      </p>
                    ) : null}

                    {!withinOutstanding && hasAmount ? (
                      <p className="main-project-rule warn">
                        Amount exceeds the outstanding balance on this loan.
                      </p>
                    ) : null}

                    <label className="main-project-note-field">
                      <span>Note or reference (optional)</span>
                      <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Add a short note for this repayment"
                        disabled={submitting}
                      />
                    </label>

                    <div className="main-project-preview">
                      <Wallet size={18} />
                      <div>
                        <b>Repayment preview</b>
                        <span>
                          {hasAmount
                            ? `${formatUGX(parsedAmount)} will leave Main Account and reduce ${selectedLoan.reference}.`
                            : 'Enter an amount to preview this repayment.'}
                        </span>
                      </div>
                    </div>
                  </>
                ) : null}

                {error ? <p className="main-project-rule warn">{error}</p> : null}
              </section>
            </div>

            <div className="modal-foot main-project-details-foot">
              <button
                type="button"
                className="btn btn-outline"
                onClick={goBackToOptions}
                disabled={submitting}
              >
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!canSendLoan}>
                  {submitting ? 'Sending…' : 'Send repayment'}
                </button>
              </div>
            </div>
          </form>
        ) : isShareFlow ? (
          <form onSubmit={submitSharePurchase}>
            <div className="modal-body main-project-details-body">
              <section className="main-project-transfer-panel">
                <div className="main-project-transfer-summary">
                  <div>
                    <small>Main Account available</small>
                    <strong>{formatUGX(available || 0)}</strong>
                  </div>
                  <div>
                    <small>Price per share</small>
                    <strong>{shareOptionsLoading ? 'Loading…' : formatUGX(pricePerShare)}</strong>
                  </div>
                </div>

                {shareOptionsLoading ? (
                  <p className="main-project-rule">Checking share price and tier thresholds…</p>
                ) : null}

                {shareOptions ? (
                  <>
                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Your current tier</small>
                        <strong>
                          {shareOptions.currentTierEmoji ? `${shareOptions.currentTierEmoji} ` : ''}
                          {shareOptions.currentTier || 'Standard'}
                        </strong>
                      </div>
                      <div>
                        <small>Current shares</small>
                        <strong>{shareOptions.currentSharesDisplay || formatShares(currentShares)}</strong>
                      </div>
                    </div>

                    <label className="main-project-amount-field">
                      <span>Number of shares to buy</span>
                      <div className="main-project-amount-input">
                        <span>Shares</span>
                        <input
                          inputMode="decimal"
                          value={shareQuantity}
                          onChange={(e) => setShareQuantity(e.target.value)}
                          placeholder="0.5, 1, 1.5…"
                          autoFocus
                          disabled={submitting}
                        />
                      </div>
                    </label>

                    <p className={`main-project-rule ${hasValidShareStep || !shareQuantity ? 'ok' : 'warn'}`}>
                      Shares are bought in steps of 0.5. Minimum purchase is 0.5 share.
                    </p>

                    {!shareCostWithinBalance && hasValidShareStep ? (
                      <p className="main-project-rule warn">
                        This purchase exceeds your available Main Account balance.
                      </p>
                    ) : null}

                    <div className="main-project-preview">
                      <Wallet size={18} />
                      <div>
                        <b>Share purchase preview</b>
                        <span>
                          {hasValidShareStep
                            ? `${formatShares(parsedShares)} share(s) will cost ${formatUGX(shareCost)}. You will move from ${formatShares(currentShares)} to ${formatShares(projectedShares)} shares${
                                projectedTier?.name ? ` and project as ${projectedTier.emoji ? `${projectedTier.emoji} ` : ''}${projectedTier.name}` : ''
                              }.`
                            : 'Enter shares in 0.5 steps to preview this purchase.'}
                        </span>
                      </div>
                    </div>

                    {nextTier ? (
                      <div className="main-project-tier-next">
                        <small>Next tier target</small>
                        <strong>
                          {nextTier.emoji ? `${nextTier.emoji} ` : ''}
                          {nextTier.name}
                        </strong>
                        <span>
                          {Number(nextTier.minValue || 0) > 0
                            ? `Reach portfolio value of ${formatUGX(nextTier.minValue)}.`
                            : `Reach ${nextTier.minSharesDisplay || formatShares(nextTier.minShares)} total shares.`}
                        </span>
                      </div>
                    ) : null}

                    <div className="main-project-tier-guide">
                      <div>
                        <b>What it takes to move tiers</b>
                        <small>Tier updates after each approved share purchase.</small>
                      </div>
                      <div className="main-project-tier-list">
                        {shareOptions.tierRequirements.map((tier) => (
                          <div key={tier.name} className="main-project-tier-row">
                            <span>
                              {tier.emoji ? `${tier.emoji} ` : ''}
                              {tier.name}
                            </span>
                            <strong>{tierRangeLabel(tier, shareOptions.tierRequirements)}</strong>
                          </div>
                        ))}
                      </div>
                    </div>

                    <label className="main-project-note-field">
                      <span>Note or reference (optional)</span>
                      <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Add a short note for this share purchase"
                        disabled={submitting}
                      />
                    </label>
                  </>
                ) : null}

                {error ? <p className="main-project-rule warn">{error}</p> : null}
              </section>
            </div>

            <div className="modal-foot main-project-details-foot">
              <button
                type="button"
                className="btn btn-outline"
                onClick={goBackToOptions}
                disabled={submitting}
              >
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!canSendSharePurchase}>
                  {submitting ? 'Purchasing…' : 'Buy shares'}
                </button>
              </div>
            </div>
          </form>
        ) : isWscFlow ? (
          <form onSubmit={submitWscContribution}>
            <div className="modal-body main-project-details-body">
              <section className="main-project-transfer-panel">
                <div className="main-project-transfer-summary">
                  <div>
                    <small>Main Account available</small>
                    <strong>{formatUGX(wscAvailable)}</strong>
                  </div>
                  <div>
                    <small>Cycle deposits</small>
                    <strong>{wscOptionsLoading ? 'Loading…' : formatUGX(wscDeposits)}</strong>
                  </div>
                </div>

                {wscOptionsLoading ? (
                  <p className="main-project-rule">Checking your 52WSC cycle progress…</p>
                ) : null}

                {wscOptions ? (
                  <>
                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Cycle progress</small>
                        <strong>
                          {Number(wscOptions.progressPercentage || 0).toFixed(1)}% · week{' '}
                          {wscOptions.nextWeekToCover || 1}/{wscOptions.totalWeeks || 52}
                        </strong>
                      </div>
                      <div>
                        <small>Target</small>
                        <strong>{formatUGX(wscTarget)}</strong>
                      </div>
                    </div>

                    {!wscCanContribute ? (
                      <p className="main-project-rule warn">
                        {wscOptions.blockMessage ||
                          'Complete your matured-cycle decision before contributing again.'}
                      </p>
                    ) : null}

                    <label className="main-project-amount-field">
                      <span>Amount to contribute</span>
                      <div className="main-project-amount-input">
                        <span>UGX</span>
                        <input
                          inputMode="numeric"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          placeholder="Enter amount"
                          autoFocus
                          disabled={submitting || !wscCanContribute}
                        />
                      </div>
                    </label>

                    {!withinBalance && hasAmount ? (
                      <p className="main-project-rule warn">
                        Amount exceeds your available Main Account balance.
                      </p>
                    ) : null}

                    <div className="main-project-preview">
                      <PiggyBank size={18} />
                      <div>
                        <b>Contribution preview</b>
                        <span>
                          {hasAmount
                            ? `${formatUGX(parsedAmount)} will leave Main Account and raise this cycle from ${formatUGX(wscDeposits)} to ${formatUGX(projectedWscDeposits)} (${projectedWscProgress.toFixed(1)}% of target).`
                            : 'Enter an amount to preview this 52WSC contribution.'}
                        </span>
                      </div>
                    </div>

                    <label className="main-project-note-field">
                      <span>Note or reference (optional)</span>
                      <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Add a short note for this contribution"
                        disabled={submitting || !wscCanContribute}
                      />
                    </label>
                  </>
                ) : null}

                {error ? <p className="main-project-rule warn">{error}</p> : null}
              </section>
            </div>

            <div className="modal-foot main-project-details-foot">
              <button
                type="button"
                className="btn btn-outline"
                onClick={goBackToOptions}
                disabled={submitting}
              >
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!canSendWsc}>
                  {submitting ? 'Sending…' : 'Send contribution'}
                </button>
              </div>
            </div>
          </form>
        ) : isGwcFlow ? (
          <form onSubmit={submitGwcContribution}>
            <div className="modal-body main-project-details-body">
              <section className="main-project-transfer-panel">
                <div className="main-project-transfer-summary">
                  <div>
                    <small>Main Account available</small>
                    <strong>{formatUGX(gwcAvailable)}</strong>
                  </div>
                  <div>
                    <small>Minimum deposit</small>
                    <strong>{gwcOptionsLoading ? 'Loading…' : formatUGX(gwcMinimum)}</strong>
                  </div>
                </div>

                {gwcOptionsLoading ? (
                  <p className="main-project-rule">Checking GWC deposit terms…</p>
                ) : null}

                {gwcOptions ? (
                  <>
                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Interest</small>
                        <strong>
                          {gwcInterestRate}% compound · {gwcTenureDays} days
                        </strong>
                      </div>
                      <div>
                        <small>Your GWC principal</small>
                        <strong>{formatUGX(gwcOptions.totalPrincipal || 0)}</strong>
                      </div>
                    </div>

                    <p className="main-project-rule ok">
                      Deposits from {formatUGX(gwcMonthlyRedeemableThreshold)} automatically
                      unlock monthly interest redemption. Smaller deposits pay out at maturity.
                    </p>

                    <label className="main-project-amount-field">
                      <span>Amount to deposit</span>
                      <div className="main-project-amount-input">
                        <span>UGX</span>
                        <input
                          inputMode="numeric"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          placeholder={String(gwcMinimum)}
                          autoFocus
                          disabled={submitting}
                        />
                      </div>
                    </label>

                    <div className="main-project-amount-shortcuts">
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => setAmount(String(gwcMinimum))}
                        disabled={submitting || gwcAvailable < gwcMinimum}
                      >
                        Minimum {formatUGX(gwcMinimum)}
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => setAmount(String(gwcMonthlyRedeemableThreshold))}
                        disabled={submitting || gwcAvailable < gwcMonthlyRedeemableThreshold}
                      >
                        Monthly interest {formatUGX(gwcMonthlyRedeemableThreshold)}
                      </button>
                    </div>

                    {hasAmount && !gwcMeetsMinimum ? (
                      <p className="main-project-rule warn">
                        GWC deposits require at least {formatUGX(gwcMinimum)}.
                      </p>
                    ) : null}

                    {hasAmount && parsedAmount > gwcAvailable ? (
                      <p className="main-project-rule warn">
                        Amount exceeds your available Main Account balance.
                      </p>
                    ) : null}

                    <div className="main-project-preview">
                      <Building2 size={18} />
                      <div>
                        <b>Deposit preview</b>
                        <span>
                          {hasAmount && gwcMeetsMinimum
                            ? `${formatUGX(parsedAmount)} will leave Main Account and open a new GWC fixed deposit at ${gwcInterestRate}% for ${gwcTenureDays} days. ${gwcGetsMonthlyInterest ? 'Monthly interest redemption will be enabled.' : `Interest will be payable at maturity unless the deposit reaches ${formatUGX(gwcMonthlyRedeemableThreshold)}.`}`
                            : `Enter at least ${formatUGX(gwcMinimum)} to preview this GWC deposit.`}
                        </span>
                      </div>
                    </div>

                    <label className="main-project-note-field">
                      <span>Note or reference (optional)</span>
                      <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Add a short note for this deposit"
                        disabled={submitting}
                      />
                    </label>
                  </>
                ) : null}

                {error ? <p className="main-project-rule warn">{error}</p> : null}
              </section>
            </div>

            <div className="modal-foot main-project-details-foot">
              <button
                type="button"
                className="btn btn-outline"
                onClick={goBackToOptions}
                disabled={submitting}
              >
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!canSendGwc}>
                  {submitting ? 'Sending…' : 'Open GWC deposit'}
                </button>
              </div>
            </div>
          </form>
        ) : isCgfFlow ? (
          <form onSubmit={submitCgfPurchase}>
            <div className="modal-body main-project-details-body" ref={detailsBodyRef}>
              <section className="main-project-transfer-panel">
                <div className="main-project-transfer-summary">
                  <div>
                    <small>Main Account available</small>
                    <strong>{formatUGX(cgfAvailable)}</strong>
                  </div>
                  <div>
                    <small>Package price</small>
                    <strong>{cgfOptionsLoading ? 'Loading…' : formatUGX(cgfUnitCost)}</strong>
                  </div>
                </div>

                {cgfOptionsLoading ? (
                  <p className="main-project-rule">Loading active CGF packages…</p>
                ) : null}

                {cgfPackage ? (
                  <>
                    <label className="main-project-amount-field">
                      <span>Select package</span>
                      <select
                        className="main-project-select"
                        value={cgfPackageId || String(cgfPackage.id)}
                        onChange={(e) => {
                          setCgfPackageId(e.target.value)
                          setCgfQuantity('1')
                          setError('')
                        }}
                        disabled={submitting || !cgfCanPurchase}
                        autoFocus
                      >
                        {cgfPackages.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name} · {formatUGX(item.totalCost)} · {item.cycleDurationMonths} months
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Term</small>
                        <strong>{cgfPackage.cycleDurationMonths} months</strong>
                      </div>
                      <div>
                        <small>Starting stock</small>
                        <strong>{cgfPackage.goatCount} female breeders</strong>
                      </div>
                    </div>

                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Expected harvest</small>
                        <strong>
                          {cgfPackage.harvestGoats} goats ({cgfPackage.goatCount} + {cgfPackage.expectedKids} kids)
                        </strong>
                      </div>
                      <div>
                        <small>Cash-out at maturity</small>
                        <strong>{formatUGX(cgfPackage.expectedCashout)}</strong>
                      </div>
                    </div>

                    <p className="main-project-rule ok">
                      Gain if you cash out: {formatUGX(cgfGain)} above the {formatUGX(cgfPackage.totalCost)}{' '}
                      package price ({formatUGX(cgfPackage.cashoutPerGoat)} per goat). At month{' '}
                      {cgfPackage.cycleDurationMonths} you can take all {cgfPackage.harvestGoats} goats
                      physically or cash out to Main Account.
                    </p>

                    {!cgfCanPurchase && cgfOptions?.blockMessage ? (
                      <p className="main-project-rule warn">{cgfOptions.blockMessage}</p>
                    ) : null}

                    <label className="main-project-amount-field">
                      <span>Number of packages</span>
                      <div className="main-project-amount-input">
                        <span>Qty</span>
                        <input
                          inputMode="numeric"
                          value={cgfQuantity}
                          onChange={(e) => setCgfQuantity(e.target.value)}
                          placeholder="1"
                          disabled={submitting || !cgfCanPurchase}
                        />
                      </div>
                    </label>

                    {cgfTotalCost > cgfAvailable && parsedCgfQuantity >= 1 ? (
                      <p className="main-project-rule warn">
                        {formatUGX(cgfTotalCost)} exceeds your available Main Account balance.
                      </p>
                    ) : null}

                    <div className="main-project-preview">
                      <Sprout size={18} />
                      <div>
                        <b>Purchase preview</b>
                        <span>
                          {parsedCgfQuantity} × {cgfPackage.name} will cost {formatUGX(cgfTotalCost)},
                          add {parsedCgfQuantity * Number(cgfPackage.goatCount || 0)} female breeders,
                          and target {cgfHarvestGoats} goats at month {cgfPackage.cycleDurationMonths}
                          {cgfOptions?.farmName ? ` at ${cgfOptions.farmName}` : ''}. Cash-out value
                          would be {formatUGX(cgfExpectedCashout)}.
                        </span>
                      </div>
                    </div>

                    <label className="main-project-note-field">
                      <span>Note or reference (optional)</span>
                      <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Add a short note for this package purchase"
                        disabled={submitting || !cgfCanPurchase}
                      />
                    </label>
                  </>
                ) : !cgfOptionsLoading ? (
                  <p className="main-project-rule warn">
                    {cgfOptions?.blockMessage || 'No CGF package is open for purchase right now.'}
                  </p>
                ) : null}

                {error ? <p className="main-project-rule warn">{error}</p> : null}
              </section>
            </div>

            <div className="modal-foot main-project-details-foot">
              <button
                type="button"
                className="btn btn-outline"
                onClick={goBackToOptions}
                disabled={submitting}
              >
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!canSendCgf}>
                  {submitting ? 'Purchasing…' : 'Buy CGF package'}
                </button>
              </div>
            </div>
          </form>
        ) : isRepFlow ? (
          <form onSubmit={submitRepContribution}>
            <div className="modal-body main-project-details-body" ref={detailsBodyRef}>
              <section className="main-project-transfer-panel">
                <div className="main-project-transfer-summary">
                  <div>
                    <small>Main Account available</small>
                    <strong>{formatUGX(repAvailable)}</strong>
                  </div>
                  <div>
                    <small>Already paid</small>
                    <strong>
                      {repOptionsLoading
                        ? 'Loading…'
                        : formatUGX(repProject?.alreadyPaid || 0)}
                    </strong>
                  </div>
                </div>

                {repOptionsLoading ? (
                  <p className="main-project-rule">Loading running Real Estate projects…</p>
                ) : null}

                {repProject ? (
                  <>
                    <label className="main-project-amount-field">
                      <span>Select project</span>
                      <select
                        className="main-project-select"
                        value={repProjectId || String(repProject.id)}
                        onChange={(e) => {
                          setRepProjectId(e.target.value)
                          setAmount('')
                          setError('')
                        }}
                        disabled={submitting || !repCanContribute}
                        autoFocus
                      >
                        {repProjects.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name}
                            {item.location ? ` · ${item.location}` : ''}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Location</small>
                        <strong>{repProject.location || '—'}</strong>
                      </div>
                      <div>
                        <small>Minimum investment</small>
                        <strong>{repProject.minimumInvestment || 'No minimum listed'}</strong>
                      </div>
                    </div>

                    <div className="main-project-transfer-summary">
                      <div>
                        <small>Start</small>
                        <strong>{repProject.startDate || '—'}</strong>
                      </div>
                      <div>
                        <small>Ends</small>
                        <strong>{repProject.endDate || '—'}</strong>
                      </div>
                    </div>

                    {repProject.landSizeLabel ? (
                      <p className="main-project-rule ok">
                        Land size: {repProject.landSizeLabel}.
                        {repProject.description ? ` ${repProject.description}` : ''}
                      </p>
                    ) : repProject.description ? (
                      <p className="main-project-rule ok">{repProject.description}</p>
                    ) : null}

                    {!repCanContribute && repOptions?.blockMessage ? (
                      <p className="main-project-rule warn">{repOptions.blockMessage}</p>
                    ) : null}

                    <label className="main-project-amount-field">
                      <span>Amount to contribute</span>
                      <div className="main-project-amount-input">
                        <span>UGX</span>
                        <input
                          inputMode="numeric"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          placeholder="0"
                          disabled={submitting || !repCanContribute}
                        />
                      </div>
                    </label>

                    <div className="main-project-amount-shortcuts">
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => setAmount(String(Math.round(repAvailable)))}
                        disabled={submitting || !repCanContribute || repAvailable <= 0}
                      >
                        Use available {formatUGX(repAvailable)}
                      </button>
                    </div>

                    {hasAmount && parsedAmount > repAvailable ? (
                      <p className="main-project-rule warn">
                        Amount exceeds your available Main Account balance.
                      </p>
                    ) : null}

                    <div className="main-project-preview">
                      <Home size={18} />
                      <div>
                        <b>Contribution preview</b>
                        <span>
                          {hasAmount
                            ? `${formatUGX(parsedAmount)} will leave Main Account and post to ${repProject.name}. Your paid total on this project will become ${formatUGX((Number(repProject.alreadyPaid) || 0) + parsedAmount)}.`
                            : `Enter an amount to send to ${repProject.name}.`}
                        </span>
                      </div>
                    </div>

                    <label className="main-project-note-field">
                      <span>Note or reference (optional)</span>
                      <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Add a short note for this contribution"
                        disabled={submitting || !repCanContribute}
                      />
                    </label>
                  </>
                ) : !repOptionsLoading ? (
                  <p className="main-project-rule warn">
                    {repOptions?.blockMessage ||
                      'You do not have an open Real Estate project to pay into yet.'}
                  </p>
                ) : null}

                {error ? <p className="main-project-rule warn">{error}</p> : null}
              </section>
            </div>

            <div className="modal-foot main-project-details-foot">
              <button
                type="button"
                className="btn btn-outline"
                onClick={goBackToOptions}
                disabled={submitting}
              >
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!canSendRep}>
                  {submitting ? 'Sending…' : 'Pay real estate project'}
                </button>
              </div>
            </div>
          </form>
        ) : (
          <>
            <div className="modal-body main-project-details-body">
              <section className="main-project-transfer-panel">
                <div className="main-project-preview">
                  <Wallet size={18} />
                  <div>
                    <b>{selected?.title}</b>
                    <span>
                      Paying this destination from Main Account is next. Loan repayments, share
                      purchases, 52WSC, GWC, CGF, and Real Estate are available now.
                    </span>
                  </div>
                </div>
              </section>
            </div>
            <div className="modal-foot main-project-details-foot">
              <button type="button" className="btn btn-outline" onClick={goBackToOptions}>
                <ArrowLeft size={15} />
                Back to options
              </button>
              <div className="main-project-details-foot-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose}>
                  Cancel
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body,
  )
}
