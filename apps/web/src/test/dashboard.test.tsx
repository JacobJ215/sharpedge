import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AlphaBadge } from '@/components/ui/alpha-badge'
import { RegimeChip } from '@/components/value-plays/regime-chip'

describe('AlphaBadge', () => {
  it('renders PREMIUM badge with correct text', () => {
    render(<AlphaBadge badge="PREMIUM" />)
    expect(screen.getByText('PREMIUM')).toBeTruthy()
  })

  it('renders PREMIUM badge with emerald pill styling', () => {
    const { container } = render(<AlphaBadge badge="PREMIUM" />)
    const span = container.querySelector('span')
    expect(span?.className).toContain('emerald')
  })

  it('renders SPECULATIVE badge with correct text', () => {
    render(<AlphaBadge badge="SPECULATIVE" />)
    expect(screen.getByText('SPECULATIVE')).toBeTruthy()
  })

  it('renders SPECULATIVE badge with zinc/slate pill styling', () => {
    const { container } = render(<AlphaBadge badge="SPECULATIVE" />)
    const span = container.querySelector('span')
    expect(span?.className).toContain('zinc')
  })
})

describe('RegimeChip', () => {
  it('renders regime_state text in a chip element', () => {
    render(<RegimeChip regime="BULL_MARKET" />)
    expect(screen.getByText('BULL_MARKET')).toBeTruthy()
  })

  it('renders regime chip with monospace styling', () => {
    const { container } = render(<RegimeChip regime="BEAR_MARKET" />)
    const span = container.querySelector('span')
    expect(span?.className).toContain('mono')
  })
})
