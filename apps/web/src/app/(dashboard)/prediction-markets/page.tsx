'use client'

import useSWR from 'swr'
import { getValuePlays } from '@/lib/api'
import type { ValuePlay } from '@/lib/api'
import { PmTable } from '@/components/prediction-markets/pm-table'
import { VenueDislocWidget } from '@/components/venue/VenueDislocWidget'

const REGIME_LEGEND = [
  { label: 'Discovery', color: 'bg-emerald-500' },
  { label: 'Consensus', color: 'bg-blue-500' },
  { label: 'News Catalyst', color: 'bg-amber-500' },
]

export default function PredictionMarketsPage() {
  const { data: plays, error, isLoading } = useSWR<ValuePlay[]>(
    'pm-value-plays',
    () => getValuePlays({ sport: 'prediction_markets' }),
    { refreshInterval: 60000 }
  )

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Prediction Markets</h1>
        <div className="flex items-center gap-3">
          {REGIME_LEGEND.map(({ label, color }) => (
            <span key={label} className="flex items-center gap-1.5 text-xs text-zinc-400">
              <span className={`h-2 w-2 rounded-full ${color}`} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {isLoading && (
        <p className="text-sm text-zinc-500">Loading prediction market edges…</p>
      )}

      {error && (
        <p className="text-sm text-red-400">Failed to load prediction market data.</p>
      )}

      {plays && plays.length === 0 && (
        <p className="text-sm text-zinc-500">No prediction market edges found at this time.</p>
      )}

      {plays && plays.length > 0 && <PmTable plays={plays} />}

      <section className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Cross-Venue Dislocation
        </h2>
        <VenueDislocWidget
          marketId={
            plays && plays.length > 0
              ? (plays[0] as ValuePlay & { market_id?: string }).market_id ?? 'KXBTCD-01'
              : 'KXBTCD-01'
          }
        />
      </section>
    </div>
  )
}
