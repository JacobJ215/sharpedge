/**
 * Tests for WIRE-01: Dashboard layout auth guard
 * Unauthenticated session triggers router.replace('/auth/login').
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'

// Mock next/navigation before any imports
const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}))

// Mock supabase — will be configured per test
const mockGetSession = vi.fn()
const mockOnAuthStateChange = vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } }))
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
    },
  },
}))

describe('DashboardLayout auth guard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects to /auth/login when session is null', async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } })

    const { default: DashboardLayout } = await import('@/app/(dashboard)/layout')
    render(<DashboardLayout>children</DashboardLayout>)

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/auth/login')
    })
  })

  it('renders children when session is present', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { access_token: 'valid-token' } } })

    const { default: DashboardLayout } = await import('@/app/(dashboard)/layout')
    const { getByText } = render(<DashboardLayout>hello</DashboardLayout>)

    await waitFor(() => {
      expect(getByText('hello')).toBeTruthy()
    })
  })

  it('renders skeleton while session check is pending', async () => {
    // getSession never resolves during this test
    mockGetSession.mockReturnValue(new Promise(() => {}))

    const { default: DashboardLayout } = await import('@/app/(dashboard)/layout')
    const { container } = render(<DashboardLayout>content</DashboardLayout>)

    // Skeleton div with bg-zinc-950 should be present immediately
    expect(container.querySelector('.bg-zinc-950')).toBeTruthy()
  })
})
