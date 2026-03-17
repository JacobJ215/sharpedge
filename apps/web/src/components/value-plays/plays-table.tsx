'use client'

import { useState } from 'react'
import type { ValuePlay } from '@/lib/api'
import { AlphaBadge } from '@/components/ui/alpha-badge'
import { RegimeChip } from '@/components/value-plays/regime-chip'

type SortCol = 'alpha_score' | 'expected_value' | 'event' | null
type SortDir = 'asc' | 'desc'

function EvCell({ value }: { value: number }) {
  const pct = value * 100
  const isStrong = pct >= 5
  const isModerate = pct >= 2
  const isNegative = pct < 0
  const colorClass = isStrong
    ? 'text-emerald-400'
    : isModerate
    ? 'text-blue-400'
    : isNegative
    ? 'text-red-400'
    : 'text-zinc-500'
  const bgClass = isStrong
    ? 'bg-emerald-500/8'
    : isModerate
    ? 'bg-blue-500/8'
    : isNegative
    ? 'bg-red-500/8'
    : ''

  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-xs font-semibold ${colorClass} ${bgClass}`}>
      {pct >= 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  )
}

function EdgeBadge({ badge }: { badge: string }) {
  if (badge === 'PREMIUM') {
    return (
      <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
        <svg width="7" height="7" viewBox="0 0 7 7" fill="currentColor">
          <path d="M3.5 0.5 4.5 2.8H7L5.2 4.2l.7 2.3L3.5 5.1 1.8 6.5l.7-2.3L1 2.8h2.5z"/>
        </svg>
        Strong
      </span>
    )
  }
  if (badge === 'HIGH') {
    return <span className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20">Moderate</span>
  }
  return null
}

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
    'py-2 px-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-600 select-none cursor-pointer hover:text-zinc-400 transition-colors'
  const tdClass = 'py-1.5 px-2.5 text-xs text-zinc-400'

  return (
    <div className="overflow-x-auto rounded border border-zinc-800/60">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-zinc-800/80 bg-zinc-900/40">
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
            <tr key={play.id} className="border-b border-zinc-900/60 hover:bg-zinc-900/30 transition-colors">
              <td className={`${tdClass} font-medium text-zinc-300`}>{play.event}</td>
              <td className={tdClass}>{play.market}</td>
              <td className={tdClass}>{play.team}</td>
              <td className="py-1.5 px-2.5">
                <EvCell value={play.expected_value} />
              </td>
              <td className={tdClass}>{play.book}</td>
              <td className={`${tdClass} font-mono text-zinc-300`}>{play.alpha_score.toFixed(2)}</td>
              <td className={tdClass}>
                <div className="flex items-center gap-1.5">
                  <AlphaBadge badge={play.alpha_badge} />
                  <EdgeBadge badge={play.alpha_badge} />
                </div>
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
