'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface BankrollPoint {
  date: string
  bankroll: number
}

export function BankrollCurve({ data }: { data: BankrollPoint[] }) {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="bankrollGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#71717a' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#71717a' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}`}
          />
          <Tooltip
            contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', fontSize: 11 }}
            formatter={(value: number) => [`$${value.toFixed(0)}`, 'Bankroll']}
          />
          <Area
            type="monotone"
            dataKey="bankroll"
            stroke="#3b82f6"
            strokeWidth={1.5}
            fill="url(#bankrollGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
