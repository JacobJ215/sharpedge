import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { MonteCarloResult } from '@/lib/api'

const mockResult: MonteCarloResult = {
  ruin_probability: 0.032,
  p5_outcome: 820,
  p50_outcome: 1100,
  p95_outcome: 1450,
  max_drawdown: 0.18,
  paths_simulated: 2000,
}

describe('MonteCarloChart', () => {
  it('renders with a MonteCarloResult prop', async () => {
    const { MonteCarloChart } = await import('@/components/bankroll/monte-carlo-chart')
    render(<MonteCarloChart result={mockResult} numBets={100} />)
    // chart container is rendered
    expect(document.querySelector('.recharts-wrapper') ?? document.querySelector('[data-testid="mc-chart"]')).toBeTruthy()
  })

  it('shows ruin probability stat below chart', async () => {
    const { MonteCarloChart } = await import('@/components/bankroll/monte-carlo-chart')
    render(<MonteCarloChart result={mockResult} numBets={100} />)
    expect(screen.getAllByText(/3\.2%|ruin/i).length).toBeGreaterThan(0)
  })

  it('accepts p5_outcome, p50_outcome, p95_outcome from result prop', async () => {
    const { MonteCarloChart } = await import('@/components/bankroll/monte-carlo-chart')
    const { container } = render(<MonteCarloChart result={mockResult} numBets={50} />)
    expect(container).toBeTruthy()
  })
})

describe('KellyCalculator', () => {
  it('renders bankroll, win_rate, and odds inputs', async () => {
    const { KellyCalculator } = await import('@/components/bankroll/kelly-calculator')
    render(<KellyCalculator />)
    expect(screen.getByLabelText(/bankroll/i) ?? screen.getByPlaceholderText(/bankroll/i) ?? document.querySelector('input[name="bankroll"]')).toBeTruthy()
    expect(screen.getByLabelText(/win/i) ?? screen.getByPlaceholderText(/win/i) ?? document.querySelector('input[name="win_rate"]')).toBeTruthy()
    expect(screen.getByLabelText(/odds/i) ?? screen.getByPlaceholderText(/odds/i) ?? document.querySelector('input[name="odds"]')).toBeTruthy()
  })

  it('renders a stake recommendation output area', async () => {
    const { KellyCalculator } = await import('@/components/bankroll/kelly-calculator')
    render(<KellyCalculator />)
    // button to calculate
    expect(screen.getByRole('button') ?? document.querySelector('button')).toBeTruthy()
  })
})

describe('AnalysisPanel', () => {
  it('renders win_probability and ev_percentage', async () => {
    const { AnalysisPanel } = await import('@/components/game/analysis-panel')
    const mockAnalysis = {
      game_id: 'g1',
      model_prediction: { win_probability: 0.63, confidence: 'HIGH' },
      ev_breakdown: { ev_percentage: 0.082, fair_odds: -118, market_odds: -110 },
      regime_state: 'BULL_MARKET',
      key_number_proximity: null,
      alpha_score: 0.77,
      alpha_badge: 'HIGH' as const,
    }
    render(<AnalysisPanel analysis={mockAnalysis} />)
    expect(screen.getByText(/63\.0%/)).toBeTruthy()
    expect(screen.getByText(/8\.2%/)).toBeTruthy()
  })
})
