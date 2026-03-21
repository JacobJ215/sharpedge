'use client'

import { useEffect, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { signOut } from '@/app/auth/actions'

type NavItem = { href: string; label: string; icon: ReactNode }

const navItems: NavItem[] = [
  {
    href: '/portfolio',
    label: 'Portfolio',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <rect x="1" y="6.5" width="2.5" height="5.5" rx="0.5" />
        <rect x="5.25" y="3.5" width="2.5" height="8.5" rx="0.5" />
        <rect x="9.5" y="1" width="2.5" height="11" rx="0.5" />
      </svg>
    ),
  },
  {
    href: '/value-plays',
    label: 'Value Plays',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="1,10 4.5,5.5 7.5,7.5 12,2" />
        <polyline points="8.5,2 12,2 12,5.5" />
      </svg>
    ),
  },
  {
    href: '/bankroll',
    label: 'Bankroll',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="6.5" cy="6.5" r="5" />
        <path d="M6.5 3.5v6M5 5.2c0-.9.67-1.7 1.5-1.7s1.5.8 1.5 1.7-.67 1.5-1.5 1.5S5 8 5 8.9s.67 1.6 1.5 1.6 1.5-.7 1.5-1.6" />
      </svg>
    ),
  },
  {
    href: '/copilot',
    label: 'Copilot',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6.5 1.5 8.2 5.5H12l-2.8 2 1.1 3.5-3.8-2.7-3.8 2.7L3.8 7.5 1 5.5h3.8z" />
      </svg>
    ),
  },
  {
    href: '/prediction-markets',
    label: 'Markets',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="6.5" cy="6.5" r="5" />
        <path d="M6.5 2v1.2M6.5 9.8V11M2 6.5h1.2M9.8 6.5H11" />
        <circle cx="6.5" cy="6.5" r="1.5" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    href: '/lines',
    label: 'Lines',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M1.5 9.5 4 7l2.5 2 2.5-3 2.5 2.5 2-2" />
        <circle cx="1.5" cy="9.5" r="0.9" fill="currentColor" stroke="none" />
        <circle cx="11.5" cy="6.5" r="0.9" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    href: '/props',
    label: 'Props',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M6.5 1.5v10M3 4.5h7M3 8.5h7" />
      </svg>
    ),
  },
  {
    href: '/swarm',
    label: 'Swarm',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6.5" cy="2.5" r="1.2" />
        <circle cx="2" cy="9" r="1.2" />
        <circle cx="11" cy="9" r="1.2" />
        <line x1="6.5" y1="3.7" x2="2.9" y2="7.9" />
        <line x1="6.5" y1="3.7" x2="10.1" y2="7.9" />
        <line x1="3.2" y1="9" x2="9.8" y2="9" />
      </svg>
    ),
  },
  {
    href: '/analytics',
    label: 'Analytics',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M2 10 5 6.5 8 8 11 3" />
        <circle cx="2" cy="10" r="1" fill="currentColor" stroke="none" />
        <circle cx="5" cy="6.5" r="1" fill="currentColor" stroke="none" />
        <circle cx="8" cy="8" r="1" fill="currentColor" stroke="none" />
        <circle cx="11" cy="3" r="1" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    href: '/feed',
    label: 'Feed',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M1.5 4h10M1.5 6.5h7M1.5 9h5" />
      </svg>
    ),
  },
  {
    href: '/account',
    label: 'Account',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6.5" cy="4" r="2.5" />
        <path d="M1.5 11.5c0-2.5 2.2-4 5-4s5 1.5 5 4" />
      </svg>
    ),
  },
]

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [checking, setChecking] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setAuthenticated(true)
      } else {
        setAuthenticated(false)
        router.replace('/auth/login')
      }
      setChecking(false)
    })
    return () => subscription.unsubscribe()
  }, [router])

  async function handleSignOut() {
    await signOut()
  }

  if (checking) {
    return <div className="min-h-screen bg-zinc-950" />
  }

  if (!authenticated) {
    return <div className="min-h-screen bg-zinc-950" />
  }

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <nav className="flex w-52 shrink-0 flex-col border-r border-zinc-800/60 bg-zinc-950 px-2 py-4">
        <div className="mb-5 flex items-center gap-2.5 px-2.5">
          <div className="flex h-6 w-6 items-center justify-center">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#10b981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1,9 4,5 7,6.5 11,2" />
            </svg>
          </div>
          <div>
            <div className="text-[11px] font-bold tracking-wider text-zinc-100">SharpEdge</div>
            <div className="text-[8px] font-semibold uppercase tracking-widest text-zinc-600">Intelligence</div>
          </div>
        </div>
        <ul className="flex-1 space-y-0.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-2.5 px-2.5 py-2 text-xs transition-colors ${
                    isActive
                      ? 'text-emerald-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  <span className={isActive ? 'text-emerald-400' : 'text-zinc-600'}>
                    {item.icon}
                  </span>
                  <span className={`font-medium ${isActive ? 'text-emerald-400' : ''}`}>
                    {item.label}
                  </span>
                  {isActive && (
                    <span className="ml-auto h-1 w-1 rounded-full bg-emerald-500" />
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
        <div className="border-t border-zinc-800/60 pt-3">
          <button
            onClick={handleSignOut}
            className="flex w-full items-center gap-2.5 rounded px-2.5 py-2 text-left text-xs text-zinc-600 transition-colors hover:bg-zinc-800/50 hover:text-zinc-400"
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 2H2a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h3M9 9.5l2.5-3L9 3.5M4 6.5h8" />
            </svg>
            Sign out
          </button>
        </div>
      </nav>
      <main className="min-w-0 flex-1 p-5">{children}</main>
    </div>
  )
}
