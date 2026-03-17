'use client'

import { useState } from 'react'
import { KellyCalculator } from '@/components/bankroll/kelly-calculator'
import { MonteCarloChart } from '@/components/bankroll/monte-carlo-chart'
import { simulateBankroll } from '@/lib/api'
import type { MonteCarloResult } from '@/lib/api'
import { ExposureWidget } from '@/components/venue/ExposureWidget'

export default function BankrollPage() {
  const [mcResult, setMcResult] = useState<MonteCarloResult | null>(null)
  const [numBets, setNumBets] = useState(100)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSimulate(params: {
    bankroll: number
    bet_size: number
    num_bets: number
    win_rate: number
  }) {
    setIsLoading(true)
    setError(null)
    try {
      const result = await simulateBankroll(params)
      setMcResult(result)
      setNumBets(params.num_bets)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Bankroll</h1>
        <div className="h-px flex-1 bg-zinc-800/60" />
      </div>

      {/* Kelly Calculator section */}
      <section className="py-2">
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-px bg-emerald-500" />
          <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Kelly Calculator</h2>
        </div>
        <KellyCalculator />
      </section>

      {/* Monte Carlo simulation trigger */}
      <section className="py-2">
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-px bg-blue-500" />
          <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Monte Carlo Simulation</h2>
        </div>
        <SimulateForm onSimulate={handleSimulate} isLoading={isLoading} />
        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        {mcResult && (
          <div className="mt-4">
            <MonteCarloChart result={mcResult} numBets={numBets} />
          </div>
        )}
      </section>

      {/* Live Exposure widget */}
      <section className="py-2">
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-px bg-amber-500" />
          <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Live Exposure (Current Session)</h2>
        </div>
        <ExposureWidget />
        <p className="mt-3 text-xs text-zinc-600">
          (Resets on server restart — reflects current process positions)
        </p>
      </section>

      {/* Exposure limits reminder */}
      <section className="py-2 border-t border-zinc-800/40 pt-4">
        <h2 className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-amber-500">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5.5 1 L10 9.5 H1 Z" /><line x1="5.5" y1="4.5" x2="5.5" y2="6.5" /><circle cx="5.5" cy="8" r="0.4" fill="currentColor" stroke="none" /></svg>
          Exposure Limits
        </h2>
        <p className="text-xs text-zinc-400">
          Never bet more than <span className="font-semibold text-amber-300">2% Kelly</span> per
          wager. Full Kelly is theoretically optimal but produces variance that exceeds most
          bettors&apos; risk tolerance. Half or quarter Kelly is recommended for sustained
          compounding.
        </p>
      </section>
    </div>
  )
}

interface SimulateFormProps {
  onSimulate: (params: {
    bankroll: number
    bet_size: number
    num_bets: number
    win_rate: number
  }) => void
  isLoading: boolean
}

function SimulateForm({ onSimulate, isLoading }: SimulateFormProps) {
  const [bankroll, setBankroll] = useState('1000')
  const [betSize, setBetSize] = useState('20')
  const [numBets, setNumBets] = useState('100')
  const [winRate, setWinRate] = useState('0.55')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSimulate({
      bankroll: parseFloat(bankroll),
      bet_size: parseFloat(betSize),
      num_bets: parseInt(numBets, 10),
      win_rate: parseFloat(winRate),
    })
  }

  const inputClass =
    'w-full rounded bg-zinc-900 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-zinc-600 font-mono'
  const labelClass = 'block text-xs text-zinc-500 mb-1'

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
      <div>
        <label className={labelClass}>Bankroll ($)</label>
        <input type="number" value={bankroll} onChange={(e) => setBankroll(e.target.value)} className={inputClass} />
      </div>
      <div>
        <label className={labelClass}>Bet Size ($)</label>
        <input type="number" value={betSize} onChange={(e) => setBetSize(e.target.value)} className={inputClass} />
      </div>
      <div>
        <label className={labelClass}>Number of Bets</label>
        <input type="number" value={numBets} onChange={(e) => setNumBets(e.target.value)} className={inputClass} />
      </div>
      <div>
        <label className={labelClass}>Win Rate (0–1)</label>
        <input type="number" step="0.01" value={winRate} onChange={(e) => setWinRate(e.target.value)} className={inputClass} />
      </div>
      <div className="col-span-2">
        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {isLoading ? 'Simulating…' : 'Run Simulation'}
        </button>
      </div>
    </form>
  )
}
