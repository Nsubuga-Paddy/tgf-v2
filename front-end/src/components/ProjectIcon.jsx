import {
  ArrowDownLeft,
  ArrowUpRight,
  Building2,
  Clock3,
  Coffee,
  HandCoins,
  HeartHandshake,
  Landmark,
  Lock,
  PiggyBank,
  Shield,
  Sprout,
  Users,
} from 'lucide-react'

const MAP = {
  piggy: PiggyBank,
  heart: HeartHandshake,
  goat: HandCoins,
  building: Building2,
  lock: Lock,
  clock: Clock3,
  users: Users,
  coffee: Coffee,
  seedling: Sprout,
  hand: HandCoins,
  landmark: Landmark,
  shield: Shield,
}

export default function ProjectIcon({ name, size = 18 }) {
  const Icon = MAP[name] ?? PiggyBank
  return <Icon size={size} />
}
