/**
 * Tests for WIRE-01: /auth/login page
 * Login page renders email/password form, calls signInWithPassword on submit.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock next/navigation before any imports
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

// Mock supabase
const mockSignIn = vi.fn()
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: mockSignIn,
    },
  },
}))

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSignIn.mockResolvedValue({ data: { session: { access_token: 'tok' } }, error: null })
  })

  it('renders email and password inputs', async () => {
    const { default: LoginPage } = await import('@/app/auth/login/page')
    render(<LoginPage />)
    expect(document.getElementById('email')).toBeTruthy()
    expect(document.getElementById('password')).toBeTruthy()
  })

  it('renders a submit button', async () => {
    const { default: LoginPage } = await import('@/app/auth/login/page')
    render(<LoginPage />)
    expect(screen.getByRole('button', { name: /sign in|log in|login/i })).toBeTruthy()
  })

  it('calls signInWithPassword with email and password on submit', async () => {
    const { default: LoginPage } = await import('@/app/auth/login/page')
    render(<LoginPage />)

    fireEvent.change(document.getElementById('email')!, { target: { value: 'user@example.com' } })
    fireEvent.change(document.getElementById('password')!, { target: { value: 'secret123' } })
    fireEvent.submit(document.querySelector('form')!)

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({ email: 'user@example.com', password: 'secret123' })
    })
  })

  it('redirects to / on successful login', async () => {
    const { default: LoginPage } = await import('@/app/auth/login/page')
    render(<LoginPage />)

    fireEvent.change(document.getElementById('email')!, { target: { value: 'user@example.com' } })
    fireEvent.change(document.getElementById('password')!, { target: { value: 'secret' } })
    fireEvent.submit(document.querySelector('form')!)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  it('shows error message when signInWithPassword returns an error', async () => {
    mockSignIn.mockResolvedValue({ data: {}, error: { message: 'Invalid credentials' } })
    const { default: LoginPage } = await import('@/app/auth/login/page')
    render(<LoginPage />)

    fireEvent.change(document.getElementById('email')!, { target: { value: 'bad@example.com' } })
    fireEvent.change(document.getElementById('password')!, { target: { value: 'wrong' } })
    fireEvent.submit(document.querySelector('form')!)

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeTruthy()
    })
  })
})
