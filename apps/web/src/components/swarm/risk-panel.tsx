'use client'

import useSWR from 'swr'
import { supabase } from '@/lib/supabase'

interface PaperTrade {
  id: string
  market_id: string
  direction: string
  size: number
  entry_price: number
  trading_mode: string
  pnl: number | null
  confidence_score: number | null
  opened_at: string
  resolved_at: string | null
  status?: string
}

interface OpenPosition {
  market_id: string
  size: number
  trading_mode: string
  status: string
}

interface TradingConfig {
  key: string
  value: string
}

const BANKROLL = 10_000

async function fetchRiskData() {
  const [tradesResp, posResp, configResp] = await Promise.all([
    supabase.from('paper_trades').select('*').order('opened_at', { ascending: false }).limit(20),
    supabase.from('open_positions').select('*').eq('status', 'open'),
    supabase.from('trading_config').select('*'),
  ])

  return {
    trades: (tradesResp.data ?? []) as PaperTrade[],
    positions: (posResp.data ?? []) as OpenPosition[],
    config: (configResp.data ?? []) as TradingConfig[],
  }
}

function configVal(config: TradingConfig[], key: string, fallback: string): string {
  return config.find((c) => c.key === key)?.value ?? fallback
}

export function RiskPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-risk',
    fetchRiskData,
    { refreshInterval: 5000 }
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 animate-pulse rounded bg-zinc-900/40" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded border border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Failed to load — retrying
      </div>
    )
  }

  const { trades, positions, config } = data
  const activeSize = positions.reduce((s, p) => s + (p.size ?? 0), 0)
  const activePct = (activeSize / BANKROLL) * 100
  const availablePct = Math.max(0, 100 - activePct)
  const tradingMode = positions[0]?.trading_mode ?? 'paper'

  const incoming = trades[0] ?? null
  const maxPosition = BANKROLL * 0.05
  const incomingSize = incoming?.size ?? 0
  const incomingPct = (incomingSize / BANKROLL) * 100

  let consecutive = 0
  for (const t of trades) {
    if (t.pnl != null && t.pnl < 0) consecutive++
    else if (t.pnl != null) break
  }
  const cbStatus = consecutive >= 5 ? 'Paused' : consecutive >= 3 ? 'Triggered' : 'Normal'

  const limits = [
    { label: 'Max Category Exposure', value: configVal(config, 'max_category_exposure', '20%') },
    { label: 'Max Total Exposure', value: configVal(config, 'max_total_exposure', '40%') },
    { label: 'Daily Loss Limit', value: configVal(config, 'daily_loss_limit', '10%') },
    { label: 'Min Liquidity', value: configVal(config, 'min_liquidity', '$50K') },
    { label: 'Min Edge Required', value: configVal(config, 'min_edge', '3%') },
    { label: 'Kelly Fraction', value: configVal(config, 'kelly_fraction', '0.25') },
  ]

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* LEFT */}
      <div className="space-y-2.5">
        {/* Agent header */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-800 bg-zinc-900">
            <div className="h-2.5 w-2.5 rounded-sm bg-red-500 opacity-90" />
          </div>
          <div className="flex-1">
            <div className="text-[11px] font-bold text-zinc-200">Risk Agent</div>
            <div className="text-[9px] text-zinc-600">Automated Position Management</div>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-violet-500" />
            <span className="text-[9px] font-semibold text-violet-400 capitalize">{tradingMode} Mode</span>
          </div>
        </div>

        {/* Bankroll */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-1 text-[9px] uppercase tracking-wider text-zinc-600">Total Bankroll</div>
          <div className="font-mono text-2xl font-extrabold text-zinc-200 leading-tight">
            ${BANKROLL.toLocaleString()}
          </div>
          <div className="text-[9px] text-zinc-600 mb-3">Paper trading balance</div>
          <div>
            <div className="mb-1 flex justify-between">
              <span className="text-[9px] uppercase tracking-wider text-zinc-600">Capital Allocation</span>
              <span className="text-[9px] font-bold text-amber-400">{activePct.toFixed(0)}% deployed</span>
            </div>
            <div className="flex h-1.5 overflow-hidden rounded bg-zinc-800">
              <div className="bg-emerald-500" style={{ width: `${Math.min(activePct, 100)}%` }} />
              <div className="bg-zinc-700" style={{ width: `${Math.min(availablePct, 100)}%` }} />
            </div>
            <div className="mt-1 flex gap-3">
              {[['bg-emerald-500', 'Active'], ['bg-zinc-700', 'Available']].map(([c, l]) => (
                <div key={l} className="flex items-center gap-1">
                  <div className={`h-1.5 w-1.5 rounded-full ${c}`} />
                  <span className="text-[8px] text-zinc-600">{l}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Risk limits */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Risk Limits</div>
          <div className="space-y-1.5">
            {limits.map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span className="text-[10px] text-zinc-500">{label}</span>
                <span className="font-mono text-[10px] font-semibold text-zinc-300">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Circuit breaker */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2.5">
          <div className="flex items-center gap-2">
            <div className={`h-1.5 w-1.5 rounded-full ${cbStatus === 'Normal' ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-600">Circuit Breaker</span>
            <span className={`ml-auto text-[9px] font-semibold ${cbStatus === 'Normal' ? 'text-emerald-400' : 'text-red-400'}`}>
              {cbStatus}
            </span>
          </div>
          <div className="mt-1 text-[9px] text-zinc-600">
            {consecutive} consecutive loss{consecutive !== 1 ? 'es' : ''} — trading {cbStatus === 'Normal' ? 'active' : 'paused'}
          </div>
        </div>
      </div>

      {/* RIGHT */}
      <div className="space-y-2.5">
        {/* Incoming trade */}
        {incoming ? (
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-1 text-[9px] text-zinc-600">Incoming Trade</div>
            <div className="mb-0.5 text-sm font-bold text-zinc-200 truncate">{incoming.market_id}</div>
            <div className="mb-3 text-[9px] text-zinc-600">
              {incoming.trading_mode} · opened {new Date(incoming.opened_at).toLocaleDateString()}
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {[
                { label: 'Edge', value: `+${((incoming.entry_price - 0.5) * 100).toFixed(0)}%`, color: 'text-emerald-400' },
                { label: 'Market', value: `${(incoming.entry_price * 100).toFixed(0)}¢`, color: 'text-zinc-300' },
                { label: 'True Prob', value: `${(incoming.entry_price * 100).toFixed(0)}%`, color: 'text-blue-400' },
                { label: 'Confidence', value: `${((incoming.confidence_score ?? 0.5) * 100).toFixed(0)}%`, color: 'text-amber-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded border border-zinc-900 bg-zinc-950 p-1.5 text-center">
                  <div className={`font-mono text-xs font-bold ${color}`}>{value}</div>
                  <div className="text-[8px] uppercase tracking-wide text-zinc-600">{label}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-5 text-center text-[10px] text-zinc-600">
            No recent trades
          </div>
        )}

        {/* Position size check */}
        {incoming && (
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2 flex items-center gap-2">
              <div className={`h-1.5 w-1.5 rounded-full ${incomingSize <= maxPosition ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span className="text-[10px] font-semibold text-zinc-200">Position Size Check</span>
              <span className={`ml-auto text-[9px] ${incomingSize <= maxPosition ? 'text-emerald-400' : 'text-red-400'}`}>
                {incomingSize <= maxPosition ? '✓ Within limits' : '✗ Exceeds limit'}
              </span>
            </div>
            <div className="space-y-1.5">
              {[
                { label: 'Calculated Size', value: `$${incomingSize.toFixed(0)} (${incomingPct.toFixed(1)}%)` },
                { label: 'Max Allowed (5%)', value: `$${maxPosition.toFixed(0)}` },
                { label: 'Final Position', value: `$${Math.min(incomingSize, maxPosition).toFixed(0)}` },
                { label: '% of Bankroll', value: `${Math.min(incomingPct, 5).toFixed(1)}% ${incomingPct <= 5 ? '✓' : '✗'}` },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[10px] text-zinc-500">{label}</span>
                  <span className="font-mono text-[10px] font-semibold text-zinc-300">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Trade status */}
        {incoming && (
          <div className={`flex items-center gap-2.5 rounded border p-2.5 ${
            incoming.pnl == null || incoming.pnl >= 0
              ? 'border-emerald-800 bg-emerald-950/30'
              : 'border-red-800 bg-red-950/30'
          }`}>
            <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              incoming.pnl == null || incoming.pnl >= 0 ? 'bg-emerald-500 text-black' : 'bg-red-500 text-white'
            }`}>
              {incoming.pnl == null || incoming.pnl >= 0 ? '✓' : '✗'}
            </div>
            <div>
              <div className={`text-[11px] font-bold ${incoming.pnl == null || incoming.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {incoming.pnl == null ? 'Trade Active' : incoming.pnl >= 0 ? 'Trade Won' : 'Trade Lost'}
              </div>
              <div className={`text-[9px] ${incoming.pnl == null || incoming.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                ${incomingSize.toFixed(0)} position · {incomingPct.toFixed(1)}% of bankroll
              </div>
            </div>
          </div>
        )}

        {/* Recent decisions */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Recent Decisions</div>
          <div className="space-y-1">
            {trades.slice(0, 10).map((t) => {
              const approved = t.pnl == null || t.pnl >= 0
              return (
                <div key={t.id} className="flex items-center justify-between border-b border-zinc-900 py-1 last:border-0">
                  <span className="truncate max-w-[180px] text-[9px] text-zinc-400">
                    {t.market_id} · {t.direction ?? '—'}
                  </span>
                  <span className={`text-[9px] font-semibold ${approved ? 'text-emerald-400' : 'text-zinc-500'}`}>
                    {approved ? 'APPROVED' : 'DROPPED'}
                  </span>
                </div>
              )
            })}
            {trades.length === 0 && (
              <div className="text-[9px] text-zinc-700 italic">No decisions yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
