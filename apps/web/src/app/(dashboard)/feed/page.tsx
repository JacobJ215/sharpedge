'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { getValuePlays } from '@/lib/api'
import type { ValuePlay } from '@/lib/api'

type FeedType = 'all' | 'sharp' | 'value' | 'steam' | 'pm'

interface FeedItem {
  id: string
  type: Exclude<FeedType, 'all'>
  event: string
  context: string
  title: string
  analysis: string
  badge: string
  confidence: 'HIGH' | 'MODERATE' | 'LOW'
  ev?: number
  book?: string
}

function buildFeedItems(plays: ValuePlay[]): FeedItem[] {
  const items: FeedItem[] = []

  // Strong / sharp signals (EV >= 5%)
  for (const p of plays.filter(p => p.expected_value * 100 >= 5)) {
    const ev = p.expected_value * 100
    items.push({
      id: `sharp-${p.id}`,
      type: 'sharp',
      event: p.event,
      context: `${p.market}  ·  ${p.book}`,
      title: 'Sharp Edge Detected',
      analysis: `Model finds +${ev.toFixed(1)}% EV — market is underpricing this outcome. `
        + `Alpha badge: ${p.alpha_badge}. Regime: ${p.regime_state}. `
        + `High CLV potential. Enter before line corrects toward fair value.`,
      badge: 'SHARP',
      confidence: 'HIGH',
      ev,
      book: p.book,
    })
  }

  // Value signals (1% <= EV < 5%)
  for (const p of plays.filter(p => p.expected_value * 100 >= 1 && p.expected_value * 100 < 5)) {
    const ev = p.expected_value * 100
    items.push({
      id: `value-${p.id}`,
      type: 'value',
      event: p.event,
      context: `${p.market}  ·  ${p.book}`,
      title: 'Value Alert',
      analysis: `+${ev.toFixed(1)}% EV detected. Moderate edge — size conservatively per fractional Kelly. `
        + `Regime: ${p.regime_state}. Monitor for confirming line movement before committing full position.`,
      badge: 'VALUE',
      confidence: 'MODERATE',
      ev,
      book: p.book,
    })
  }

  // Prediction market signals (regime contains discovery or news)
  for (const p of plays.filter(p =>
    p.regime_state?.toLowerCase().includes('discovery') ||
    p.regime_state?.toLowerCase().includes('news') ||
    p.event?.toLowerCase().includes('polymarket') ||
    p.event?.toLowerCase().includes('kalshi')
  )) {
    const ev = p.expected_value * 100
    items.push({
      id: `pm-${p.id}`,
      type: 'pm',
      event: p.event,
      context: `${p.market}  ·  ${p.regime_state}`,
      title: 'Prediction Market Signal',
      analysis: `${ev >= 0 ? '+' : ''}${ev.toFixed(1)}% edge in ${p.regime_state} regime. `
        + `Resolution probability diverges from model estimate. `
        + `Alpha: ${p.alpha_score.toFixed(2)}. Consider position size relative to market liquidity.`,
      badge: 'MARKET',
      confidence: ev >= 3 ? 'HIGH' : 'MODERATE',
      ev,
    })
  }

  // Sort: HIGH confidence first, then by EV descending
  return items.sort((a, b) => {
    const order = { HIGH: 0, MODERATE: 1, LOW: 2 }
    const confDiff = order[a.confidence] - order[b.confidence]
    if (confDiff !== 0) return confDiff
    return (b.ev ?? 0) - (a.ev ?? 0)
  })
}

// ── Badge styles ──────────────────────────────────────────────────────────────
const badgeStyle: Record<string, string> = {
  SHARP:  'text-blue-400',
  VALUE:  'text-emerald-400',
  STEAM:  'text-red-400',
  MARKET: 'text-violet-400',
}

const accentBar: Record<string, string> = {
  SHARP:  'bg-blue-500/40',
  VALUE:  'bg-emerald-500/40',
  STEAM:  'bg-red-500/40',
  MARKET: 'bg-violet-500/40',
}

const confStyle: Record<string, string> = {
  HIGH:     'text-emerald-600',
  MODERATE: 'text-zinc-600',
  LOW:      'text-zinc-700',
}

