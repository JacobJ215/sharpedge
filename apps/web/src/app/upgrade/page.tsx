'use client'

import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import { microcopy } from '@/lib/microcopy'

export default function UpgradePage() {
  const router = useRouter()
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="w-full max-w-md rounded border border-zinc-800 bg-zinc-900 p-8 text-center">
        <div className="mb-6">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            SharpEdge
          </span>
          <h1 className="mt-2 text-lg font-semibold text-zinc-100">
            {microcopy.upgradePageTitle}
          </h1>
          <p className="mt-2 text-xs text-zinc-400">
            {microcopy.upgradePageSubtitle}
          </p>
        </div>

        <div className="space-y-3">
          <a
            href={process.env.NEXT_PUBLIC_WHOP_STOREFRONT_URL ?? microcopy.whopStorefrontUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full rounded bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-500"
          >
            {microcopy.upgradeCtaWhop}
          </a>
          <Link
            href="/account"
            className="block text-xs text-zinc-500 hover:text-zinc-400"
          >
            {microcopy.upgradeBackDashboard}
          </Link>
          <button
            onClick={async () => { await supabase.auth.signOut(); router.replace('/auth/login') }}
            className="block w-full text-xs text-zinc-700 hover:text-zinc-500"
          >
            {microcopy.upgradeSignOut}
          </button>
        </div>

        <p className="mt-6 text-[10px] text-zinc-600">
          {microcopy.upgradeFootnote}
        </p>
      </div>
    </div>
  )
}
