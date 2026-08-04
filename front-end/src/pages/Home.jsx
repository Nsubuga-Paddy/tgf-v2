import AppShell from '../components/layout/AppShell'
import BalanceHero from '../components/BalanceHero'
import MaturedProjects from '../components/MaturedProjects'
import MyProjects from '../components/MyProjects'
import OtherProjects from '../components/OtherProjects'
import PendingActionRequests from '../components/PendingActionRequests'
import PortfolioSummary from '../components/PortfolioSummary'

export default function Home() {
  return (
    <AppShell title="Home">
      <BalanceHero />
      <PortfolioSummary />
      <PendingActionRequests />
      <MaturedProjects />
      <MyProjects />
      <OtherProjects />
      <p className="foot">MCS Member Portal · personal portfolio</p>
    </AppShell>
  )
}