// ── Feed card ─────────────────────────────────────────────────────────────────
function FeedCard({ item }: { item: FeedItem }) {
  return (
    <div className="flex gap-3 border-b border-zinc-800/30 py-4 transition-colors">
      <div className={`mt-1 h-14 w-px shrink-0 ${accentBar[item.badge] ?? 'bg-zinc-700'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2.5">
          <span className={`text-[9px] font-bold uppercase tracking-widest ${badgeStyle[item.badge] ?? ''}`}>
            {item.badge}
          </span>
          <span className="text-zinc-800">·</span>
          <span className={`text-[9px] font-semibold uppercase tracking-wider ${confStyle[item.confidence]}`}>{item.confidence}</span>
          <span className="ml-auto text-[9px] text-zinc-700">{item.context.split('·')[1]?.trim()}</span>
        </div>
        <div className="mt-1.5 truncate text-sm font-semibold text-zinc-200">{item.event}</div>
        <div className="mt-0.5 text-[10px] text-zinc-600">{item.context}</div>
        <div className="mt-2 text-[11px] leading-relaxed text-zinc-500">{item.analysis}</div>
        {item.ev !== undefined && (
          <div className="mt-2 flex items-center gap-1.5">
            <span className={`font-mono text-xs font-bold ${item.ev >= 5 ? 'text-emerald-400' : item.ev >= 1 ? 'text-blue-400' : item.ev < 0 ? 'text-red-400' : 'text-zinc-500'}`}>
              {item.ev >= 0 ? '+' : ''}{item.ev.toFixed(1)}% EV
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Filter pill ───────────────────────────────────────────────────────────────
function FilterPill({ label, active, count, onClick }: { label: string; active: boolean; count: number; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-1 py-1 text-xs font-semibold transition-colors border-b ${
        active
          ? 'border-emerald-500 text-emerald-400'
          : 'border-transparent text-zinc-600 hover:text-zinc-400'
      }`}
    >
      {label}
      <span className={`text-[9px] font-bold ${active ? 'text-emerald-500' : 'text-zinc-700'}`}>
        {count}
      </span>
    </button>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function FeedPage() {
  const [activeFilter, setActiveFilter] = useState<FeedType>('all')

  const { data: plays = [], isLoading } = useSWR<ValuePlay[]>(
    'feed-plays',
    () => getValuePlays({ limit: 100 }),
    { refreshInterval: 30_000 }
  )

  const allItems = buildFeedItems(plays)
  const filtered = activeFilter === 'all' ? allItems : allItems.filter(i => i.type === activeFilter)

  const counts = {
    all: allItems.length,
    sharp: allItems.filter(i => i.type === 'sharp').length,
    value: allItems.filter(i => i.type === 'value').length,
    steam: allItems.filter(i => i.type === 'steam').length,
    pm: allItems.filter(i => i.type === 'pm').length,
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4">
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Intelligence Feed</h1>
        <div className="h-px flex-1 bg-zinc-800/60" />
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600">Live · {counts.all} signals</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-1.5 pb-4">
        <FilterPill label="All" active={activeFilter === 'all'} count={counts.all} onClick={() => setActiveFilter('all')} />
        <FilterPill label="Sharp" active={activeFilter === 'sharp'} count={counts.sharp} onClick={() => setActiveFilter('sharp')} />
        <FilterPill label="Value" active={activeFilter === 'value'} count={counts.value} onClick={() => setActiveFilter('value')} />
        <FilterPill label="Steam" active={activeFilter === 'steam'} count={counts.steam} onClick={() => setActiveFilter('steam')} />
        <FilterPill label="Markets" active={activeFilter === 'pm'} count={counts.pm} onClick={() => setActiveFilter('pm')} />
      </div>

      {/* Feed */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded border border-zinc-800 bg-zinc-900" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-16 text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/60">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#374151" strokeWidth="1.5" strokeLinecap="round">
              <path d="M3 5h14M3 10h14M3 15h8"/>
            </svg>
          </div>
          <div className="text-sm font-semibold text-zinc-500">Feed is quiet</div>
          <div className="mt-1 text-xs text-zinc-700">
            {activeFilter === 'all' ? 'Signals will appear as markets become active' : `No ${activeFilter} signals at this time`}
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded border border-zinc-800/60">
          {filtered.map(item => <FeedCard key={item.id} item={item} />)}
        </div>
      )}
    </div>
  )
}
