import type { ReactNode } from 'react'

interface StatsCardsProps {
  roi: number
  win_rate: number
  clv_average: number
  drawdown: number
}

interface StatCardProps {
  label: string
  value: number
  suffix?: string
  accentColor: string
  icon: ReactNode
}

function StatCard({ label, value, suffix = '', accentColor, icon }: StatCardProps) {
  const isNegative = value < 0
  const isPositive = value > 0
  return (
    <div className="p-3.5">
      <div className="flex items-start justify-between">
        <div className="text-[9px] font-semibold uppercase tracking-widest text-zinc-600">
          {label}
        </div>
        <span className="text-zinc-700">{icon}</span>
      </div>
      <div className={`mt-2 font-mono text-2xl font-bold leading-none ${isNegative ? 'text-red-400' : isPositive ? 'text-zinc-100' : 'text-zinc-400'}`}>
        {value > 0 ? '+' : ''}{value.toFixed(1)}{suffix}
      </div>
      <div className="mt-1.5 flex items-center gap-1">
        {isPositive && (
          <svg width="8" height="8" viewBox="0 0 8 8" fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1,6 4,2 7,6" />
          </svg>
        )}
        {isNegative && (
          <svg width="8" height="8" viewBox="0 0 8 8" fill="none" stroke="#f87171" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1,2 4,6 7,2" />
          </svg>
        )}
        <span className={`text-[9px] font-medium ${isNegative ? 'text-red-500' : isPositive ? 'text-emerald-600' : 'text-zinc-600'}`}>
          {isNegative ? 'Below baseline' : isPositive ? 'Above baseline' : 'At baseline'}
        </span>
      </div>
    </div>
  )
}

export function StatsCards({ roi, win_rate, clv_average, drawdown }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      <StatCard
        label="ROI"
        value={roi}
        suffix="%"
        accentColor="bg-emerald-500"
        icon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1,9 4,5 7,6.5 11,2" />
          </svg>
        }
      />
      <StatCard
        label="Win Rate"
        value={win_rate}
        suffix="%"
        accentColor="bg-blue-500"
        icon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="6" cy="6" r="4.5" />
            <path d="M6 3v3.5l2 1.2" />
          </svg>
        }
      />
      <StatCard
        label="CLV Avg"
        value={clv_average}
        suffix="%"
        accentColor="bg-violet-500"
        icon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M6 1.5 7.5 5H11l-3 2.2 1.1 3.3L6 8.5l-3.1 2 1.1-3.3L1 5h3.5z" />
          </svg>
        }
      />
      <StatCard
        label="Max Drawdown"
        value={drawdown}
        suffix="%"
        accentColor="bg-amber-500"
        icon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1,3 4,7 7,5.5 11,9" />
          </svg>
        }
      />
    </div>
  )
}
