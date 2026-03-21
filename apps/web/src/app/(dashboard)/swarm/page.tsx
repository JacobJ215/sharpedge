'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { ScannerPanel } from '@/components/swarm/scanner-panel'
import { PredictionPanel } from '@/components/swarm/prediction-panel'
import { RiskPanel } from '@/components/swarm/risk-panel'
import { PostMortemPanel } from '@/components/swarm/post-mortem-panel'

type Tab = 'scanner' | 'prediction' | 'risk' | 'post-mortem'

const TABS: { id: Tab; label: string }[] = [
  { id: 'scanner', label: 'Scanner' },
  { id: 'prediction', label: 'Prediction' },
  { id: 'risk', label: 'Risk' },
  { id: 'post-mortem', label: 'Post-Mortem' },
]

function SwarmContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const activeTab = (searchParams.get('tab') as Tab) ?? 'scanner'

  function setTab(tab: Tab) {
    router.push(`/swarm?tab=${tab}`)
  }

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">
          Swarm Monitor
        </span>
        <div className="h-px flex-1 bg-zinc-800/60" />
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600">Live</span>
        </div>
      </div>

      {/* Tab row */}
      <div className="flex gap-0 border-b border-zinc-800">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setTab(tab.id)}
              className={`px-4 py-1.5 text-[11px] font-medium transition-colors border-b-2 -mb-px ${
                isActive
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Panel */}
      {activeTab === 'scanner' && <ScannerPanel />}
      {activeTab === 'prediction' && <PredictionPanel />}
      {activeTab === 'risk' && <RiskPanel />}
      {activeTab === 'post-mortem' && <PostMortemPanel />}
    </div>
  )
}

export default function SwarmPage() {
  return (
    <Suspense fallback={
      <div className="space-y-3">
        <div className="h-4 w-32 animate-pulse rounded bg-zinc-900/40" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded bg-zinc-900/40" />
          ))}
        </div>
      </div>
    }>
      <SwarmContent />
    </Suspense>
  )
}
