'use client'

import { useState } from 'react'
import { KellyCalculator } from '@/components/bankroll/kelly-calculator'
import { MonteCarloChart } from '@/components/bankroll/monte-carlo-chart'
import { simulateBankroll } from '@/lib/api'
import type { MonteCarloResult } from '@/lib/api'

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
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-xl font-semibold text-white">Bankroll Management</h1>

      {/* Kelly Calculator section */}
      <section className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
        <h2 className="mb-3 text-sm font-semibold text-zinc-300">Kelly Calculator</h2>
        <KellyCalculator />
      </section>

      {/* Monte Carlo simulation trigger */}
      <section className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
        <h2 className="mb-3 text-sm font-semibold text-zinc-300">Monte Carlo Simulation</h2>
        <SimulateForm onSimulate={handleSimulate} isLoading={isLoading} />
        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        {mcResult && (
          <div className="mt-4">
            <MonteCarloChart result={mcResult} numBets={numBets} />
          </div>
        )}
      </section>

      {/* Exposure limits reminder */}
      <section className="rounded border border-zinc-700 bg-amber-950/20 p-4">
        <h2 className="mb-1 text-sm font-semibold text-amber-400">Exposure Limits</h2>
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
    'w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-zinc-500 font-mono'
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
          className="w-full rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {isLoading ? 'Simulating…' : 'Run Simulation'}
        </button>
      </div>
    </form>
  )
}
