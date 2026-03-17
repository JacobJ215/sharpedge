'use client'

import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { getPortfolio } from '@/lib/api'
import { supabase } from '@/lib/supabase'
import { StatsCards } from '@/components/portfolio/stats-cards'
import { RoiCurve } from '@/components/portfolio/roi-curve'
import { BankrollCurve } from '@/components/portfolio/bankroll-curve'

// Placeholder ROI history — replace with real endpoint when available
const ROI_HISTORY = [
  { date: 'Jan', roi: 0 },
  { date: 'Feb', roi: 4.2 },
  { date: 'Mar', roi: 7.1 },
]

// Placeholder bankroll history — replace with real endpoint when available
const BANKROLL_HISTORY = [
  { date: 'Jan', bankroll: 1000 },
  { date: 'Feb', bankroll: 1042 },
  { date: 'Mar', bankroll: 1113 },
]

export default function PortfolioPage() {
  const [token, setToken] = useState<string>('')
  const [userId, setUserId] = useState<string | null>(null)

  // Source real auth token and user ID from Supabase browser session
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setToken(session?.access_token ?? '')
      setUserId(session?.user?.id ?? null)
    })
    // Also listen for auth state changes (sign-in / sign-out / token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setToken(session?.access_token ?? '')
      setUserId(session?.user?.id ?? null)
    })
    return () => subscription.unsubscribe()
  }, [])

  const { data: portfolio, error, isLoading } = useSWR(
    token && userId ? ['portfolio', userId, token] : null,
    () => getPortfolio(userId!, token),
    { refreshInterval: 120_000 }
  )

  if (isLoading || !token || !userId) {
    return (
      <div className="space-y-3">
        <h1 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Portfolio</h1>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded bg-zinc-900/40" />
          ))}
        </div>
        <div className="h-[200px] animate-pulse rounded bg-zinc-900/40" />
      </div>
    )
  }

  if (error || !portfolio) {
    return (
      <div className="space-y-3">
        <h1 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Portfolio</h1>
        <div className="rounded border border-red-900 bg-red-950/30 px-3 py-2 text-xs text-red-400">
          Failed to load portfolio data
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Portfolio Overview</h1>
        <div className="h-px flex-1 bg-zinc-800/60" />
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600">Live</span>
        </div>
      </div>
      <StatsCards
        roi={portfolio.roi}
        win_rate={portfolio.win_rate}
        clv_average={portfolio.clv_average}
        drawdown={portfolio.drawdown}
      />
      <div>
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-0.5 rounded-full bg-emerald-500" />
          <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
            ROI Curve
          </div>
        </div>
        <RoiCurve data={ROI_HISTORY} />
      </div>
      <div>
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-0.5 rounded-full bg-blue-500" />
          <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
            Bankroll Curve
          </div>
        </div>
        <BankrollCurve data={BANKROLL_HISTORY} />
      </div>
      {portfolio.active_bets.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <div className="h-2.5 w-0.5 rounded-full bg-amber-500" />
            <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Active Bets
            </div>
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[9px] font-semibold text-zinc-400">
              {portfolio.active_bets.length}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="py-1.5 px-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                    Event
                  </th>
                  <th className="py-1.5 px-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                    Stake
                  </th>
                  <th className="py-1.5 px-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                    Book
                  </th>
                </tr>
              </thead>
              <tbody>
                {portfolio.active_bets.slice(0, 10).map((bet) => (
                  <tr key={bet.id} className="border-b border-zinc-900 hover:bg-zinc-900/40">
                    <td className="py-1 px-2 text-xs text-zinc-300">{bet.event}</td>
                    <td className="py-1 px-2 font-mono text-xs text-zinc-300">
                      ${bet.stake.toFixed(2)}
                    </td>
                    <td className="py-1 px-2 text-xs text-zinc-300">{bet.book}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
