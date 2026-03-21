import Link from 'next/link'

export default function UpgradePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="w-full max-w-md rounded border border-zinc-800 bg-zinc-900 p-8 text-center">
        <div className="mb-6">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            SharpEdge
          </span>
          <h1 className="mt-2 text-lg font-semibold text-zinc-100">
            Upgrade to unlock this feature
          </h1>
          <p className="mt-2 text-xs text-zinc-400">
            This feature requires a Pro or Sharp subscription.
            Upgrade on Whop to get instant access.
          </p>
        </div>

        <div className="space-y-3">
          <a
            href="https://whop.com/sharpedge/"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full rounded bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-500"
          >
            Upgrade on Whop
          </a>
          <Link
            href="/"
            className="block text-xs text-zinc-500 hover:text-zinc-400"
          >
            Back to dashboard
          </Link>
        </div>

        <p className="mt-6 text-[10px] text-zinc-600">
          Already subscribed? Your access updates automatically within 30 seconds.
          Try refreshing the page.
        </p>
      </div>
    </div>
  )
}
