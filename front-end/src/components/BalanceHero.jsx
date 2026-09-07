import { useState } from 'react'
import { ArrowLeftRight, ArrowUpFromLine, CheckCircle2, History } from 'lucide-react'
import { useMember } from '../context/MemberContext'
import { formatUGX, greetingForNow } from '../utils/format'
import MainAccountProjectsModal from './MainAccountProjectsModal'
import RequestWithdrawModal from './RequestWithdrawModal'
import TransactionHistoryModal from './TransactionHistoryModal'

export default function BalanceHero() {
  const { member, mainAccount } = useMember()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [withdrawOpen, setWithdrawOpen] = useState(false)
  const [projectsOpen, setProjectsOpen] = useState(false)

  return (
    <div id="home">
      <div className="hero-grid">
        <section className="welcome-card">
          <div className="greet-hello">{greetingForNow()},</div>
          <h2 className="greet-name">{member.fullName}</h2>
          <div className="greet-row">
            {member.isVerified ? (
              <span className="pill ok">
                <CheckCircle2 size={12} />
                Verified member
              </span>
            ) : null}
            <span className="acct-chip">{member.accountNumber}</span>
          </div>
        </section>

        <section className="balance-card">
          <div className="balance-label">Main account balance. Available for withdraw</div>
          <div className="balance-amount">{formatUGX(mainAccount.available)}</div>
          <div className="balance-actions">
            <button
              type="button"
              className="btn btn-light"
              onClick={() => setWithdrawOpen(true)}
            >
              <ArrowUpFromLine size={16} />
              Request withdraw
            </button>
            <button
              type="button"
              className="btn btn-ghost-light"
              onClick={() => setProjectsOpen(true)}
            >
              <ArrowLeftRight size={16} />
              Use Main Account
            </button>
            <button
              type="button"
              className="btn btn-ghost-light"
              onClick={() => setHistoryOpen(true)}
            >
              <History size={16} />
              Transaction history
            </button>
          </div>
        </section>
      </div>

      <TransactionHistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <RequestWithdrawModal open={withdrawOpen} onClose={() => setWithdrawOpen(false)} />
      <MainAccountProjectsModal
        open={projectsOpen}
        onClose={() => setProjectsOpen(false)}
        available={mainAccount.available}
      />
    </div>
  )
}
