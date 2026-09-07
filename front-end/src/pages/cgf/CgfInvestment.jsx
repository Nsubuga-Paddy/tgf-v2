import {
  Calculator,
  Check,
  Clock,
  Crown,
  HelpCircle,
  Info,
  LineChart,
  PiggyBank,
  Shield,
  Sprout,
} from 'lucide-react'
import CgfShell from '../../components/cgf/CgfShell'
import { CGF_CURRENT_INVESTMENTS, CGF_PACKAGES } from '../../data/cgfData'
import { useMember } from '../../context/MemberContext'
import { formatUGX } from '../../utils/format'

function Badge({ tone, children }) {
  return <span className={`cgf-badge cgf-badge-${tone}`}>{children}</span>
}

export default function CgfInvestment() {
  const { addToast } = useMember()

  const invest = (pkg) => {
    addToast(`${pkg.name} invest option is still under development`)
  }

  return (
    <CgfShell title="Investment Packages">
      <section className="cgf-hero">
        <div>
          <h2>Investment Packages</h2>
          <p>Choose your investment package and start your goat farming journey</p>
        </div>
      </section>

      <section className="cgf-package-grid">
        {CGF_PACKAGES.map((pkg) => (
          <article key={pkg.id} className="cgf-card cgf-package">
            <div className="cgf-card-head">
              <h3>
                {pkg.icon === 'crown' ? <Crown size={18} /> : <Sprout size={18} />}
                {pkg.name}
              </h3>
            </div>
            <div className="cgf-package-body">
              <div className="cgf-package-hero">
                <Sprout size={40} />
                <h4>
                  {pkg.goatCount} Female Goat{pkg.goatCount === 1 ? '' : 's'}
                </h4>
                <strong>{formatUGX(pkg.price)}</strong>
                <p>{pkg.summary}</p>
              </div>
              <ul className="cgf-feature-list">
                {pkg.features.map((feature) => (
                  <li key={feature}>
                    <Check size={15} className="ok" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <button type="button" className="btn btn-primary cgf-full-btn" onClick={() => invest(pkg)}>
                Invest Now
              </button>
            </div>
          </article>
        ))}
      </section>

      <section className="cgf-card">
        <div className="cgf-card-head">
          <h3>
            <HelpCircle size={18} />
            Frequently Asked Questions
          </h3>
        </div>
        <div className="cgf-faq-grid">
          <div>
            <h4>
              <Clock size={15} />
              Timeline Questions
            </h4>
            <div className="cgf-faq-item">
              <strong>How long until I see returns?</strong>
              <p>
                Timelines now follow the package terms. Existing packages may remain on their
                original 14-month cycle, while newer packages can use the updated 18-month cycle.
              </p>
            </div>
            <div className="cgf-faq-item">
              <strong>When do goats start breeding?</strong>
              <p>
                Female goats are immediately allocated and begin breeding within 1–2 months of
                purchase.
              </p>
            </div>
            <div className="cgf-faq-item">
              <strong>How often do goats breed?</strong>
              <p>Goats can breed every 8 months, allowing for multiple breeding cycles.</p>
            </div>
          </div>
          <div>
            <h4>
              <Calculator size={15} />
              Returns & Investment
            </h4>
            <div className="cgf-faq-item">
              <strong>How many kids per goat?</strong>
              <p>
                Each package defines expected kids per goat (default 2). Admins set this when
                creating packages.
              </p>
            </div>
            <div className="cgf-faq-item">
              <strong>What&apos;s the total ROI?</strong>
              <p>
                Total return = original goats + (goats × kids per goat). Varies by package (e.g. 2
                goats × 2 kids = 4, total 6).
              </p>
            </div>
            <div className="cgf-faq-item">
              <strong>Can I sell the goats?</strong>
              <p>Yes! Mature goats can be sold or kept for further breeding cycles.</p>
            </div>
          </div>
          <div>
            <h4>
              <Shield size={15} />
              Management & Care
            </h4>
            <div className="cgf-faq-item">
              <strong>Who manages the goats?</strong>
              <p>Professional farm managers handle all daily operations, feeding, and care.</p>
            </div>
            <div className="cgf-faq-item">
              <strong>What about health issues?</strong>
              <p>Regular veterinary checkups and health monitoring are included in the package.</p>
            </div>
            <div className="cgf-faq-item">
              <strong>How do I track progress?</strong>
              <p>Monthly progress reports and photos are provided through your dashboard.</p>
            </div>
          </div>
        </div>
        <div className="cgf-notes">
          <h4>
            <Info size={15} />
            Important Notes
          </h4>
          <div className="cgf-notes-grid">
            <div>
              <strong>Breeding Success Rate</strong>
              <p>95% success rate with professional management</p>
            </div>
            <div>
              <strong>Contract Terms</strong>
              <p>Clear terms with guaranteed goat allocation</p>
            </div>
            <div>
              <strong>Market Value</strong>
              <p>Goat prices remain stable and growing</p>
            </div>
          </div>
        </div>
      </section>

      <section className="cgf-card">
        <div className="cgf-card-head">
          <h3>
            <LineChart size={18} />
            Your Current Investments
          </h3>
        </div>
        <div className="cgf-table-wrap">
          {CGF_CURRENT_INVESTMENTS.length === 0 ? (
            <div className="cgf-empty">
              <PiggyBank size={40} />
              <p>You haven&apos;t made any investments yet</p>
            </div>
          ) : (
            <table className="cgf-table">
              <thead>
                <tr>
                  <th>Package</th>
                  <th>Investment Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Expected Returns</th>
                </tr>
              </thead>
              <tbody>
                {CGF_CURRENT_INVESTMENTS.map((inv) => (
                  <tr key={inv.id}>
                    <td>{inv.packageName}</td>
                    <td>{inv.investmentDate}</td>
                    <td>{formatUGX(inv.amount)}</td>
                    <td>
                      <Badge tone={inv.statusColor}>{inv.status}</Badge>
                    </td>
                    <td>{inv.expectedReturns} goats</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </CgfShell>
  )
}
