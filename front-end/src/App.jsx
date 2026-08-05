import { Navigate, Route, Routes } from 'react-router-dom'
import AccountVerifiedEmail from './pages/AccountVerifiedEmail'
import ForgotPassword from './pages/ForgotPassword'
import HelpCenter from './pages/HelpCenter'
import Home from './pages/Home'
import Login from './pages/Login'
import PasswordResetComplete from './pages/PasswordResetComplete'
import Profile from './pages/Profile'
import ProtectionBenefits from './pages/ProtectionBenefits'
import RealEstateDashboard from './pages/RealEstateDashboard'
import RealEstateProjectDetail from './pages/RealEstateProjectDetail'
import ResetPassword from './pages/ResetPassword'
import CgfDashboard from './pages/cgf/CgfDashboard'
import CgfInvestment from './pages/cgf/CgfInvestment'
import CgfTransactions from './pages/cgf/CgfTransactions'
import SessionTimeoutBanner from './components/SessionTimeoutBanner'
import { useAuth } from './context/AuthContext'
import GenerationalWealth from './pages/GenerationalWealth'
import Savings52Challenge from './pages/Savings52Challenge'
import SignUp from './pages/SignUp'
import VerificationPending from './pages/VerificationPending'

function RequireAuth({ children }) {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (user?.is_verified === false) return <Navigate to="/verification-pending" replace />
  return children
}

function GuestOnly({ children }) {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return children
  if (user?.is_verified === false) return <Navigate to="/verification-pending" replace />
  return <Navigate to="/" replace />
}

function AuthenticatedOverlays() {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return null
  return <SessionTimeoutBanner />
}

export default function App() {
  return (
    <>
      <AuthenticatedOverlays />
      <Routes>
      <Route path="/" element={<RequireAuth><Home /></RequireAuth>} />
      <Route path="/protection" element={<RequireAuth><ProtectionBenefits /></RequireAuth>} />
      <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
      <Route path="/projects/52wsc" element={<RequireAuth><Savings52Challenge /></RequireAuth>} />
      <Route path="/projects/gwc" element={<RequireAuth><GenerationalWealth /></RequireAuth>} />
      <Route path="/projects/cgf" element={<RequireAuth><CgfDashboard /></RequireAuth>} />
      <Route path="/projects/cgf/investment" element={<RequireAuth><CgfInvestment /></RequireAuth>} />
      <Route path="/projects/cgf/transactions" element={<RequireAuth><CgfTransactions /></RequireAuth>} />
      <Route path="/projects/rep" element={<RequireAuth><RealEstateDashboard /></RequireAuth>} />
      <Route path="/projects/rep/:projectId" element={<RequireAuth><RealEstateProjectDetail /></RequireAuth>} />
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/signup" element={<GuestOnly><SignUp /></GuestOnly>} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/forgot_password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/reset_password" element={<ResetPassword />} />
      <Route path="/reset/:uid/:token" element={<ResetPassword />} />
      <Route path="/reset/:uid/:token/" element={<ResetPassword />} />
      <Route path="/reset/complete" element={<PasswordResetComplete />} />
      <Route path="/verification-pending" element={<VerificationPending />} />
      <Route path="/verification_pending" element={<VerificationPending />} />
      <Route path="/account-verified-email" element={<AccountVerifiedEmail />} />
      <Route path="/help" element={<HelpCenter />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </>
  )
}
