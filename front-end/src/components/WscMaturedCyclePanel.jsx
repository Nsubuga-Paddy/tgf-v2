import { useMemo, useState } from 'react'
import {
  ArrowLeftRight,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  Wallet,
  X,
} from 'lucide-react'
import { maturedTotals } from '../data/savings52Data'
import { formatUGX } from '../utils/format'

/**
 * Frontend-only matured-cycle decision UI.
 * Backend wiring comes after design sign-off.
 */
export default function WscMaturedCyclePanel({
  cycle,
  onStartNewCycle,
  onTransferAll,
  onTransferMaturedPot,
}) {
  const [chooserOpen, setChooserOpen] = useState(false)
  const [confirm, setConfirm] = useState(null) // 'new_cycle' | 'transfer_all' | null
  const totals = useMemo(() => maturedTotals(cycle), [cycle])

  if (!cycle) return null

  const awaiting = cycle.status === 'awaiting_decision'
  const newCycleStarted = cycle.status === 'new_cycle_started'
  const allTransferred = cycle.status === 'all_transferred'

  const closeAll = () => {
    setChooserOpen(false)
    setConfirm(null)
  }

  return (
    <>
      <section className={`wsc-matured-panel ${awaiting ? 'awaiting' : ''}`}>
        <div className="wsc-matured-head">
          <div>
            <span className="wsc-matured-kicker">
              <Sparkles size={14} />
              Matured cycle
            </span>
            <h3>{cycle.label || '52WSC cycle'}</h3>
            <p>
              Started {cycle.startDate} · Matured {cycle.maturedOn} · {cycle.weeksCompleted}/52
              weeks complete
            </p>
          </div>
          <span className="wsc-matured-status">
            <CheckCircle2 size={14} />
            {awaiting
              ? 'Action needed'
              : newCycleStarted
                ? 'New cycle started'
                : allTransferred
                  ? 'Transferred'
                  : 'Matured'}
          </span>
        </div>

        <div className="wsc-matured-breakdown">
          <div>
            <span>Amount saved</span>
            <b>{formatUGX(totals.amountSaved)}</b>
          </div>
          <div>
            <span>Interest earned</span>
            <b>{formatUGX(totals.interestEarned)}</b>
            <small>15% annualized · daily accrual</small>
          </div>
          <div className="bf">
            <span>Balance brought forward</span>
            <b>{formatUGX(totals.balanceBroughtForward)}</b>
            <small>Leftover after week 52</small>
          </div>
          <div className="total">
            <span>Total if transferred together</span>
            <b>{formatUGX(totals.transferAll)}</b>
          </div>
        </div>

        {awaiting ? (
          <div className="wsc-matured-cta">
            <p>
              Choose what to do with the leftover BF: seed your next cycle, or send everything
              (saved + interest + BF) to your Main Account.
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setChooserOpen(true)}
            >
              Choose next step
            </button>
          </div>
        ) : null}

        {newCycleStarted ? (
          <div className="wsc-matured-outcome">
            <div className="wsc-outcome-card seed">
              <RefreshCw size={18} />
              <div>
                <b>New cycle opened with BF</b>
                <p>
                  {formatUGX(totals.balanceBroughtForward)} is the opening balance for Cycle 2.
                  Week 1 funding can continue from deposits.
                </p>
              </div>
            </div>
            <div className="wsc-outcome-card pot">
              <Wallet size={18} />
              <div>
                <b>Matured pot still available</b>
                <p>
                  {formatUGX(totals.maturedPot)} (saved + interest) can be transferred to Main
                  Account anytime.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => onTransferMaturedPot?.(totals)}
              >
                Transfer matured pot
              </button>
            </div>
          </div>
        ) : null}

        {allTransferred ? (
          <div className="wsc-matured-outcome">
            <div className="wsc-outcome-card done">
              <ArrowLeftRight size={18} />
              <div>
                <b>Everything moved to Main Account</b>
                <p>
                  {formatUGX(totals.transferAll)} credited (saved + interest + BF). A new cycle
                  starts when you make your next deposit.
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {chooserOpen ? (
        <div className="wsc-choice-backdrop" role="presentation" onClick={closeAll}>
          <div
            className="wsc-choice-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="wsc-choice-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="wsc-choice-head">
              <div>
                <h3 id="wsc-choice-title">Matured cycle · next step</h3>
                <p>Your 52 weeks are complete. Pick how to handle the leftover BF.</p>
              </div>
              <button type="button" className="wsc-choice-close" aria-label="Close" onClick={closeAll}>
                <X size={16} />
              </button>
            </div>

            {!confirm ? (
              <div className="wsc-choice-grid">
                <button
                  type="button"
                  className="wsc-choice-card"
                  onClick={() => setConfirm('new_cycle')}
                >
                  <RefreshCw size={20} />
                  <strong>Start a new cycle with BF</strong>
                  <p>
                    Use {formatUGX(totals.balanceBroughtForward)} as the opening balance for
                    Cycle 2.
                  </p>
                  <ul>
                    <li>BF seeds the new cycle</li>
                    <li>
                      Matured pot {formatUGX(totals.maturedPot)} stays available to transfer to
                      Main Account
                    </li>
                  </ul>
                </button>

                <button
                  type="button"
                  className="wsc-choice-card alt"
                  onClick={() => setConfirm('transfer_all')}
                >
                  <ArrowLeftRight size={20} />
                  <strong>Transfer everything to Main Account</strong>
                  <p>
                    Send saved + interest + BF together ({formatUGX(totals.transferAll)}).
                  </p>
                  <ul>
                    <li>Full amount goes to Main Account</li>
                    <li>New cycle begins on your next deposit</li>
                  </ul>
                </button>
              </div>
            ) : (
              <div className="wsc-choice-confirm">
                {confirm === 'new_cycle' ? (
                  <>
                    <h4>Confirm: start Cycle 2 with BF?</h4>
                    <p>
                      Opening balance: <b>{formatUGX(totals.balanceBroughtForward)}</b>
                      <br />
                      Matured pot kept for later transfer:{' '}
                      <b>{formatUGX(totals.maturedPot)}</b>
                    </p>
                  </>
                ) : (
                  <>
                    <h4>Confirm: transfer everything?</h4>
                    <p>
                      Main Account credit: <b>{formatUGX(totals.transferAll)}</b>
                      <br />
                      Includes saved {formatUGX(totals.amountSaved)} + interest{' '}
                      {formatUGX(totals.interestEarned)} + BF{' '}
                      {formatUGX(totals.balanceBroughtForward)}.
                    </p>
                  </>
                )}
                <div className="wsc-choice-confirm-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setConfirm(null)}>
                    Back
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      if (confirm === 'new_cycle') onStartNewCycle?.(totals)
                      else onTransferAll?.(totals)
                      closeAll()
                    }}
                  >
                    {confirm === 'new_cycle' ? 'Start new cycle' : 'Transfer all'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  )
}
