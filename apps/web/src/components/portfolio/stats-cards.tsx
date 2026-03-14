interface StatsCardsProps {
  roi: number
  win_rate: number
  clv_average: number
  drawdown: number
}

function StatCard({ label, value, suffix = '' }: { label: string; value: number; suffix?: string }) {
  const isNegative = value < 0
  return (
    <div className="rounded border border-zinc-800 bg-zinc-900 p-3">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className={`font-mono text-xl font-bold ${isNegative ? 'text-red-400' : 'text-zinc-100'}`}>
        {value > 0 ? '+' : ''}{value.toFixed(1)}{suffix}
      </div>
    </div>
  )
}

export function StatsCards({ roi, win_rate, clv_average, drawdown }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      <StatCard label="ROI" value={roi} suffix="%" />
      <StatCard label="Win Rate" value={win_rate} suffix="%" />
      <StatCard label="CLV Avg" value={clv_average} suffix="%" />
      <StatCard label="Max Drawdown" value={drawdown} suffix="%" />
    </div>
  )
}
