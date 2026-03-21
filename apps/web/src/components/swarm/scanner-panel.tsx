'use client'

import useSWR from 'swr'
import { getSwarmPipeline, SwarmFilterStep } from '@/lib/api'

function StepCard({ step }: { step: SwarmFilterStep }) {
  const isComplete = step.status === 'complete'
  const isActive = step.status === 'active'
  const isPending = step.status === 'pending'

  return (
    <div
      className={`flex items-center gap-3 rounded border px-3 py-2.5 ${
        isActive
          ? 'border-emerald-800 bg-zinc-950'
          : isPending
          ? 'border-zinc-900 bg-zinc-950 opacity-50'
          : 'border-zinc-800 bg-zinc-900/60'
      }`}
    >
      {/* Step number */}
      <div
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${
          isActive
            ? 'bg-emerald-500 text-black'
            : isComplete
            ? 'border border-emerald-700 bg-emerald-950 text-emerald-400'
            : 'border border-zinc-700 bg-zinc-800 text-zinc-500'
        }`}
      >
        {step.step}
      </div>

      {/* Name + description */}
      <div className="flex-1 min-w-0">
        <div className={`text-[11px] font-semibold ${isActive ? 'text-emerald-400' : isPending ? 'text-zinc-500' : 'text-zinc-200'}`}>
          {step.name}
        </div>
        <div className={`text-[9px] ${isActive ? 'text-emerald-600' : 'text-zinc-600'}`}>
          {step.description}
        </div>
      </div>

      {/* Count */}
      <div className="text-right shrink-0">
        {step.passed != null ? (
          <>
            <div className={`font-mono text-base font-bold ${isActive ? 'text-emerald-400' : 'text-zinc-200'}`}>
              {step.passed}
            </div>
            {step.removed != null && (
              <div className="text-[9px] text-red-500">−{step.removed} removed</div>
            )}
            {isActive && (
              <div className="text-[9px] text-emerald-600">Running...</div>
            )}
          </>
        ) : (
          <div className="font-mono text-base font-bold text-zinc-700">—</div>
        )}
      </div>
    </div>
  )
}

export function ScannerPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-pipeline',
    getSwarmPipeline,
    { refreshInterval: 30000 }
  )

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded bg-zinc-900/40" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded border border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Failed to load — retrying
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Agent header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-zinc-900 border border-zinc-800">
            <div className="h-3 w-3 rounded-sm bg-emerald-500 opacity-80" />
          </div>
          <div>
            <div className="text-[11px] font-bold text-zinc-200">Market Filter Agent</div>
            <div className="text-[9px] text-zinc-600">{data.agent_status}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[9px] uppercase tracking-wider text-zinc-600">Active Markets</div>
          <div className="font-mono text-2xl font-extrabold text-zinc-200 leading-tight">
            {data.active_markets}
          </div>
        </div>
      </div>

      {/* Filter Pipeline */}
      <div>
        <div className="mb-2 flex items-center gap-1.5">
          <div className="h-2.5 w-0.5 rounded-full bg-emerald-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            Filter Pipeline
          </span>
        </div>
        <div className="space-y-1">
          {data.steps.map((step) => (
            <StepCard key={step.step} step={step} />
          ))}
        </div>
      </div>

      {/* Qualified Markets */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-0.5 rounded-full bg-blue-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            Qualified Markets
          </span>
          <div className="h-px flex-1 bg-zinc-900" />
          <span className="text-[9px] font-bold text-zinc-600">
            {data.qualified_markets.length} FOUND
          </span>
        </div>
        {data.qualified_markets.length === 0 ? (
          <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-5 text-center text-[10px] text-zinc-700">
            Pipeline running — qualified markets appear here
          </div>
        ) : (
          <div className="space-y-1">
            {data.qualified_markets.map((m) => (
              <div
                key={m.market_id}
                className="flex items-center justify-between rounded border border-zinc-800 bg-zinc-900/40 px-3 py-2"
              >
                <div>
                  <div className="text-[10px] font-semibold text-zinc-300 truncate max-w-[220px]">
                    {m.title || m.market_id}
                  </div>
                  <div className="text-[9px] text-zinc-600">{m.platform}</div>
                </div>
                <div className="font-mono text-sm font-bold text-emerald-400">
                  +{(m.edge * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
