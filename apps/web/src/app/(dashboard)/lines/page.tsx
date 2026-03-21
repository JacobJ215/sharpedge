'use client'

import { useCallback, useEffect, useState } from 'react'
import { microcopy } from '@/lib/microcopy'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type GameRow = { id: string; home_team: string; away_team: string; commence_time: string }

type FormattedLine = {
  sportsbook_display: string
  side: string
  line: number | null
  odds: number
  is_best: boolean
}

type Comparison = {
  game_id: string
  home_team: string
  away_team: string
  spread_home: FormattedLine[]
  spread_away: FormattedLine[]
  total_over: FormattedLine[]
  total_under: FormattedLine[]
  moneyline_home: FormattedLine[]
  moneyline_away: FormattedLine[]
}

const SPORTS = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB'] as const

function LineTable({ title, rows }: { title: string; rows: FormattedLine[] }) {
  if (!rows.length) return null
  return (
    <div className="mb-4">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
        {title}
      </div>
      <div className="overflow-hidden rounded border border-zinc-800">
        <table className="w-full text-left text-xs text-zinc-300">
          <thead className="bg-zinc-900/80 text-[10px] uppercase text-zinc-500">
            <tr>
              <th className="px-2 py-1.5">Book</th>
              <th className="px-2 py-1.5">Side</th>
              <th className="px-2 py-1.5">Line</th>
              <th className="px-2 py-1.5">Odds</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={`${r.sportsbook_display}-${i}`}
                className={r.is_best ? 'bg-emerald-950/40' : 'border-t border-zinc-800/80'}
              >
                <td className="px-2 py-1.5">{r.sportsbook_display}</td>
                <td className="px-2 py-1.5">{r.side}</td>
                <td className="px-2 py-1.5 font-mono">{r.line ?? '—'}</td>
                <td className="px-2 py-1.5 font-mono">{r.odds > 0 ? `+${r.odds}` : r.odds}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function LinesPage() {
  const [sport, setSport] = useState<string>('NFL')
  const [games, setGames] = useState<GameRow[]>([])
  const [gameId, setGameId] = useState<string>('')
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingGames, setLoadingGames] = useState(false)
  const [loadingLines, setLoadingLines] = useState(false)

  const loadGames = useCallback(async () => {
    setLoadingGames(true)
    setError(null)
    try {
      const r = await fetch(`${API_BASE}/api/v1/odds/games?sport=${encodeURIComponent(sport)}`)
      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || r.statusText)
      }
      const data = (await r.json()) as GameRow[]
      setGames(data)
      if (data.length) setGameId(data[0].id)
      else setGameId('')
    } catch (e) {
      setError(e instanceof Error ? e.message : microcopy.oddsApiUnavailable)
      setGames([])
      setGameId('')
    } finally {
      setLoadingGames(false)
    }
  }, [sport])

  const loadComparison = useCallback(async () => {
    if (!gameId) return
    setLoadingLines(true)
    setError(null)
    try {
      const qs = new URLSearchParams({ sport, game_id: gameId })
      const r = await fetch(`${API_BASE}/api/v1/odds/line-comparison?${qs}`)
      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || r.statusText)
      }
      setComparison((await r.json()) as Comparison)
    } catch (e) {
      setError(e instanceof Error ? e.message : microcopy.oddsApiUnavailable)
      setComparison(null)
    } finally {
      setLoadingLines(false)
    }
  }, [sport, gameId])

  useEffect(() => {
    void loadGames()
  }, [sport, loadGames])

  useEffect(() => {
    if (gameId) void loadComparison()
  }, [gameId, sport, loadComparison])

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">
          {microcopy.linesPageTitle}
        </h1>
        <p className="mt-1 text-[11px] text-zinc-500">{microcopy.linesPageSubtitle}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-[10px] uppercase text-zinc-500">Sport</label>
        <select
          value={sport}
          onChange={(e) => {
            setSport(e.target.value)
            setGameId('')
            setComparison(null)
          }}
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
          className="rounded bg-zinc-800 px-2 py-1 text-[10px] font-semibold uppercase text-zinc-300 hover:bg-zinc-700"
        >
          Refresh games
        </button>
      </div>

      {loadingGames ? (
        <p className="text-xs text-zinc-500">Loading games…</p>
      ) : (
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

      {error ? (
        <div className="rounded border border-red-900 bg-red-950/30 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      ) : null}

      {loadingLines ? (
        <p className="text-xs text-zinc-500">Loading lines…</p>
      ) : comparison ? (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-zinc-200">
            {comparison.away_team} @ {comparison.home_team}
          </p>
          <LineTable title="Spread (home)" rows={comparison.spread_home} />
          <LineTable title="Spread (away)" rows={comparison.spread_away} />
          <LineTable title="Total over" rows={comparison.total_over} />
          <LineTable title="Total under" rows={comparison.total_under} />
          <LineTable title="Moneyline home" rows={comparison.moneyline_home} />
          <LineTable title="Moneyline away" rows={comparison.moneyline_away} />
        </div>
      ) : null}
    </div>
  )
}
