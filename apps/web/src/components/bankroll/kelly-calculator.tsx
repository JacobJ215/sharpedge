'use client'

import { useState } from 'react'

interface KellyResult {
  kellyFraction: number
  recommendedStake: number
}

function calcKelly(bankroll: number, winRate: number, decimalOdds: number): KellyResult {
  const lossRate = 1 - winRate
  const kellyFraction = Math.max(0, (decimalOdds * winRate - lossRate) / decimalOdds)
  return {
    kellyFraction,
    recommendedStake: bankroll * kellyFraction,
  }
}

export function KellyCalculator() {
  const [bankroll, setBankroll] = useState('')
  const [winRate, setWinRate] = useState('')
  const [odds, setOdds] = useState('')
  const [result, setResult] = useState<KellyResult | null>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const b = parseFloat(bankroll)
    const w = parseFloat(winRate)
    const o = parseFloat(odds)
    if (!isNaN(b) && !isNaN(w) && !isNaN(o) && o > 0) {
      setResult(calcKelly(b, w, o))
    }
  }

  const inputClass =
    'w-full rounded bg-zinc-900 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-zinc-500 font-mono'
  const labelClass = 'block text-xs text-zinc-500 mb-1'

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className={labelClass} htmlFor="bankroll">
          Bankroll ($)
        </label>
        <input
          id="bankroll"
          name="bankroll"
          type="number"
          min="0"
          step="any"
          placeholder="1000"
          value={bankroll}
          onChange={(e) => setBankroll(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label className={labelClass} htmlFor="win_rate">
          Win Probability (0–1)
        </label>
        <input
          id="win_rate"
          name="win_rate"
          type="number"
          min="0"
          max="1"
          step="0.01"
          placeholder="0.55"
          value={winRate}
          onChange={(e) => setWinRate(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label className={labelClass} htmlFor="odds">
          Decimal Odds
        </label>
        <input
          id="odds"
          name="odds"
          type="number"
          min="1"
          step="0.01"
          placeholder="1.91"
          value={odds}
          onChange={(e) => setOdds(e.target.value)}
          className={inputClass}
        />
      </div>
      <button
        type="submit"
        className="w-full rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-500 focus:outline-none"
      >
        Calculate
      </button>
      {result !== null && (
        <div className="rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs text-zinc-300">
          <p>
            Kelly fraction:{' '}
            <span className="font-mono text-emerald-400">{(result.kellyFraction * 100).toFixed(2)}%</span>
          </p>
          <p>
            Recommended stake:{' '}
            <span className="font-mono text-emerald-400">${result.recommendedStake.toFixed(2)}</span>
          </p>
        </div>
      )}
    </form>
  )
}
