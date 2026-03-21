'use client'

import { useCallback, useEffect, useState } from 'react'
import { microcopy } from '@/lib/microcopy'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type GameRow = { id: string; home_team: string; away_team: string }

type PropRow = {
  sportsbook_display: string
  outcome_name: string
  point: number | null
  price: number
}

const SPORTS = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB'] as const

export default function PropsPage() {
  const [sport, setSport] = useState<string>('NBA')
  const [marketKey, setMarketKey] = useState('player_points')
  const [games, setGames] = useState<GameRow[]>([])
  const [gameId, setGameId] = useState<string>('')
  const [rows, setRows] = useState<PropRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const loadGames = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API_BASE}/api/v1/odds/games?sport=${encodeURIComponent(sport)}`)
      if (!r.ok) throw new Error(await r.text())
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
    if (!gameId || !marketKey.trim()) return
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams({
        sport,
        game_id: gameId,
        market_key: marketKey.trim(),
      })
      const r = await fetch(`${API_BASE}/api/v1/odds/props?${qs}`)
      if (!r.ok) throw new Error(await r.text())
      const data = (await r.json()) as { outcomes: PropRow[] }
      setRows(data.outcomes ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : microcopy.oddsApiUnavailable)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [sport, gameId, marketKey])

  useEffect(() => {
    void loadGames()
  }, [sport, loadGames])

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
          {microcopy.propsPageTitle}
        </h1>
        <p className="mt-1 text-[11px] text-zinc-500">{microcopy.propsPageSubtitle}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          value={sport}
          onChange={(e) => setSport(e.target.value)}
          className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
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
          className="rounded bg-zinc-800 px-2 py-1 text-[10px] font-semibold uppercase text-zinc-300"
        >
          Refresh games
        </button>
      </div>

      {games.length > 0 && (
        <div>
          <label className="text-[10px] uppercase text-zinc-500">Game</label>
          <select
            value={gameId}
            onChange={(e) => setGameId(e.target.value)}
            className="mt-1 w-full max-w-md rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
          >
            {games.map((g) => (
              <option key={g.id} value={g.id}>
                {g.away_team} @ {g.home_team}
              </option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label className="text-[10px] uppercase text-zinc-500">Market key</label>
        <input
          value={marketKey}
          onChange={(e) => setMarketKey(e.target.value)}
          className="mt-1 w-full max-w-md rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
          placeholder="player_points"
        />
      </div>

      <button
        type="button"
        onClick={() => void loadProps()}
        disabled={loading || !gameId}
        className="rounded bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
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
