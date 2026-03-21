'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

const TIER_LABELS: Record<string, string> = {
  free: 'Free',
  pro: 'Pro',
  sharp: 'Sharp',
}

const TIER_COLORS: Record<string, string> = {
  free: 'text-zinc-400 border-zinc-700 bg-zinc-800',
  pro: 'text-emerald-400 border-emerald-700/50 bg-emerald-900/20',
  sharp: 'text-amber-400 border-amber-700/50 bg-amber-900/20',
}

export default function AccountPage() {
  const [tier, setTier] = useState<string>('free')
  const [email, setEmail] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUser() {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        setTier((session.user.app_metadata?.tier as string) ?? 'free')
        setEmail(session.user.email ?? '')
      }
      setLoading(false)
    }
    loadUser()
  }, [])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-xs text-zinc-600">Loading...</div>
      </div>
    )
  }

  const tierLabel = TIER_LABELS[tier] ?? 'Free'
  const tierColor = TIER_COLORS[tier] ?? TIER_COLORS.free

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-sm font-semibold text-zinc-100">Account</h1>
        <p className="mt-1 text-xs text-zinc-500">Manage your SharpEdge account and subscription.</p>
      </div>

      {/* User info */}
      <div className="rounded border border-zinc-800 bg-zinc-900 p-4">
        <div className="text-xs text-zinc-500">Email</div>
        <div className="mt-1 text-xs text-zinc-200">{email}</div>
      </div>

      {/* Current tier */}
      <div className="rounded border border-zinc-800 bg-zinc-900 p-4">
        <div className="text-xs text-zinc-500">Current Plan</div>
        <div className="mt-2 flex items-center gap-3">
          <span
            className={`inline-block rounded border px-3 py-1 text-xs font-semibold ${tierColor}`}
          >
            {tierLabel}
          </span>
          {tier === 'free' && (
            <a
              href="https://whop.com/sharpedge/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-emerald-400 hover:text-emerald-300"
            >
              Upgrade
            </a>
          )}
        </div>
      </div>

      {/* Subscription management */}
      <div className="rounded border border-zinc-800 bg-zinc-900 p-4">
        <div className="text-xs text-zinc-500">Subscription</div>
        <div className="mt-2">
          {tier !== 'free' ? (
            <a
              href="https://whop.com/manage"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300"
            >
              Manage subscription on Whop
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7.5 5.5v2a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2" />
                <path d="M6 1.5h2.5V4" />
                <path d="M4.5 5.5 8.5 1.5" />
              </svg>
            </a>
          ) : (
            <p className="text-xs text-zinc-600">
              No active subscription.{' '}
              <a
                href="https://whop.com/sharpedge/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-400 hover:text-emerald-300"
              >
                Subscribe on Whop
              </a>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
