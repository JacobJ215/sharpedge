'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
} from 'recharts'
import type { MonteCarloResult } from '@/lib/api'

interface MonteCarloChartProps {
  result: MonteCarloResult
  numBets: number
}

function buildChartData(result: MonteCarloResult, numBets: number) {
  const { p5_outcome, p50_outcome, p95_outcome } = result
  const points = Math.min(numBets, 50)
  return Array.from({ length: points + 1 }, (_, i) => {
    const t = i / points
    return {
      bet: i,
      p5: Math.round(1000 + (p5_outcome - 1000) * t),
      p50: Math.round(1000 + (p50_outcome - 1000) * t),
      p95: Math.round(1000 + (p95_outcome - 1000) * t),
    }
  })
}

export function MonteCarloChart({ result, numBets }: MonteCarloChartProps) {
  const data = buildChartData(result, numBets)
  const ruinPct = (result.ruin_probability * 100).toFixed(1)

  return (
    <div data-testid="mc-chart">
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis dataKey="bet" tick={{ fontSize: 10, fill: '#71717a' }} />
          <YAxis tick={{ fontSize: 10, fill: '#71717a' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', fontSize: 11 }}
          />
          {/* Layer 1: shaded P5-P95 band */}
          <Area
            dataKey="p95"
            stackId="band"
            fill="#3b82f6"
            fillOpacity={0.1}
            stroke="none"
          />
          <Area
            dataKey="p5"
            stackId="band"
            fill="#0f172a"
            fillOpacity={1}
            stroke="none"
          />
          {/* Layer 2: solid P50 expected path */}
          <Line
            dataKey="p50"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
          />
          {/* Layer 3: P5 dashed floor line */}
          <Line
            dataKey="p5"
            stroke="#ef4444"
            strokeWidth={1}
            strokeDasharray="4 2"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="mt-2 text-center text-xs text-zinc-400">
        <span className="font-mono text-red-400">{ruinPct}%</span> ruin risk over {numBets} bets
        &nbsp;&middot;&nbsp;
        <span className="text-zinc-500">{result.paths_simulated.toLocaleString()} paths simulated</span>
      </p>
    </div>
  )
}
