import { Link } from 'react-router-dom'

export default function AccountVerifiedEmail() {
  return (
    <div className="verification-page email-preview-page">
      <main className="email-preview-card">
        <div className="email-preview-label">Email preview</div>
        <h1>Your MCS account has been verified</h1>

        <div className="email-preview-body">
          <p>Hello Sarah,</p>
          <p>
            Great news — your MCS account has been verified. You can now sign in and use
            the member portal.
          </p>
          <p>
            <strong>Sign in here:</strong>
            <br />
            <Link to="/login">http://127.0.0.1:4173/login</Link>
          </p>
          <p>
            <strong>Your MCS account number:</strong> MCSTGF-NS0042
          </p>
          <p>
            If you requested access to specific MCS groups, an administrator will approve
            each project separately. You can check the status of those requests after you
            sign in.
          </p>
          <p>If you did not create this account, please contact MCS support.</p>
          <p>
            — Mushana Multipurpose Cooperative Society (MCS)
            <br />
            http://127.0.0.1:4173
          </p>
        </div>

        <div className="email-preview-actions">
          <Link to="/login" className="btn btn-primary">
            Go to login
          </Link>
          <Link to="/verification-pending" className="btn btn-outline">
            Back to pending page
          </Link>
        </div>
      </main>
    </div>
  )
}
