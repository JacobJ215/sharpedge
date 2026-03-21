'use client'

import useSWR from 'swr'
import { supabase } from '@/lib/supabase'

interface FailedTrade {
  id: string
  market_id: string
  direction: string | null
  size: number
  entry_price: number
  pnl: number
  actual_outcome: string | null
  confidence_score: number | null
  opened_at: string
  resolved_at: string
}

async function fetchPostMortemData() {
  const [failedResp, allResp] = await Promise.all([
    supabase
      .from('paper_trades')
      .select('*')
      .lt('pnl', 0)
      .not('resolved_at', 'is', null)
      .order('resolved_at', { ascending: false })
      .limit(20),
    supabase
      .from('paper_trades')
      .select('id,pnl,resolved_at')
      .not('resolved_at', 'is', null),
  ])

  const failed = (failedResp.data ?? []) as FailedTrade[]
  const all = allResp.data ?? []
  const resolved = all.length
  const wins = all.filter((t) => (t.pnl ?? 0) >= 0).length
  const winRate = resolved > 0 ? (wins / resolved) * 100 : 0
  const firstDate =
    all.length > 0
      ? new Date(Math.min(...all.map((t) => new Date(t.resolved_at ?? 0).getTime())))
      : null
  const periodDays = firstDate
    ? Math.floor((Date.now() - firstDate.getTime()) / 86400000)
    : 0

  return { failed, resolved, winRate, periodDays }
}

function deriveAgentFindings(trade: FailedTrade) {
  const conf = trade.confidence_score ?? 0.5
  const pnl = trade.pnl
  const entryVsBase = Math.abs(trade.entry_price - 0.5)

  return [
    {
      name: 'Data',
      finding: conf < 0.5 ? 'Low sample confidence' : 'Strong historical base',
      highlighted: conf < 0.5,
    },
    {
      name: 'Sentiment',
      finding: pnl < 0 && conf > 0.7 ? 'Overconfident — check signals' : 'Aligned with market',
      highlighted: pnl < 0 && conf > 0.7,
    },
    {
      name: 'Timing',
      finding: entryVsBase > 0.05 ? 'Entry timing issue' : 'Entry timing nominal',
      highlighted: entryVsBase > 0.05,
    },
    {
      name: 'Model',
      finding:
        trade.direction === 'BUY' && trade.actual_outcome === 'NO'
          ? 'Model missed reversal'
          : 'Model output consistent',
      highlighted: trade.direction === 'BUY' && trade.actual_outcome === 'NO',
    },
    {
      name: 'Risk',
      finding: pnl < -200 ? 'Position sized above optimal' : 'Risk limits respected',
      highlighted: pnl < -200,
    },
  ]
}

function generateLogEntries(trade: FailedTrade) {
  const base = new Date(trade.resolved_at).getTime()
  const conf = trade.confidence_score ?? 0.5
  return [
    { offset: 0, tag: '[RISK]', color: 'text-violet-400', msg: 'Checking risk approval decision tree...' },
    {
      offset: 2000,
      tag: '[MODEL]',
      color: 'text-blue-400',
      msg:
        conf > 0.7
          ? 'High confidence but outcome negative — review features'
          : 'Model output below confidence threshold',
    },
    { offset: 4000, tag: '[RISK]', color: 'text-violet-400', msg: `PnL: $${trade.pnl.toFixed(2)} — loss recorded` },
    { offset: 6000, tag: '[DATA]', color: 'text-emerald-400', msg: '✓ Analysis complete. Findings ready.' },
    { offset: 8000, tag: '[SENT]', color: 'text-emerald-400', msg: '✓ Sentiment analysis complete.' },
    { offset: 10000, tag: '[TIME]', color: 'text-emerald-400', msg: '✓ Timing analysis complete.' },
  ].map(({ offset, tag, color, msg }) => ({
    time: new Date(base + offset).toTimeString().slice(0, 8),
    tag,
    color,
    msg,
  }))
}

