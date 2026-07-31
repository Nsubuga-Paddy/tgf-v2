import AppShell from '../components/layout/AppShell'
import BalanceHero from '../components/BalanceHero'
import MaturedProjects from '../components/MaturedProjects'
import MyProjects from '../components/MyProjects'
import OtherProjects from '../components/OtherProjects'
import PortfolioSummary from '../components/PortfolioSummary'

export default function Home() {
  return (
    <AppShell title="Home">
      <BalanceHero />
      <PortfolioSummary />
      <MaturedProjects />
      <MyProjects />
      <OtherProjects />
      <p className="foot">MCS Member Portal · personal portfolio</p>
    </AppShell>
  )
}
