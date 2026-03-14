'use client'

import useSWR from 'swr'
import { getValuePlays } from '@/lib/api'
import { PlaysTable } from '@/components/value-plays/plays-table'

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export default function ValuePlaysPage() {
  const { data: plays, error, isLoading, isValidating } = useSWR(
    'value-plays',
    () => getValuePlays(),
    { refreshInterval: 60_000 }
  )

  const lastRefresh = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
            Value Plays
          </h1>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
        </div>
        <span className="text-[10px] text-zinc-600">
          {isValidating ? 'Refreshing...' : `Last refresh: ${lastRefresh}`}
        </span>
      </div>

      {isLoading && (
        <div className="space-y-1">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-7 animate-pulse rounded bg-zinc-900" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded border border-red-900 bg-red-950/30 px-3 py-2 text-xs text-red-400">
          Failed to load value plays
        </div>
      )}

      {plays && <PlaysTable plays={plays} />}
    </div>
  )
}