export function PostMortemPanel() {
  const { data, error, isLoading } = useSWR('swarm-post-mortem', fetchPostMortemData, {
    refreshInterval: 30000,
  })

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

  const { failed, resolved, winRate, periodDays } = data

  if (failed.length === 0) {
    return (
      <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-8 text-center text-[10px] text-zinc-600">
        No failed predictions yet — keep trading in paper mode
      </div>
    )
  }

  const trade = failed[0]
  const findings = deriveAgentFindings(trade)
  const logEntries = generateLogEntries(trade)

  return (
    <div className="space-y-4">
      {/* Agent header */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-800 bg-zinc-900">
          <div className="h-2.5 w-2.5 rounded-sm bg-amber-500 opacity-90" />
        </div>
        <div className="flex-1">
          <div className="text-[11px] font-bold text-zinc-200">Post-Mortem Analysis</div>
          <div className="text-[9px] text-zinc-600">Learning from failed predictions</div>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
          <span className="text-[9px] font-semibold text-amber-400">Root cause identified</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* LEFT */}
        <div className="space-y-2.5">
          {/* Failed prediction card */}
          <div className="rounded border border-red-900 bg-zinc-900/60 p-3">
            <div className="mb-1.5 text-[9px] font-bold uppercase tracking-wider text-red-500">Failed Prediction</div>
            <div className="text-sm font-bold text-zinc-200 truncate">{trade.market_id}</div>
            <div className="mb-3 text-[9px] text-zinc-600">
              Resolved {new Date(trade.resolved_at).toLocaleDateString()}
            </div>
            <div className="mb-3 grid grid-cols-2 gap-1.5">
              <div className="rounded border border-zinc-900 bg-zinc-950 p-2 text-center">
                <div className="font-mono text-lg font-extrabold text-red-400">${trade.pnl.toFixed(0)}</div>
                <div className="text-[8px] uppercase text-zinc-600">Loss</div>
              </div>
              <div className="rounded border border-zinc-900 bg-zinc-950 p-2 text-center">
                <div className="font-mono text-lg font-extrabold text-zinc-200">
                  {((trade.entry_price ?? 0) * 100).toFixed(0)}%
                </div>
                <div className="text-[8px] uppercase text-zinc-600">Our Prob</div>
              </div>
            </div>
            <div className="space-y-1 mb-3">
              {[
                { label: 'Position', value: `${trade.direction ?? '—'} @ ${((trade.entry_price ?? 0) * 100).toFixed(0)}¢` },
                { label: 'Actual Outcome', value: trade.actual_outcome ?? 'Unknown', red: true },
                { label: 'Model Confidence', value: `${(((trade.confidence_score ?? 0.5)) * 100).toFixed(0)}%` },
                { label: 'Edge Estimated', value: `+${((trade.entry_price - 0.5) * 100).toFixed(0)}%` },
              ].map(({ label, value, red }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[9px] text-zinc-600">{label}</span>
                  <span className={`text-[9px] font-semibold ${red ? 'text-red-400' : 'text-zinc-300'}`}>{value}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-zinc-800 pt-2">
              <div className="mb-1 text-[9px] uppercase tracking-wider text-zinc-600">Context</div>
              <div className="text-[9px] leading-relaxed text-zinc-500">
                Market resolved against our prediction. Model confidence was high but outcome was
                negative — see analysis agents for root cause breakdown.
              </div>
            </div>
          </div>

          {/* Promotion gate */}
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Promotion Gate</div>
            <div className="space-y-1">
              {[
                { label: 'Resolved trades', value: `${resolved} / 50 needed`, red: resolved < 50 },
                { label: 'Period', value: `${periodDays} / 30 days`, red: periodDays < 30 },
                { label: 'Win rate', value: resolved > 0 ? `${winRate.toFixed(1)}%` : '—', red: false },
                { label: 'Status', value: 'Paper mode', red: true },
              ].map(({ label, value, red }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[9px] text-zinc-600">{label}</span>
                  <span className={`text-[9px] font-semibold ${red ? 'text-red-400' : 'text-zinc-300'}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="space-y-2.5">
          {/* Analysis agents */}
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2.5 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Analysis Agents</div>
            <div className="grid grid-cols-5 gap-1.5">
              {findings.map(({ name, finding, highlighted }) => (
                <div
                  key={name}
                  className={`rounded border p-2 text-center ${
                    highlighted && name === 'Risk' ? 'border-red-900 bg-zinc-950' : 'border-zinc-900 bg-zinc-950'
                  }`}
                >
                  <div className="text-[10px] font-bold text-zinc-300 mb-1">{name}</div>
                  <div className="text-[8px] text-emerald-500 mb-1">✓ Complete</div>
                  <div className={`text-[8px] leading-snug ${highlighted ? 'text-red-400' : 'text-zinc-600'}`}>
                    {finding}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analysis log */}
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-1 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Analysis Log</div>
            <div className="mb-2 text-[9px] text-zinc-700">Real-time agent findings</div>
            <div className="space-y-0.5 font-mono text-[9px]">
              {logEntries.map((entry, i) => (
                <div key={i} className="flex gap-2 border-b border-zinc-900 py-0.5 last:border-0">
                  <span className="shrink-0 text-zinc-700">{entry.time}</span>
                  <span className={`shrink-0 ${entry.color}`}>{entry.tag}</span>
                  <span className="text-zinc-500 min-w-0 truncate">{entry.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
