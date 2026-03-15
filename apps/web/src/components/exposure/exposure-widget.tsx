'use client'

import { useEffect, useState } from 'react'

interface VenueExposure {
  venue_id: string
  exposure: number
  utilization_pct: number
}

interface ExposureResponse {
  total_exposure: number
  bankroll: number
  venues: VenueExposure[]
}

function barColor(pct: number): string {
  return pct > 50 ? 'bg-amber-500' : 'bg-green-600'
}

export function ExposureWidget() {
  const [data, setData] = useState<ExposureResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false

    fetch('/api/v1/bankroll/exposure')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<ExposureResponse>
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
  }, [])

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-4 w-48 rounded bg-zinc-800" />
        <div className="h-20 rounded bg-zinc-800" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <p className="text-xs text-zinc-500">Exposure data unavailable</p>
    )
  }

  if (!data.venues || data.venues.length === 0) {
    return (
      <p className="text-xs text-zinc-500">No active positions</p>
    )
  }

  const overallPct =
    data.bankroll > 0
      ? Math.min((data.total_exposure / data.bankroll) * 100, 100)
      : 0

  return (
    <div className="space-y-3">
      <div className="text-xs text-zinc-400">
        Total Exposure:{' '}
        <span className="font-mono font-semibold text-zinc-200">
          ${data.total_exposure.toFixed(0)}
        </span>{' '}
        / Bankroll:{' '}
        <span className="font-mono font-semibold text-zinc-200">
          ${data.bankroll.toFixed(0)}
        </span>
      </div>

      <div className="space-y-2">
        {data.venues.map((v) => (
          <div key={v.venue_id} className="space-y-0.5">
            <div className="flex justify-between text-xs text-zinc-400">
              <span className="font-mono">{v.venue_id}</span>
              <span className="font-mono">
                ${v.exposure.toFixed(0)} — {v.utilization_pct.toFixed(1)}%
              </span>
            </div>
            <div className="h-1.5 w-full rounded bg-zinc-800">
              <div
                style={{ width: `${Math.min(v.utilization_pct, 100)}%` }}
                className={`h-1.5 rounded ${barColor(v.utilization_pct)}`}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-0.5 pt-1">
        <div className="flex justify-between text-xs text-zinc-500">
          <span>Overall utilization</span>
          <span className="font-mono">{overallPct.toFixed(1)}%</span>
        </div>
        <div className="h-1.5 w-full rounded bg-zinc-800">
          <div
            style={{ width: `${overallPct}%` }}
            className={`h-1.5 rounded ${barColor(overallPct)}`}
          />
        </div>
      </div>
    </div>
  )
}

export default ExposureWidget
