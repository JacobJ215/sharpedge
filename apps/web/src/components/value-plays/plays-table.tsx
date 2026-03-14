'use client'

import { useState } from 'react'
import type { ValuePlay } from '@/lib/api'
import { AlphaBadge } from '@/components/ui/alpha-badge'
import { RegimeChip } from '@/components/value-plays/regime-chip'

type SortCol = 'alpha_score' | 'expected_value' | 'event' | null
type SortDir = 'asc' | 'desc'

export function PlaysTable({ plays }: { plays: ValuePlay[] }) {
  const [sortCol, setSortCol] = useState<SortCol>(null)
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(col: SortCol) {
    if (sortCol === col) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc')
    } else {
      setSortCol(col)
      setSortDir('asc')
    }
  }

  const sorted = [...plays].sort((a, b) => {
    if (!sortCol) return 0
    const av = a[sortCol] as number | string
    const bv = b[sortCol] as number | string
    if (typeof av === 'number' && typeof bv === 'number') {
      return sortDir === 'asc' ? av - bv : bv - av
    }
    return sortDir === 'asc'
      ? String(av).localeCompare(String(bv))
      : String(bv).localeCompare(String(av))
  })

  const thClass =
    'py-1.5 px-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500 select-none cursor-pointer hover:text-zinc-300'
  const tdClass = 'py-1 px-2 text-xs text-zinc-300'

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className={thClass} onClick={() => handleSort('event')}>
              Event
            </th>
            <th className={thClass}>Market</th>
            <th className={thClass}>Team</th>
            <th className={thClass} onClick={() => handleSort('expected_value')}>
              EV%
            </th>
            <th className={thClass}>Book</th>
            <th className={thClass} onClick={() => handleSort('alpha_score')}>
              Alpha
            </th>
            <th className={thClass}>Badge</th>
            <th className={thClass}>Regime</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((play) => (
            <tr key={play.id} className="border-b border-zinc-900 hover:bg-zinc-900/40">
              <td className={tdClass}>{play.event}</td>
              <td className={tdClass}>{play.market}</td>
              <td className={tdClass}>{play.team}</td>
              <td className={`${tdClass} font-mono`}>{(play.expected_value * 100).toFixed(1)}%</td>
              <td className={tdClass}>{play.book}</td>
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
