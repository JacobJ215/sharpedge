import { AlphaBadge } from '@/components/ui/alpha-badge'
import { RegimeChip } from '@/components/value-plays/regime-chip'

export interface GameAnalysis {
  game_id: string
  model_prediction: { win_probability: number; confidence: string }
  ev_breakdown: { ev_percentage: number; fair_odds: number; market_odds: number }
  regime_state: string
  key_number_proximity: unknown | null
  alpha_score: number
  alpha_badge: 'PREMIUM' | 'HIGH' | 'MEDIUM' | 'SPECULATIVE'
}

interface AnalysisPanelProps {
  analysis: GameAnalysis
}

export function AnalysisPanel({ analysis }: AnalysisPanelProps) {
  const { model_prediction, ev_breakdown, regime_state, key_number_proximity, alpha_badge } =
    analysis
  const winPct = (model_prediction.win_probability * 100).toFixed(1)
  const evPct = (ev_breakdown.ev_percentage * 100).toFixed(1)

  return (
    <div className="space-y-3 rounded border border-zinc-800 bg-zinc-900/60 p-4">
      {/* Row 1: Win Probability + Confidence */}
      <div className="flex items-center gap-4">
        <div>
          <p className="text-xs text-zinc-500">Win Probability</p>
          <p className="font-mono text-3xl font-bold text-white">{winPct}%</p>
        </div>
        <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
          {model_prediction.confidence}
        </span>
      </div>

      {/* Row 2: EV / Fair Odds / Market Odds */}
      <div className="grid grid-cols-3 gap-2 border-t border-zinc-800 pt-3">
        <div>
          <p className="text-xs text-zinc-500">EV%</p>
          <p className="font-mono text-sm text-emerald-400">{evPct}%</p>
        </div>
        <div>
          <p className="text-xs text-zinc-500">Fair Odds</p>
          <p className="font-mono text-sm text-zinc-200">{ev_breakdown.fair_odds}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-500">Market Odds</p>
          <p className="font-mono text-sm text-zinc-200">{ev_breakdown.market_odds}</p>
        </div>
      </div>

      {/* Row 3: Regime + Alpha + Key Number */}
      <div className="flex flex-wrap items-center gap-2 border-t border-zinc-800 pt-3">
        <RegimeChip regime={regime_state} />
        <AlphaBadge badge={alpha_badge} />
        <span className="text-xs text-zinc-500">
          Key #:{' '}
          {key_number_proximity != null ? String(key_number_proximity) : 'None'}
        </span>
      </div>
    </div>
  )
}
