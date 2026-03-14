import Link from 'next/link'
import type { ReactNode } from 'react'

const navItems = [
  { href: '/', label: 'Portfolio' },
  { href: '/value-plays', label: 'Value Plays' },
  { href: '/bankroll', label: 'Bankroll' },
  { href: '/copilot', label: 'Copilot' },
  { href: '/prediction-markets', label: 'Pred Markets' },
]

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <nav className="w-48 shrink-0 border-r border-zinc-800 px-2 py-4">
        <div className="mb-4 px-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            SharpEdge
          </span>
        </div>
        <ul className="space-y-0.5">
          {navItems.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="block rounded px-2 py-1.5 text-xs text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <main className="min-w-0 flex-1 p-4">{children}</main>
    </div>
  )
}
