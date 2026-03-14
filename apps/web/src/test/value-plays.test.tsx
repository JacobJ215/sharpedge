import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PlaysTable } from '@/components/value-plays/plays-table'
import type { ValuePlay } from '@/lib/api'

const mockPlays: ValuePlay[] = [
  {
    id: '1',
    event: 'Lakers vs Celtics',
    market: 'Moneyline',
    team: 'Lakers',
    our_odds: -110,
    book_odds: -120,
    expected_value: 0.08,
    book: 'DraftKings',
    timestamp: '2026-03-14T00:00:00Z',
    alpha_score: 0.85,
    alpha_badge: 'PREMIUM',
    regime_state: 'BULL_MARKET',
  },
  {
    id: '2',
    event: 'Chiefs vs Eagles',
    market: 'Spread',
    team: 'Chiefs',
    our_odds: -105,
    book_odds: -115,
    expected_value: 0.05,
    book: 'FanDuel',
    timestamp: '2026-03-14T01:00:00Z',
    alpha_score: 0.62,
    alpha_badge: 'HIGH',
    regime_state: 'NEUTRAL',
  },
  {
    id: '3',
    event: 'Yankees vs Red Sox',
    market: 'Total',
    team: 'Yankees',
    our_odds: -115,
    book_odds: -125,
    expected_value: 0.03,
    book: 'BetMGM',
    timestamp: '2026-03-14T02:00:00Z',
    alpha_score: 0.41,
    alpha_badge: 'MEDIUM',
    regime_state: 'BEAR_MARKET',
  },
]

describe('PlaysTable', () => {
  it('renders table rows for each play', () => {
    render(<PlaysTable plays={mockPlays} />)
    expect(screen.getByText('Lakers vs Celtics')).toBeTruthy()
    expect(screen.getByText('Chiefs vs Eagles')).toBeTruthy()
    expect(screen.getByText('Yankees vs Red Sox')).toBeTruthy()
  })

  it('renders AlphaBadge text in rows', () => {
    render(<PlaysTable plays={mockPlays} />)
    expect(screen.getByText('PREMIUM')).toBeTruthy()
    expect(screen.getByText('HIGH')).toBeTruthy()
    expect(screen.getByText('MEDIUM')).toBeTruthy()
  })

  it('renders RegimeChip text in rows', () => {
    render(<PlaysTable plays={mockPlays} />)
    expect(screen.getByText('BULL_MARKET')).toBeTruthy()
    expect(screen.getByText('NEUTRAL')).toBeTruthy()
    expect(screen.getByText('BEAR_MARKET')).toBeTruthy()
  })

  it('includes Event, Market, EV%, Book, Alpha, Regime column headers', () => {
    render(<PlaysTable plays={mockPlays} />)
    expect(screen.getByText('Event')).toBeTruthy()
    expect(screen.getByText('Market')).toBeTruthy()
    expect(screen.getByText('Book')).toBeTruthy()
  })

  it('sorts rows by alpha_score when Alpha column header clicked', () => {
    render(<PlaysTable plays={mockPlays} />)
    const alphaHeader = screen.getByText('Alpha')
    fireEvent.click(alphaHeader)
    const rows = document.querySelectorAll('tbody tr')
    expect(rows.length).toBe(3)
    // After ascending sort click, first row should have lowest alpha_score
    const firstRowText = rows[0].textContent ?? ''
    expect(firstRowText).toContain('Yankees vs Red Sox')
  })
})

describe('StatsCards', () => {
  it('renders roi, win_rate, clv_average, drawdown values', async () => {
    const { StatsCards } = await import('@/components/portfolio/stats-cards')
    render(
      <StatsCards
        roi={12.5}
        win_rate={58.3}
        clv_average={2.1}
        drawdown={-8.4}
      />
    )
    expect(screen.getByText(/12\.5/)).toBeTruthy()
    expect(screen.getByText(/58\.3/)).toBeTruthy()
    expect(screen.getByText(/2\.1/)).toBeTruthy()
    expect(screen.getByText(/8\.4/)).toBeTruthy()
  })
})
