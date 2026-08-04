import { useState } from 'react'
import {
  Award,
  BriefcaseBusiness,
  Clock3,
  FileText,
  Info,
  Landmark,
  Layers3,
  ShoppingCart,
  Star,
  Wallet,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'

export default function PortfolioSummary() {
  const { authFetch } = useAuth()
  const {
    totals,
    myProjects,
    shareholding,
    mainAccount,
    pendingRequests,
    isShareholder,
    addToast,
    reloadDashboard,
  } = useMember()
  const [claiming, setClaiming] = useState(false)
  const sharesLabel = shareholding.sharesHeldDisplay || String(shareholding.sharesHeld || 0)
  const eligibleLabel =
    shareholding.dividendEligibleDisplay || String(shareholding.dividendEligible || 0)
  const memberSinceLabel = shareholding.yearJoined || shareholding.memberSince || '—'
  const certificateLabel = shareholding.certificateStatus || 'Not issued'
  const earnedDividend = Number(shareholding.expectedDividend || 0)
  const canClaim = Boolean(shareholding.canClaimDividend)
  const claimPending = Boolean(shareholding.dividendClaimPending)
  const electionOpen = Boolean(shareholding.electionOpen)
  const claimBlockMessage =
    shareholding.dividendClaimBlockMessage ||
    (!electionOpen
      ? 'Dividends are not ready for claim.'
      : claimPending
        ? 'Your dividend claim is already awaiting administrator approval.'
        : 'You do not have claimable dividends right now.')

  const handleClaimDividends = async () => {
    if (claiming) return
    if (!canClaim) {
      addToast(claimBlockMessage)
      return
    }

    setClaiming(true)
    try {
      const payload = await authFetch('/api/shareholding/claim-dividend/', {
        method: 'POST',
        body: {},
      })
      addToast(
        payload.detail ||
          'Dividend claim submitted. After approval, the amount will be credited to your Main Account.',
      )
      await reloadDashboard({ silent: true })
    } catch (err) {
      addToast(err.message || 'Could not submit dividend claim.')
    } finally {
      setClaiming(false)
    }
  }

  return (
    <>
      <section className="summary-strip">
        <article className="stat-tile">
          <div className="stat-tile-top">
            <div className="stat-icon portfolio">
              <BriefcaseBusiness size={18} />
            </div>
            <div className="k">Your portfolio</div>
          </div>
          <div className="v">{formatUGX(totals.totalPortfolio)}</div>
          <div className="h">Main + projects + shares</div>
        </article>
        <article className="stat-tile">
          <div className="stat-tile-top">
            <div className="stat-icon projects">
              <Layers3 size={18} />
            </div>
            <div className="k">Invested in Projects</div>
          </div>
          <div className="v">{formatUGX(totals.invested)}</div>
          <div className="h">{myProjects.length} active projects</div>
        </article>
        <article className="stat-tile">
          <div className="stat-tile-top">
            <div className="stat-icon shares">
              <Landmark size={18} />
            </div>
            <div className="k">Share value</div>
          </div>
          <div className="v">
            {isShareholder ? formatUGX(shareholding.portfolioValue) : '—'}
          </div>
          <div className="h">
            {isShareholder ? `${sharesLabel} shares` : 'Not a shareholder'}
          </div>
        </article>
        <article className="stat-tile">
          <div className="stat-tile-top">
            <div className="stat-icon pending">
              <Clock3 size={18} />
            </div>
            <div className="k">Pending requests</div>
          </div>
          <div className="v">{pendingRequests.length}</div>
          <div className="h">{formatUGX(totals.pendingWithheld || mainAccount.pendingWithdrawal)} withheld</div>
        </article>
      </section>

      <section className="section" id="shares">
        <div className="section-head">
          <div>
            <h2>Cooperative Shareholding</h2>
            <p className="section-note">Your equity in Mushana Cooperative</p>
          </div>
        </div>

        <div className={`equity-card ${isShareholder ? '' : 'empty'}`.trim()}>
          {isShareholder ? (
            <div className="equity-inner">
              <div className="equity-header">
                <div className="equity-badge">
                  <Landmark size={20} />
                </div>
                <div className="equity-title">
                  <b>Shareholder Equity</b>
                  <span>
                    Member since {memberSinceLabel}
                    {certificateLabel ? ` · Certificate: ${certificateLabel}` : ''}
                  </span>
                </div>
                <div className="tier-chip">
                  <Star size={14} />
                  {shareholding.tierEmoji ? `${shareholding.tierEmoji} ` : ''}
                  {shareholding.tier || 'Shareholder'}
                </div>
              </div>

              <div className="equity-metrics">
                <div className="eq-metric">
                  <div className="lbl">Shares held</div>
                  <div className="val">
                    {sharesLabel}
                    <span className="cur"> shares</span>
                  </div>
                </div>
                <div className="eq-metric">
                  <div className="lbl">Portfolio value</div>
                  <div className="val">{formatUGX(shareholding.portfolioValue)}</div>
                </div>
                <div className="eq-metric">
                  <div className="lbl">Dividend eligible</div>
                  <div className="val">
                    {eligibleLabel}
                    <span className="cur"> shares</span>
                  </div>
                </div>
                <div className="eq-metric eq-metric-claim">
                  <div className="lbl">Earned dividends</div>
                  <div className="eq-claim-row">
                    <div className="val accent">{formatUGX(earnedDividend)}</div>
                    <button
                      type="button"
                      className={`btn-claim-dividend${canClaim ? '' : ' is-muted'}`}
                      onClick={handleClaimDividends}
                      disabled={claiming}
                      title={
                        canClaim
                          ? 'Transfer earned dividends to Main Account'
                          : claimBlockMessage
                      }
                    >
                      <Wallet size={14} />
                      {claiming ? 'Claiming…' : claimPending ? 'Claim pending' : 'Claim'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="equity-foot">
                <div className="note">
                  <Info size={15} />
                  {claimPending
                    ? 'Your dividend claim is awaiting approval. Once approved it will appear on your Main Account for withdrawal.'
                    : !electionOpen
                      ? 'Dividends are not ready for claim.'
                      : canClaim
                        ? 'Claim earned dividends to move them to your Main Account for withdrawal.'
                        : claimBlockMessage}
                </div>
                <div className="equity-actions">
                  <button
                    type="button"
                    className="btn-equity"
                    onClick={() => addToast('Buying shares is still under development')}
                  >
                    <ShoppingCart size={15} />
                    Buy more shares
                  </button>
                  <button
                    type="button"
                    className="btn-equity outline"
                    onClick={() => addToast('Shareholding statement is still under development')}
                  >
                    <FileText size={15} />
                    Statement
                  </button>
                  <button
                    type="button"
                    className="btn-equity outline"
                    onClick={() => addToast('Share certificate download is still under development')}
                  >
                    <Award size={15} />
                    Certificate
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="equity-empty">
              <div className="equity-empty-icon">
                <Landmark size={28} />
              </div>
              <h3>
                {shareholding.displayState === 'pending_setup'
                  ? 'Shareholding setup is pending'
                  : 'You are not a shareholder yet'}
              </h3>
              <p>
                {shareholding.displayState === 'pending_setup'
                  ? 'You have Cooperative Shareholding access, but your shareholding record has not been set up yet. Please contact the office.'
                  : "You are a valued cooperative member, but you don't hold cooperative shares. Shareholders earn annual dividends and gain voting rights. Contact the office to learn how to buy shares."}
              </p>
              <div className="equity-empty-actions">
                <button
                  type="button"
                  className="btn-equity"
                  onClick={() => addToast('Buying shares is still under development')}
                >
                  <ShoppingCart size={15} />
                  Buy shares
                </button>
                <button
                  type="button"
                  className="btn-equity outline"
                  onClick={() => addToast('Shareholding help is still under development')}
                >
                  <Info size={15} />
                  Learn about shares
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  )
}
