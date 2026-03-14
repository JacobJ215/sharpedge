'use client'

import { useParams } from 'next/navigation'
import useSWR from 'swr'
import { AnalysisPanel } from '@/components/game/analysis-panel'
import type { GameAnalysis } from '@/components/game/analysis-panel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function fetchGameAnalysis(url: string): Promise<GameAnalysis> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export default function GameDetailPage() {
  const params = useParams()
  const id = params?.id as string

  const { data: analysis, error, isLoading } = useSWR<GameAnalysis>(
    id ? `${API_BASE}/api/v1/games/${id}/analysis` : null,
    fetchGameAnalysis
  )

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-zinc-500">
        Loading analysis…
      </div>
    )
  }

  if (error || !analysis) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-red-400">
        Failed to load game analysis.
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <h1 className="text-xl font-semibold text-white">Game Analysis</h1>
      <p className="font-mono text-xs text-zinc-500">Game ID: {id}</p>
      <AnalysisPanel analysis={analysis} />
    </div>
  )
}
