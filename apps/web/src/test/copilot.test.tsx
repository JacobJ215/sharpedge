import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ValuePlay } from '@/lib/api'

// Mock fetch for SSE tests
beforeEach(() => {
  vi.restoreAllMocks()
})

describe('ChatStream', () => {
  it('renders an input field and a send button', async () => {
    const { ChatStream } = await import('@/components/copilot/chat-stream')
    render(<ChatStream />)
    expect(document.querySelector('input') ?? document.querySelector('textarea')).toBeTruthy()
    expect(screen.getByRole('button')).toBeTruthy()
  })

  it('renders a scrollable message list container', async () => {
    const { ChatStream } = await import('@/components/copilot/chat-stream')
    render(<ChatStream />)
    // overflow-y-auto or overflow-auto container
    expect(document.querySelector('[class*="overflow"]')).toBeTruthy()
  })

  it('calls fetch with POST on send with mocked SSE stream', async () => {
    // Build a minimal ReadableStream that yields SSE data then closes
    const sseBody = 'data: hello\n\ndata: [DONE]\n\n'
    const encoder = new TextEncoder()
    const encoded = encoder.encode(sseBody)

    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoded)
        controller.close()
      },
    })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: mockStream,
    })
    vi.stubGlobal('fetch', mockFetch)

    const { ChatStream } = await import('@/components/copilot/chat-stream')
    render(<ChatStream />)

    const input = document.querySelector('input') ?? document.querySelector('textarea')
    if (input) {
      fireEvent.change(input, { target: { value: 'Test message' } })
    }
    fireEvent.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/copilot/chat')
    expect(options.method).toBe('POST')
  })

  it('displays streamed message content after send', async () => {
    const sseBody = 'data: hello\n\ndata: [DONE]\n\n'
    const encoder = new TextEncoder()
    const encoded = encoder.encode(sseBody)

    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoded)
        controller.close()
      },
    })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: mockStream,
    })
    vi.stubGlobal('fetch', mockFetch)

    const { ChatStream } = await import('@/components/copilot/chat-stream')
    render(<ChatStream />)

    const input = document.querySelector('input') ?? document.querySelector('textarea')
    if (input) {
      fireEvent.change(input, { target: { value: 'hi' } })
    }
    fireEvent.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(screen.queryByText('hello') ?? screen.queryByText(/hello/)).toBeTruthy()
    }, { timeout: 2000 })
  })
})

describe('PmTable', () => {
  const mockPlays: ValuePlay[] = [
    {
      id: 'pm1',
      event: 'Kalshi-NFL-2026-Q1',
      market: 'Will Patriots win?',
      team: '',
      our_odds: 1.9,
      book_odds: 1.8,
      expected_value: 0.06,
      book: 'Kalshi',
      timestamp: '2026-03-14T00:00:00Z',
      alpha_score: 0.78,
      alpha_badge: 'HIGH',
      regime_state: 'NEWS_CATALYST',
    },
  ]

  it('renders a row with alpha badge', async () => {
    const { PmTable } = await import('@/components/prediction-markets/pm-table')
    render(<PmTable plays={mockPlays} />)
    expect(screen.getByText('HIGH')).toBeTruthy()
  })

  it('renders a row with regime chip', async () => {
    const { PmTable } = await import('@/components/prediction-markets/pm-table')
    render(<PmTable plays={mockPlays} />)
    expect(screen.getByText('NEWS_CATALYST')).toBeTruthy()
  })

  it('shows platform column from event field', async () => {
    const { PmTable } = await import('@/components/prediction-markets/pm-table')
    render(<PmTable plays={mockPlays} />)
    expect(screen.getByText('Kalshi')).toBeTruthy()
  })
})
