'use client'

import useSWR from 'swr'
import { getSwarmCalibration, SwarmCalibrationLatest } from '@/lib/api'

function FeatureBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.abs(value) * 100
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 shrink-0 text-[10px] text-zinc-500">{label}</span>
      <div className="flex-1 h-[3px] rounded bg-zinc-800">
        <div className={`h-full rounded ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <span className={`w-10 text-right font-mono text-[10px] font-semibold ${value < 0 ? 'text-red-400' : color.includes('emerald') ? 'text-emerald-400' : 'text-blue-400'}`}>
        {value.toFixed(2)}
      </span>
    </div>
  )
}

function ConfidenceDot({ label, value }: { label: string; value: string }) {
  const isGood = ['High', 'Strong', 'Low'].includes(value)
  const isMid = ['Medium', 'Moderate'].includes(value)
  return (
    <div className="flex items-center gap-1.5">
      <div className={`h-1.5 w-1.5 shrink-0 rounded-full ${isGood ? 'bg-emerald-500' : isMid ? 'bg-amber-500' : 'bg-red-500'}`} />
      <span className="text-[9px] text-zinc-500">{label}: <span className="text-zinc-400">{value}</span></span>
    </div>
  )
}

function LatestPanel({ d, recent }: { d: SwarmCalibrationLatest; recent: Array<{ market_id: string; base_prob: number; calibrated_prob: number; created_at: string }> }) {
  const edgePct = (d.edge * 100).toFixed(1)
  const basePct = (d.base_prob * 100).toFixed(0)
  const calibPct = (d.calibrated_prob * 100).toFixed(0)
  const marketPct = (d.market_price * 100).toFixed(0)
  const adjPct = (d.llm_adjustment * 100).toFixed(1)

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* LEFT: Calibration pipeline */}
      <div className="space-y-2.5">
        {/* Agent header */}
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-800 bg-zinc-900">
            <div className="h-2.5 w-2.5 rounded-sm bg-violet-500 opacity-90" />
          </div>
          <div className="flex-1">
            <div className="text-[11px] font-bold text-zinc-200">Prediction Agent</div>
            <div className="text-[9px] text-zinc-600">Probability Calibration Engine</div>
          </div>
          <div className="flex gap-1">
            <span className="rounded border border-violet-900 bg-violet-950/60 px-1.5 py-0.5 text-[9px] font-bold text-violet-400">XGBoost</span>
            <span className="rounded border border-blue-900 bg-blue-950/60 px-1.5 py-0.5 text-[9px] font-bold text-blue-400">Claude</span>
          </div>
        </div>

        {/* Signal features */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-2.5">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Signal Features</div>
          <div className="space-y-1.5">
            <FeatureBar label="sentiment_score" value={d.features.sentiment_score} color="bg-emerald-500" />
            <FeatureBar label="time_decay" value={d.features.time_decay} color="bg-red-500" />
            <FeatureBar label="market_correlation" value={d.features.market_correlation} color="bg-blue-500" />
          </div>
        </div>

        {/* Raw probability */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-2.5">
          <div className="text-[9px] uppercase tracking-wider text-zinc-600">Raw Probability</div>
          <div className="font-mono text-3xl font-extrabold text-zinc-200 leading-tight">{basePct}%</div>
        </div>

        {/* LLM Calibrator */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-2.5">
          <div className="mb-2 flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-violet-500" />
            <span className="text-[10px] font-semibold text-violet-400">LLM Calibrator</span>
            <span className="ml-auto text-[9px] text-emerald-500">Complete</span>
          </div>
          <div className="space-y-1 mb-2">
            {[
              ['news_analysis', 'Sentiment adjusted'],
              ['expert_consensus', 'LLM review complete'],
              ['uncertainty_factor', `Medium (±${Math.abs(parseFloat(adjPct))}%)`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-[9px] text-zinc-600">{k}</span>
                <span className="text-[9px] font-semibold text-zinc-300">{v}</span>
              </div>
            ))}
          </div>
          <div className="border-t border-zinc-800 pt-2">
            <div className="text-[9px] uppercase tracking-wider text-zinc-600">Calibration Adjustment</div>
            <div className={`font-mono text-lg font-bold ${parseFloat(adjPct) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {parseFloat(adjPct) >= 0 ? '+' : ''}{adjPct}%
            </div>
          </div>
        </div>

        {/* Ensemble output */}
        <div className="rounded border border-emerald-800 bg-emerald-950/30 p-2.5">
          <div className="mb-1 flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-[10px] font-semibold text-emerald-400">Ensemble Output</span>
            <span className="ml-auto text-[9px] text-emerald-500">Complete</span>
          </div>
          <div className="text-[9px] uppercase tracking-wider text-emerald-700">True Probability</div>
          <div className="font-mono text-3xl font-extrabold text-emerald-400 leading-tight">{calibPct}%</div>
        </div>
      </div>

      {/* RIGHT: Market detail */}
      <div className="space-y-2.5">
        {/* Market title */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="text-sm font-bold text-zinc-200 mb-1 truncate">{d.market_title || d.market_id}</div>
          <div className="text-[9px] text-zinc-600">
            {d.resolve_date ? `Resolves ${new Date(d.resolve_date).toLocaleDateString()}` : 'Resolution date TBD'}
            {d.volume != null ? ` · $${(d.volume / 1000).toFixed(0)}K volume` : ''}
          </div>
        </div>

        {/* Probability comparison */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2.5 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Probability Comparison</div>
          <div className="space-y-2">
            <div className="flex items-center gap-2.5">
              <div className="w-20 shrink-0">
                <div className="text-[10px] font-semibold text-zinc-300">Market Price</div>
                <div className="text-[9px] text-zinc-600">Current</div>
              </div>
              <div className="flex-1 h-2 rounded bg-zinc-800">
                <div className="h-full rounded bg-violet-600" style={{ width: `${d.market_price * 100}%` }} />
              </div>
              <div className="w-8 text-right font-mono text-sm font-bold text-violet-400">{marketPct}%</div>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="w-20 shrink-0">
                <div className="text-[10px] font-semibold text-zinc-300">True Probability</div>
                <div className="text-[9px] text-zinc-600">XGBoost + LLM</div>
              </div>
              <div className="flex-1 h-2 rounded bg-zinc-800">
                <div className="h-full rounded bg-emerald-500" style={{ width: `${d.calibrated_prob * 100}%` }} />
              </div>
              <div className="w-8 text-right font-mono text-sm font-bold text-emerald-400">{calibPct}%</div>
            </div>
          </div>
        </div>

        {/* Detected edge */}
        <div className="flex items-center justify-between rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2.5">
          <div>
            <div className="text-[9px] uppercase tracking-wider text-zinc-600">Detected Edge</div>
            <div className="text-[9px] text-zinc-600">
              {calibPct}% − {marketPct}% = {parseFloat(edgePct) >= 0 ? '+' : ''}{edgePct}%
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`font-mono text-xl font-extrabold ${parseFloat(edgePct) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {parseFloat(edgePct) >= 0 ? '+' : ''}{edgePct}%
            </div>
            {d.direction && (
              <span className={`rounded border px-2 py-1 text-[10px] font-bold ${
                d.direction === 'BUY'
                  ? 'border-emerald-800 bg-emerald-950/50 text-emerald-400'
                  : 'border-red-800 bg-red-950/50 text-red-400'
              }`}>
                {d.direction} SIGNAL
              </span>
            )}
          </div>
        </div>

        {/* Model confidence */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Model Confidence</div>
          <div className="space-y-1">
            <ConfidenceDot label="Data quality" value={d.model_confidence.data_quality} />
            <ConfidenceDot label="Feature signal" value={d.model_confidence.feature_signal} />
            <ConfidenceDot label="Uncertainty" value={d.model_confidence.uncertainty} />
          </div>
        </div>

        {/* Recent predictions */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Recent Predictions</div>
          {recent.length === 0 ? (
            <div className="text-[9px] text-zinc-700 italic">No recent predictions</div>
          ) : (
            <div className="space-y-1">
              {recent.slice(0, 5).map((r, i) => (
                <div key={i} className="flex items-center justify-between border-b border-zinc-900 py-1 last:border-0">
                  <span className="font-mono text-[10px] text-zinc-400 truncate max-w-[140px]">{r.market_id}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[9px] text-zinc-600">base {r.base_prob.toFixed(4)}</span>
                    <span className={`text-[9px] font-semibold font-mono ${r.calibrated_prob > r.base_prob ? 'text-emerald-400' : 'text-amber-400'}`}>
                      → {r.calibrated_prob.toFixed(4)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function PredictionPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-calibration',
    getSwarmCalibration,
    { refreshInterval: 30000 }
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded bg-zinc-900/40" />
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

  if (!data.latest) {
    return (
      <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-8 text-center text-[10px] text-zinc-600">
        No predictions recorded yet — daemon processing markets
      </div>
    )
  }

  return <LatestPanel d={data.latest} recent={data.recent} />
}
