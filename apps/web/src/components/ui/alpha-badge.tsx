import { clsx } from 'clsx'

type Badge = 'PREMIUM' | 'HIGH' | 'MEDIUM' | 'SPECULATIVE'

const colors: Record<Badge, string> = {
  PREMIUM: 'bg-emerald-500/20 text-emerald-400 ring-emerald-500/30',
  HIGH: 'bg-blue-500/20 text-blue-400 ring-blue-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 ring-amber-500/30',
  SPECULATIVE: 'bg-zinc-500/20 text-zinc-400 ring-zinc-500/30',
}

export function AlphaBadge({ badge }: { badge: Badge }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        colors[badge]
      )}
    >
      {badge}
    </span>
  )
}
