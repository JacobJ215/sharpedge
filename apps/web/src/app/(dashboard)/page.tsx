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
  const userId = 'me'
  const [token, setToken] = useState<string>('')

  // Source real auth token from Supabase browser session
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setToken(session?.access_token ?? '')
    })
    // Also listen for auth state changes (sign-in / sign-out / token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setToken(session?.access_token ?? '')
    })
    return () => subscription.unsubscribe()
  }, [])

  const { data: portfolio, error, isLoading } = useSWR(
    token ? ['portfolio', userId, token] : null,
    () => getPortfolio(userId, token),
    { refreshInterval: 120_000 }
  )

  if (isLoading || !token) {
    return (
      <div className="space-y-3">
        <h1 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Portfolio</h1>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded border border-zinc-800 bg-zinc-900" />
          ))}
        </div>
        <div className="h-[200px] animate-pulse rounded border border-zinc-800 bg-zinc-900" />
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
    <div className="space-y-4">
      <h1 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Portfolio</h1>
      <StatsCards
        roi={portfolio.roi}
        win_rate={portfolio.win_rate}
        clv_average={portfolio.clv_average}
        drawdown={portfolio.drawdown}
      />
      <div>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
          ROI Curve
        </div>
        <RoiCurve data={ROI_HISTORY} />
      </div>
      <div>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
          Bankroll Curve
        </div>
        <BankrollCurve data={BANKROLL_HISTORY} />
      </div>
      {portfolio.active_bets.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Active Bets ({portfolio.active_bets.length})
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
