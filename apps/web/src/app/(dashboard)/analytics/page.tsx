'use client'

import useSWR from 'swr'
import { getValuePlays } from '@/lib/api'
import type { ValuePlay } from '@/lib/api'

// ── Section header ────────────────────────────────────────────────────────────
function SectionHeader({ label, accent }: { label: string; accent: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className={`h-3 w-0.5 rounded-full ${accent}`} />
      <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{label}</span>
    </div>
  )
}

// ── ATS Radar ─────────────────────────────────────────────────────────────────
function AtsRadar({ plays }: { plays: ValuePlay[] }) {
  // Classify plays into tiers based on EV and alpha
  const targets = plays.filter(p => p.expected_value * 100 >= 5)
  const neutral = plays.filter(p => p.expected_value * 100 >= 1 && p.expected_value * 100 < 5)
  const fades   = plays.filter(p => p.expected_value * 100 < 1)

  const columns = [
    { label: 'TARGET', sublabel: 'Strong Edge ≥ 5% EV', color: 'emerald', items: targets },
    { label: 'NEUTRAL', sublabel: '1–5% EV range', color: 'blue', items: neutral },
    { label: 'FADE', sublabel: 'Sub-1% or negative EV', color: 'red', items: fades },
  ]

  const colTextColor: Record<string, string> = {
    emerald: 'text-emerald-400',
    blue: 'text-blue-400',
    red: 'text-red-400',
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {columns.map(col => {
        const textColor = colTextColor[col.color]
        return (
          <div key={col.label}>
            <div className="border-b border-zinc-800/40 px-3 py-2.5">
              <div className={`text-[10px] font-black uppercase tracking-wider ${textColor}`}>{col.label}</div>
              <div className="text-[9px] text-zinc-600">{col.sublabel}</div>
              <div className={`mt-1 text-2xl font-bold leading-none ${textColor}`}>{col.items.length}</div>
            </div>
            <div className="divide-y divide-zinc-900/60">
              {col.items.slice(0, 5).map(p => (
                <div key={p.id} className="px-3 py-2">
                  <div className="truncate text-[11px] font-semibold text-zinc-300">{p.event}</div>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className={`text-[9px] font-bold ${textColor}`}>
                      {p.expected_value >= 0 ? '+' : ''}{(p.expected_value * 100).toFixed(1)}% EV
                    </span>
                    <span className="text-[9px] text-zinc-600">{p.book}</span>
                  </div>
                </div>
              ))}
              {col.items.length === 0 && (
                <div className="px-3 py-4 text-center text-[10px] text-zinc-700">No signals</div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Market Metrics ────────────────────────────────────────────────────────────
function MarketMetrics({ plays }: { plays: ValuePlay[] }) {
  const avgEv = plays.length === 0 ? 0 : plays.reduce((s, p) => s + p.expected_value * 100, 0) / plays.length
  const strongEdge = plays.filter(p => p.expected_value * 100 >= 5).length
  const positiveEv = plays.filter(p => p.expected_value > 0).length
  const premiumPct = plays.length === 0 ? 0 : Math.round((plays.filter(p => p.alpha_badge === 'PREMIUM').length / plays.length) * 100)

  const metrics = [
    { label: 'Average EV', value: `${avgEv >= 0 ? '+' : ''}${avgEv.toFixed(2)}%`, positive: avgEv >= 0 },
    { label: 'Strong Edge', value: `${strongEdge} signals`, positive: strongEdge > 0 },
    { label: '+EV Coverage', value: `${positiveEv} / ${plays.length}`, positive: positiveEv > 0 },
    { label: 'Premium Rate', value: `${premiumPct}%`, positive: premiumPct >= 20 },
  ]

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      {metrics.map(m => (
        <div key={m.label} className="p-3">
          <div className="text-[9px] font-semibold uppercase tracking-widest text-zinc-600">{m.label}</div>
          <div className={`mt-1.5 font-mono text-lg font-bold ${m.positive ? 'text-zinc-100' : 'text-red-400'}`}>{m.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Situational Edges ─────────────────────────────────────────────────────────
const SITUATIONAL_EDGES = [
  { title: 'Home Underdog', sport: 'NFL/NBA', edge: '+4.2%', description: 'Home underdogs receiving < 40% of public tickets historically outperform ATS. Books shade heavily toward favorites in primetime.', positive: true },
  { title: 'Reverse Line Move', sport: 'ALL', edge: '+3.8%', description: 'When the line moves opposite the direction of public betting %: a clear sharp money indicator. High CLV plays follow.', positive: true },
  { title: 'Back-to-Back Dog', sport: 'NBA', edge: '-2.1%', description: 'Teams on second game in 2 days underperform ATS by 2.1%, especially road teams. Fade these spots or reduce size.', positive: false },
  { title: 'Post-Bye Advantage', sport: 'NFL', edge: '+2.9%', description: 'Teams coming off bye week have extra prep time, more film study, and better rest. Consistent ATS edge over a 15-year sample.', positive: true },
  { title: 'Divisional Dog', sport: 'NFL', edge: '+2.4%', description: 'Divisional underdogs know their opponents intimately. Extra motivation and familiarity creates consistent value for dogs.', positive: true },
  { title: 'Primetime Fade', sport: 'NFL', edge: '+1.9%', description: 'Prime time slots attract heavy casual betting on favorites. Sharps systematically fade these spots, creating value on underdogs.', positive: true },
  { title: 'Short Rest Totals', sport: 'NBA', edge: '+2.2%', description: 'Teams on short rest play at a slower pace — totals trend under more often. Pace reduction averages 1.8 possessions per game.', positive: true },
  { title: 'Revenge Spot', sport: 'ALL', edge: '+1.7%', description: 'Teams facing opponents who beat them badly in a recent matchup tend to perform better ATS. Motivation edge is quantifiable.', positive: true },
] as const

function SituationalEdges() {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {SITUATIONAL_EDGES.map(edge => (
        <div key={edge.title} className="p-3">
          <div className="flex items-start justify-between">
            <span className="text-[9px] font-bold text-zinc-600">{edge.sport}</span>
            <span className={`text-sm font-black ${edge.positive ? 'text-emerald-400' : 'text-red-400'}`}>{edge.edge}</span>
          </div>
          <div className="mt-2 text-[12px] font-bold text-zinc-200">{edge.title}</div>
          <div className="mt-1.5 text-[10px] leading-relaxed text-zinc-600">{edge.description}</div>
        </div>
      ))}
    </div>
  )
}

// ── Key Numbers ───────────────────────────────────────────────────────────────
const KEY_NUMBERS = [
  { number: '3', sport: 'NFL', tier: 'critical', description: 'Most common winning margin in NFL history (~15%). Avoid buying through, always sell off.' },
  { number: '7', sport: 'NFL', tier: 'critical', description: 'TD + PAT — second most common margin. Particularly important on totals near 42-44.' },
  { number: '10', sport: 'NFL', tier: 'high', description: 'Combined FG + TD combination. Important for second-half totals and game spreads.' },
  { number: '6', sport: 'NFL', tier: 'high', description: 'Two field goals. Relevant for team totals and first-half lines.' },
  { number: '2.5', sport: 'NBA', tier: 'medium', description: 'Sharp adjustment threshold. Lines at -2.5 or +2.5 attract disproportionate sharp action.' },
  { number: '1', sport: 'MLB', tier: 'medium', description: 'Runline and first-five key number. Single-run game dynamics heavily influence totals.' },
] as const

function KeyNumbers() {
  const tierStyles = {
    critical: 'text-red-400',
    high: 'text-amber-400',
    medium: 'text-zinc-500',
  }

  return (
    <div className="divide-y divide-zinc-900/60">
      {KEY_NUMBERS.map(kn => (
        <div key={`${kn.number}-${kn.sport}`} className="flex items-center gap-4 px-4 py-3">
          <div className={`w-9 shrink-0 font-mono text-base font-black ${tierStyles[kn.tier]}`}>
            {kn.number}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-bold text-zinc-600">{kn.sport}</span>
              <span className="text-[9px] font-semibold uppercase tracking-wider text-zinc-700">{kn.tier}</span>
            </div>
            <div className="mt-0.5 text-[11px] leading-relaxed text-zinc-500">{kn.description}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Agentic Brief ─────────────────────────────────────────────────────────────
function AgenticBrief({ plays }: { plays: ValuePlay[] }) {
  const premiumCount = plays.filter(p => p.alpha_badge === 'PREMIUM').length
  const highEvCount = plays.filter(p => p.expected_value * 100 >= 5).length
  const hasEdge = highEvCount > 0

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-2.5">
        <div className="flex items-center gap-2">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5.5 1 6.8 4H10l-2.7 2 1 3.2-2.8-2-2.8 2 1-3.2L1 4h3.2z"/>
          </svg>
          <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-500">Agentic Brief</span>
        </div>
        <span className="text-[9px] text-zinc-600">Today's slate</span>
      </div>
      <div className="p-4">
        <p className="text-sm leading-relaxed text-zinc-400">
          {hasEdge
            ? `Today's slate shows ${highEvCount} strong-edge signal${highEvCount !== 1 ? 's' : ''} with EV above 5% and ${premiumCount} premium alpha badge${premiumCount !== 1 ? 's' : ''}. Market conditions suggest sharp positioning is available. Prioritize CLV retention — enter early where line movement confirms your model edge. Monitor for reverse line movements as a secondary confirmation signal.`
            : `Markets are currently efficient with no high-conviction edges detected across ${plays.length} signals scanned. This is normal — quality edges are rare. Maintain discipline: no edge means no bet. Monitor steam moves and reverse line movement for emerging opportunities. A quiet market often precedes a sharp action window.`
          }
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-[9px] font-bold text-emerald-600">CLV TARGET: &gt;+1.5%</span>
          <span className="text-[9px] font-bold text-blue-600">PHASE: {hasEdge ? 'Active' : 'Quiet'}</span>
          <span className="text-[9px] font-bold text-zinc-500">{plays.length} SIGNALS SCANNED</span>
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function AnalyticsPage() {
  const { data: plays = [], isLoading } = useSWR<ValuePlay[]>(
    'analytics-plays',
    () => getValuePlays({ limit: 50 }),
    { refreshInterval: 60_000 }
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Sports Analytics</h1>
        <div className="h-px flex-1 bg-zinc-800/60" />
        {!isLoading && (
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600">Live</span>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded border border-zinc-800 bg-zinc-900" />
          ))}
        </div>
      ) : (
        <>
          <AgenticBrief plays={plays} />

          <div className="space-y-2">
            <SectionHeader label="Market Metrics" accent="bg-emerald-500" />
            <MarketMetrics plays={plays} />
          </div>

          <div className="space-y-2">
            <SectionHeader label="ATS Radar" accent="bg-blue-500" />
            <p className="text-[10px] text-zinc-600">
              Signals classified by edge strength. TARGET = strong action, NEUTRAL = moderate, FADE = weak or negative EV.
            </p>
            <AtsRadar plays={plays} />
          </div>

          <div className="space-y-2">
            <SectionHeader label="Situational Edges" accent="bg-violet-500" />
            <SituationalEdges />
          </div>

          <div className="space-y-2">
            <SectionHeader label="Key Numbers Reference" accent="bg-amber-500" />
            <KeyNumbers />
          </div>
        </>
      )}
    </div>
  )
}
