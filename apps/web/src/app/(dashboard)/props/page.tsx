'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { microcopy } from '@/lib/microcopy'
import { oddsUrl, readOddsError } from '@/lib/odds-client'
import { propMarketsForSport } from '@/lib/odds-markets'

type GameRow = { id: string; home_team: string; away_team: string }

type PropRow = {
  sportsbook_display: string
  outcome_name: string
  point: number | null
  price: number
}

const SPORTS = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB'] as const

const OTHER_MARKET = '__other__'

export default function PropsPage() {
  const [sport, setSport] = useState<string>('NBA')
  const [marketChoice, setMarketChoice] = useState<string>('player_points')
  const [otherMarketKey, setOtherMarketKey] = useState('')
  const [games, setGames] = useState<GameRow[]>([])
  const [gameId, setGameId] = useState<string>('')
  const [rows, setRows] = useState<PropRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const marketOptions = useMemo(() => propMarketsForSport(sport), [sport])

  const effectiveMarketKey =
    marketChoice === OTHER_MARKET ? otherMarketKey.trim() : marketChoice

  useEffect(() => {
    const opts = propMarketsForSport(sport)
    const first = opts[0]?.value ?? 'player_points'
    setMarketChoice((prev) => {
      if (prev === OTHER_MARKET) return prev
      const ok = opts.some((o) => o.value === prev)
      return ok ? prev : first
    })
  }, [sport])

  const loadGames = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(oddsUrl(`/games?sport=${encodeURIComponent(sport)}`))
      if (!r.ok) throw new Error(await readOddsError(r))
      const data = (await r.json()) as GameRow[]
      setGames(data)
      if (data.length) setGameId(data[0].id)
      else setGameId('')
      setRows([])
    } catch (e) {
      setError(e instanceof Error ? e.message : microcopy.oddsApiUnavailable)
      setGames([])
    } finally {
      setLoading(false)
    }
  }, [sport])

  const loadProps = useCallback(async () => {
    if (!gameId || !effectiveMarketKey) return
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams({
        sport,
        game_id: gameId,
        market_key: effectiveMarketKey,
      })
      const r = await fetch(oddsUrl(`/props?${qs}`))
      if (!r.ok) throw new Error(await readOddsError(r))
      const data = (await r.json()) as { outcomes: PropRow[] }
      setRows(data.outcomes ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : microcopy.oddsApiUnavailable)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [sport, gameId, effectiveMarketKey])

  useEffect(() => {
    void loadGames()
  }, [sport, loadGames])

  return (
    <div className="space-y-6 p-4">
      <div>
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
          {microcopy.propsPageTitle}
        </h1>
        <p className="mt-1 text-[11px] text-zinc-500">{microcopy.propsPageSubtitle}</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={sport}
          onChange={(e) => setSport(e.target.value)}
          className="rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-200"
        >
          {SPORTS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => void loadGames()}
          className="rounded bg-zinc-800 px-3 py-2 text-[10px] font-semibold uppercase text-zinc-300"
        >
          Refresh games
        </button>
      </div>

      <div className="space-y-3">
        <label
          htmlFor="props-game"
          className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-500"
        >
          Game
        </label>
        <select
          id="props-game"
          value={gameId}
          onChange={(e) => setGameId(e.target.value)}
          disabled={!games.length}
          className="w-full max-w-md rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-200 disabled:opacity-50"
        >
          {games.length === 0 ? (
            <option value="">{loading ? 'Loading games…' : 'No games — try Refresh or another sport'}</option>
          ) : (
            games.map((g) => (
              <option key={g.id} value={g.id}>
                {g.away_team} @ {g.home_team}
              </option>
            ))
          )}
        </select>
      </div>

      <div className="space-y-3">
        <label
          htmlFor="props-market"
          className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-500"
        >
          Prop market
        </label>
        <select
          id="props-market"
          value={marketChoice}
          onChange={(e) => setMarketChoice(e.target.value)}
          className="w-full max-w-md rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-200"
        >
          {marketOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
          <option value={OTHER_MARKET}>Other (custom ID)…</option>
        </select>
        {marketChoice === OTHER_MARKET ? (
          <div className="space-y-2">
            <p className="text-[10px] text-zinc-600">
              Enter the exact market key from The Odds API docs for this sport (often{' '}
              <span className="font-mono text-zinc-500">snake_case</span>).
            </p>
            <input
              value={otherMarketKey}
              onChange={(e) => setOtherMarketKey(e.target.value)}
              className="w-full max-w-md rounded border border-zinc-800 bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-200"
              placeholder="e.g. batter_home_runs"
              aria-label="Custom Odds API market key"
            />
          </div>
        ) : null}
      </div>

      <button
        type="button"
        onClick={() => void loadProps()}
        disabled={loading || !gameId || !effectiveMarketKey}
        className="rounded bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
      >
        Load props
      </button>

      {error ? (
        <div className="rounded border border-red-900 bg-red-950/30 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      ) : null}

      {loading ? <p className="text-xs text-zinc-500">Loading…</p> : null}

      <ul className="space-y-2">
        {rows.map((row, i) => (
          <li
            key={`${row.outcome_name}-${row.sportsbook_display}-${i}`}
            className="rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs text-zinc-200"
          >
            <div className="font-semibold text-zinc-100">{row.outcome_name}</div>
            <div className="text-zinc-500">
              {row.sportsbook_display}
              {' · '}
              {row.price > 0 ? `+${row.price}` : row.price}
              {row.point != null ? ` · ${row.point}` : ''}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
