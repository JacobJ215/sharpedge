import type { ValuePlay } from '@/lib/api'
import { AlphaBadge } from '@/components/ui/alpha-badge'
import { RegimeChip } from '@/components/value-plays/regime-chip'

interface PmTableProps {
  plays: ValuePlay[]
}

function extractPlatform(event: string): string {
  const lower = event.toLowerCase()
  if (lower.includes('kalshi')) return 'Kalshi'
  if (lower.includes('polymarket')) return 'Polymarket'
  return event.split('-')[0] ?? 'Unknown'
}

export function PmTable({ plays }: PmTableProps) {
  const thClass =
    'py-1.5 px-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500'
  const tdClass = 'py-1 px-2 text-xs text-zinc-300'

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className={thClass}>Platform</th>
            <th className={thClass}>Market</th>
            <th className={thClass}>Edge%</th>
            <th className={thClass}>Alpha</th>
            <th className={thClass}>Badge</th>
            <th className={thClass}>Regime</th>
          </tr>
        </thead>
        <tbody>
          {plays.map((play) => (
            <tr key={play.id} className="border-b border-zinc-900 hover:bg-zinc-900/40">
              <td className={tdClass}>{extractPlatform(play.event)}</td>
              <td className={tdClass}>{play.market}</td>
              <td className={`${tdClass} font-mono`}>
                {(play.expected_value * 100).toFixed(1)}%
              </td>
              <td className={`${tdClass} font-mono`}>{play.alpha_score.toFixed(2)}</td>
              <td className={tdClass}>
                <AlphaBadge badge={play.alpha_badge} />
              </td>
              <td className={tdClass}>
                <RegimeChip regime={play.regime_state} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
