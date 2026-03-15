'use client'

import { useEffect, useState } from 'react'

interface DislocScore {
  venue_id: string
  mid_prob: number
  disloc_bps: number
  is_stale: boolean
}

interface DislocResponse {
  consensus_prob: number
  scores: DislocScore[]
}

interface Props {
  marketId: string
}

function bpsColor(bps: number): string {
  if (bps > 5) return 'text-green-400'
  if (bps < -5) return 'text-red-400'
  return 'text-zinc-400'
}

export function VenueDislocWidget({ marketId }: Props) {
  const [data, setData] = useState<DislocResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!marketId) {
      setLoading(false)
      return
    }

    let cancelled = false

    fetch(`/api/v1/markets/dislocation?market_id=${encodeURIComponent(marketId)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<DislocResponse>
      })
      .then((json) => {
        if (!cancelled) {
          setData(json)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [marketId])

  if (!marketId) return null

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-4 w-32 rounded bg-zinc-800" />
        <div className="h-24 rounded bg-zinc-800" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <p className="text-xs text-zinc-500">Dislocation data unavailable</p>
    )
  }

  if (!data.scores || data.scores.length === 0) {
    return (
      <p className="text-xs text-zinc-500">No dislocation data for this market</p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="text-xs text-zinc-400">
        Consensus:{' '}
        <span className="font-mono font-semibold text-zinc-200">
          {(data.consensus_prob * 100).toFixed(1)}%
        </span>
      </div>

      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-800 text-left">
            <th className="pb-1 font-medium text-zinc-500">Venue</th>
            <th className="pb-1 font-medium text-zinc-500">Mid Prob</th>
            <th className="pb-1 font-medium text-zinc-500">Disloc (bps)</th>
            <th className="pb-1 font-medium text-zinc-500">Stale</th>
          </tr>
        </thead>
        <tbody>
          {data.scores.map((row) => (
            <tr
              key={row.venue_id}
              className="border-b border-zinc-800/50 text-zinc-300 hover:bg-zinc-800/30"
            >
              <td className="py-1 pr-3 font-mono">
                {row.venue_id}
                {row.is_stale && (
                  <span className="ml-1 text-zinc-600">(stale)</span>
                )}
              </td>
              <td className="py-1 pr-3 font-mono">
                {(row.mid_prob * 100).toFixed(2)}%
              </td>
              <td className={`py-1 pr-3 font-mono ${bpsColor(row.disloc_bps)}`}>
                {row.disloc_bps > 0 ? '+' : ''}
                {row.disloc_bps}
              </td>
              <td className="py-1 text-zinc-500">
                {row.is_stale ? 'yes' : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default VenueDislocWidget
