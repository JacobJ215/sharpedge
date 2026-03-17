'use client'

import useSWR from 'swr'
import { getValuePlays } from '@/lib/api'
import type { ValuePlay } from '@/lib/api'
import { PmTable } from '@/components/prediction-markets/pm-table'
import { VenueDislocWidget } from '@/components/venue/VenueDislocWidget'

function extractPlatform(event: string): string {
  const lower = event.toLowerCase()
  if (lower.includes('kalshi')) return 'Kalshi'
  if (lower.includes('polymarket')) return 'Polymarket'
  return event.split('-')[0] ?? 'Unknown'
}

// ── Agentic Brief (deterministic from data) ───────────────────────────────────
function PmAgenticBrief({ plays }: { plays: ValuePlay[] }) {
  const premium = plays.filter(p => p.alpha_badge === 'PREMIUM').length
  const highEdge = plays.filter(p => p.expected_value * 100 >= 5).length
  const kalshi = plays.filter(p => extractPlatform(p.event) === 'Kalshi').length
  const poly = plays.filter(p => extractPlatform(p.event) === 'Polymarket').length
  const top = plays.length > 0
    ? plays.reduce((a, b) => a.expected_value > b.expected_value ? a : b)
    : null

  const brief = plays.length === 0
    ? 'No prediction market edges detected. Markets appear efficiently priced across Kalshi and Polymarket — regime scanning active. Watch for dislocations during high-volatility news events.'
    : `${plays.length} active edge${plays.length !== 1 ? 's' : ''} (${kalshi} Kalshi, ${poly} Polymarket). ${premium} premium signal${premium !== 1 ? 's' : ''}, ${highEdge} high-edge ≥5% EV.${top ? ` Top: ${top.market} at +${(top.expected_value * 100).toFixed(1)}% —` : ''} Regime-adjusted thresholds active across DISCOVERY, CONSENSUS, and PRE_RESOLUTION states.`

  return (
    <div>
      <p className="text-sm leading-relaxed text-zinc-400">{brief}</p>
      <div className="mt-3 flex flex-wrap gap-4">
        <span className="text-[9px] font-bold text-violet-500">
          {plays.length} SIGNALS
        </span>
        <span className="text-[9px] font-bold text-emerald-600">
          {highEdge} HIGH EDGE ≥5%
        </span>
        <span className="text-[9px] font-bold text-zinc-500">
          {premium} PREMIUM ALPHA
        </span>
      </div>
    </div>
  )
}

// ── Edge Distribution ─────────────────────────────────────────────────────────
function EdgeDistribution({ plays }: { plays: ValuePlay[] }) {
  const targets = plays.filter(p => p.expected_value * 100 >= 5)
  const moderate = plays.filter(p => p.expected_value * 100 >= 2 && p.expected_value * 100 < 5)
  const low = plays.filter(p => p.expected_value * 100 < 2)

  const cols = [
    { label: 'HIGH EDGE', sub: '≥5% EV', items: targets, color: 'text-emerald-400' },
    { label: 'MODERATE', sub: '2–5% EV', items: moderate, color: 'text-blue-400' },
    { label: 'LOW / FADE', sub: '<2% EV', items: low, color: 'text-zinc-500' },
  ]

  return (
    <div className="grid grid-cols-3 gap-2">
      {cols.map(col => (
        <div key={col.label}>
          <div className="border-b border-zinc-800/40 px-3 py-2.5">
            <div className={`text-[10px] font-black uppercase tracking-wider ${col.color}`}>{col.label}</div>
            <div className="text-[9px] text-zinc-600">{col.sub}</div>
            <div className={`mt-1 text-2xl font-bold leading-none ${col.color}`}>{col.items.length}</div>
          </div>
          <div className="divide-y divide-zinc-900/60">
            {col.items.slice(0, 3).map(p => (
              <div key={p.id} className="px-3 py-2">
                <div className="truncate text-[11px] font-semibold text-zinc-300">{p.market}</div>
                <div className="mt-0.5 flex items-center gap-2">
                  <span className={`text-[9px] font-bold ${col.color}`}>
                    {p.expected_value >= 0 ? '+' : ''}{(p.expected_value * 100).toFixed(1)}% EV
                  </span>
                  <span className="text-[9px] text-zinc-600">{extractPlatform(p.event)}</span>
                </div>
              </div>
            ))}
            {col.items.length === 0 && (
              <div className="px-3 py-4 text-center text-[10px] text-zinc-700">No signals</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function PredictionMarketsPage() {
  const { data: plays = [], error, isLoading } = useSWR<ValuePlay[]>(
    'pm-value-plays',
    () => getValuePlays({ sport: 'prediction_markets' }),
    { refreshInterval: 60_000 }
  )

  const firstMarketId = plays.length > 0
    ? ((plays[0] as ValuePlay & { market_id?: string }).market_id ?? 'KXBTCD-01')
    : 'KXBTCD-01'

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Prediction Markets</h1>
        <div className="h-px flex-1 bg-zinc-800/60" />
        {!isLoading && (
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-500" />
            <span className="text-[9px] font-bold uppercase tracking-wider text-violet-600">Live</span>
          </div>
        )}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded border border-zinc-800 bg-zinc-900" />
          ))}
        </div>
      )}

      {!isLoading && (
        <>
          {/* AI Brief */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-px bg-violet-500" />
              <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">AI Brief</h2>
            </div>
            {error ? (
              <p className="text-xs text-red-400">Failed to load prediction market data.</p>
            ) : (
              <PmAgenticBrief plays={plays} />
            )}
          </div>

          {/* Edge Distribution */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-px bg-emerald-500" />
              <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Edge Distribution</h2>
            </div>
            <p className="text-[10px] text-zinc-600">
              Signals classified by edge strength across Kalshi and Polymarket.
            </p>
            <EdgeDistribution plays={plays} />
          </div>

          {/* Active Edges table */}
          {plays.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-px bg-blue-500" />
                <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Active Edges</h2>
                <span className="text-[9px] font-semibold text-zinc-600">{plays.length}</span>
              </div>
              <PmTable plays={plays} />
            </div>
          )}

          {/* Cross-Venue Dislocation */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-px bg-amber-500" />
              <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Cross-Venue Dislocation</h2>
            </div>
            <VenueDislocWidget marketId={firstMarketId} />
          </div>

          {/* Regime reference */}
          <div className="space-y-1 border-t border-zinc-800/40 pt-4">
            <div className="text-[9px] font-semibold uppercase tracking-widest text-zinc-600">Regime States</div>
            <div className="flex flex-wrap gap-4 pt-1">
              {[
                { label: 'DISCOVERY', color: 'text-emerald-500', desc: 'Early market — lower threshold, wider edge window' },
                { label: 'CONSENSUS', color: 'text-blue-500', desc: 'Settled market — tighter threshold, sharper signals' },
                { label: 'NEWS CATALYST', color: 'text-amber-500', desc: 'Breaking news — elevated volatility, use caution' },
                { label: 'PRE-RESOLUTION', color: 'text-red-500', desc: 'Near close — highest threshold, only strong edges' },
              ].map(r => (
                <div key={r.label} className="flex items-start gap-1.5">
                  <div className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${r.color.replace('text-', 'bg-')}`} />
                  <div>
                    <div className={`text-[9px] font-bold ${r.color}`}>{r.label}</div>
                    <div className="text-[9px] text-zinc-600">{r.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
