'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const PLANS = [
  {
    name: 'Starter',
    price: 'Free',
    period: '',
    description: 'Explore the edge. No card required.',
    color: 'border-zinc-700',
    badge: null,
    features: [
      'Live value plays (limited)',
      'Basic EV calculations',
      'Public money indicators',
      '3 sports covered',
      'Community feed access',
    ],
    cta: 'Get started free',
    ctaHref: '/auth/login',
    ctaStyle: 'border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white',
  },
  {
    name: 'Pro',
    price: '$19.99',
    period: '/mo',
    description: 'Full edge: value, markets, portfolio, and AI copilot.',
    color: 'border-emerald-500/40',
    badge: 'Most popular',
    features: [
      'Unlimited value plays',
      'Sharp money & line movement',
      'Prediction markets dashboard',
      'Line shop & props explorer (multi-book odds)',
      'Portfolio: ROI / P/L curves, splits, active bets',
      'AI copilot & game analysis',
      'Mobile app (iOS/Android)',
    ],
    cta: 'Start Pro',
    ctaHref: '/auth/login',
    ctaStyle: 'bg-emerald-600 text-white hover:bg-emerald-500',
  },
  {
    name: 'Sharp',
    price: '$49.99',
    period: '/mo',
    description: 'Everything in Pro plus arb hunting and CLV depth.',
    color: 'border-amber-500/30',
    badge: 'Sharp',
    features: [
      'Everything in Pro',
      'Sportsbook arbitrage scanner (Discord)',
      'CLV tracking & charts',
      'Weekly AI betting review',
      'Priority support',
    ],
    cta: 'Go Sharp',
    ctaHref: '/auth/login',
    ctaStyle: 'bg-amber-600 text-white hover:bg-amber-500',
  },
]

const FEATURES = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="2,15 7,8 11,11 18,3" />
        <polyline points="14,3 18,3 18,7" />
      </svg>
    ),
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/8',
    title: 'Sharp Money Tracking',
    desc: 'Follow institutional money flows in real-time. Identify reverse line movement before the books adjust.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="10" cy="10" r="7" />
        <path d="M10 5v2.5M10 12.5V15M5 10h2.5M12.5 10H15" />
        <circle cx="10" cy="10" r="2" fill="currentColor" stroke="none" />
      </svg>
    ),
    color: 'text-blue-400',
    bg: 'bg-blue-500/8',
    title: 'Prediction Markets',
    desc: 'Cross-venue dislocation signals across Polymarket, Kalshi, and global prediction markets.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M3 15 7 9 11 11.5 17 4" />
        <circle cx="3" cy="15" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="7" cy="9" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="11" cy="11.5" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="17" cy="4" r="1.5" fill="currentColor" stroke="none" />
      </svg>
    ),
    color: 'text-violet-400',
    bg: 'bg-violet-500/8',
    title: 'AI Copilot Analysis',
    desc: 'LLM-powered agentic brief synthesizing sharp signals, situational edges, and market regimes.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <rect x="2" y="10" width="4" height="8" rx="1" />
        <rect x="8" y="6" width="4" height="12" rx="1" />
        <rect x="14" y="2" width="4" height="16" rx="1" />
      </svg>
    ),
    color: 'text-amber-400',
    bg: 'bg-amber-500/8',
    title: 'Portfolio Intelligence',
    desc: 'Track ROI curves, CLV performance, bankroll evolution, and drawdown management over time.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M10 2L12.4 7.6H18L13.5 11.2 15.3 17 10 13.4 4.7 17 6.5 11.2 2 7.6H7.6Z" />
      </svg>
    ),
    color: 'text-rose-400',
    bg: 'bg-rose-500/8',
    title: 'Key Numbers & ATS Radar',
    desc: 'NFL key numbers (3, 7, 10), ATS situational edges, home dog bias, divisional trends.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M2 6h16M2 10h11M2 14h7" />
      </svg>
    ),
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/8',
    title: 'Intelligence Feed',
    desc: 'Unified stream of steam moves, sharp action, value plays, and arbitrage — filtered in real-time.',
  },
]

const CHART_BARS = [42, 67, 38, 82, 55, 91, 63, 74, 48, 88, 59, 95]

export default function LandingPage() {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace('/portfolio')
      } else {
        setChecking(false)
      }
    })
  }, [router])

  if (checking) {
    return <div className="min-h-screen bg-[#09090b]" />
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 overflow-x-hidden">
      <style>{`
        @keyframes float-up {
          0% { transform: translateY(0px) rotateX(15deg); }
          50% { transform: translateY(-12px) rotateX(15deg); }
          100% { transform: translateY(0px) rotateX(15deg); }
        }
        @keyframes drift {
          0% { transform: translate(0, 0) rotate(0deg); }
          33% { transform: translate(8px, -6px) rotate(1deg); }
          66% { transform: translate(-4px, 4px) rotate(-0.5deg); }
          100% { transform: translate(0, 0) rotate(0deg); }
        }
        @keyframes ticker-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        @keyframes glow-pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.9; }
        }
        @keyframes number-tick {
          0% { opacity: 0.3; }
          50% { opacity: 1; }
          100% { opacity: 0.3; }
        }
        .float-panel { animation: float-up 6s ease-in-out infinite; }
        .drift-slow { animation: drift 12s ease-in-out infinite; }
        .ticker-track { animation: ticker-scroll 30s linear infinite; }
      `}</style>

      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-zinc-800/40 bg-[#09090b]/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-emerald-500/10 ring-1 ring-emerald-500/20">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1,11 5,6 8,8 13,2" />
              </svg>
            </div>
            <div>
              <div className="text-[12px] font-bold tracking-wider text-zinc-100">SharpEdge</div>
              <div className="text-[7px] font-semibold uppercase tracking-widest text-zinc-600">Intelligence</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="rounded px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:text-zinc-100">
              Sign in
            </Link>
            <Link href="/auth/login" className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-emerald-500">
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Ticker */}
      <div className="fixed top-[48px] left-0 right-0 z-40 overflow-hidden border-b border-zinc-800/30 bg-zinc-950/60 py-1">
        <div className="ticker-track flex gap-8 whitespace-nowrap text-[9px] font-mono font-semibold">
          {[
            { label: 'NFL SZN EV+', val: '+6.2%', color: 'text-emerald-400' },
            { label: 'SHARP MONEY', val: '↑ KC -3', color: 'text-blue-400' },
            { label: 'KXBTCD-01', val: '+4.1%', color: 'text-violet-400' },
            { label: 'RLM ALERT', val: 'PHI +2.5', color: 'text-amber-400' },
            { label: 'CLV LEADER', val: '+8.3%', color: 'text-emerald-400' },
            { label: 'NBA SHARP', val: '↑ BOS -4', color: 'text-blue-400' },
            { label: 'POLYMARKET', val: '+3.7%', color: 'text-violet-400' },
            { label: 'STEAM MOVE', val: 'LAR -6.5', color: 'text-rose-400' },
            { label: 'NFL SZN EV+', val: '+6.2%', color: 'text-emerald-400' },
            { label: 'SHARP MONEY', val: '↑ KC -3', color: 'text-blue-400' },
            { label: 'KXBTCD-01', val: '+4.1%', color: 'text-violet-400' },
            { label: 'RLM ALERT', val: 'PHI +2.5', color: 'text-amber-400' },
            { label: 'CLV LEADER', val: '+8.3%', color: 'text-emerald-400' },
            { label: 'NBA SHARP', val: '↑ BOS -4', color: 'text-blue-400' },
            { label: 'POLYMARKET', val: '+3.7%', color: 'text-violet-400' },
            { label: 'STEAM MOVE', val: 'LAR -6.5', color: 'text-rose-400' },
          ].map((item, i) => (
            <span key={i} className="flex items-center gap-2 text-zinc-600">
              <span className="text-zinc-700">{item.label}</span>
              <span className={item.color}>{item.val}</span>
              <span className="text-zinc-800">·</span>
            </span>
          ))}
        </div>
      </div>

      {/* Hero */}
      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden pt-24 pb-16">
        {/* Grid bg */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(#10b981 1px, transparent 1px), linear-gradient(90deg, #10b981 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }}
        />
        {/* Radial glow */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-[600px] w-[600px] rounded-full opacity-10" style={{ background: 'radial-gradient(circle, #10b981 0%, transparent 70%)' }} />
        </div>

        {/* Floating chart panel */}
        <div className="pointer-events-none absolute right-[5%] top-[20%] w-72 opacity-20 float-panel" style={{ perspective: '800px' }}>
          <div style={{ transform: 'rotateY(-20deg) rotateX(10deg)' }}>
            <div className="rounded border border-emerald-500/20 bg-zinc-900/60 p-4">
              <div className="mb-3 flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" style={{ animation: 'glow-pulse 2s ease-in-out infinite' }} />
                <span className="text-[8px] font-bold uppercase tracking-widest text-emerald-600">Live Edges</span>
              </div>
              <div className="flex items-end gap-1 h-16">
                {CHART_BARS.map((h, i) => (
                  <div
                    key={i}
                    className={`flex-1 rounded-t ${i % 3 === 0 ? 'bg-emerald-500' : i % 3 === 1 ? 'bg-blue-500' : 'bg-zinc-700'}`}
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Floating plays card */}
        <div className="pointer-events-none absolute left-[4%] top-[32%] w-52 opacity-15 drift-slow" style={{ perspective: '600px' }}>
          <div style={{ transform: 'rotateY(18deg) rotateX(8deg)' }}>
            <div className="rounded border border-blue-500/20 bg-zinc-900/50 p-3 space-y-2">
              {[
                { label: 'KC -3', ev: '+6.2%' },
                { label: 'PHI +2.5', ev: '+4.1%' },
                { label: 'BOS -4', ev: '+2.8%' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-[9px] text-zinc-400">{item.label}</span>
                  <span className="text-[9px] font-bold text-emerald-400">{item.ev}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Hero content */}
        <div className="relative z-10 max-w-3xl px-6 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-500">Live intelligence platform</span>
          </div>
          <h1 className="mb-5 text-4xl font-bold leading-tight tracking-tight text-zinc-50 sm:text-5xl lg:text-6xl">
            Surface the{' '}
            <span className="bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              sharp edge
            </span>{' '}
            before anyone else
          </h1>
          <p className="mb-8 mx-auto max-w-xl text-sm leading-relaxed text-zinc-400">
            AI-powered sports betting intelligence. Sharp money tracking, prediction market signals,
            ensemble ML models, and an agentic copilot — all in one platform.
          </p>
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link href="/auth/login" className="rounded bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-emerald-500 hover:shadow-lg hover:shadow-emerald-500/20">
              Start for free
            </Link>
            <Link href="#features" className="rounded border border-zinc-700 px-6 py-2.5 text-sm font-medium text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200">
              See how it works
            </Link>
          </div>
          <div className="mt-12 flex flex-wrap items-center justify-center gap-8 border-t border-zinc-800/60 pt-8">
            {[
              { val: '+8.3%', label: 'Avg CLV' },
              { val: '12ms', label: 'Signal latency' },
              { val: '5', label: 'Sports covered' },
              { val: '24/7', label: 'Live monitoring' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-xl font-bold text-zinc-100">{s.val}</div>
                <div className="text-[9px] font-semibold uppercase tracking-widest text-zinc-600">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-10 text-center">
          <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-emerald-600">Platform capabilities</div>
          <h2 className="text-2xl font-bold text-zinc-100">Everything serious bettors need</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded border border-zinc-800 bg-zinc-900/40 p-5 transition-all hover:border-zinc-700 hover:bg-zinc-900/80">
              <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded ${f.bg} ${f.color}`}>
                {f.icon}
              </div>
              <h3 className="mb-1.5 text-sm font-semibold text-zinc-100">{f.title}</h3>
              <p className="text-xs leading-relaxed text-zinc-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Signal showcase */}
      <section className="border-y border-zinc-800/60 bg-zinc-900/20 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-8 text-center">
            <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-blue-500">Live signal stream</div>
            <h2 className="text-xl font-bold text-zinc-100">Real-time intelligence feed</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { type: 'SHARP', color: 'border-blue-500/30 bg-blue-500/5', badge: 'text-blue-400 bg-blue-500/10', event: 'KC Chiefs -3', detail: 'Sharp money 78% · Steam +1.5pts', ev: '+6.2%' },
              { type: 'VALUE', color: 'border-emerald-500/30 bg-emerald-500/5', badge: 'text-emerald-400 bg-emerald-500/10', event: 'PHI Eagles +2.5', detail: 'Home dog · Post-bye edge', ev: '+4.1%' },
              { type: 'MARKET', color: 'border-violet-500/30 bg-violet-500/5', badge: 'text-violet-400 bg-violet-500/10', event: 'KXBTCD-01', detail: 'Discovery regime · Dislocation 3.7%', ev: '+3.7%' },
              { type: 'STEAM', color: 'border-rose-500/30 bg-rose-500/5', badge: 'text-rose-400 bg-rose-500/10', event: 'LAR Rams -6.5', detail: 'Line moved 1.5pts in 8 min', ev: '+2.9%' },
            ].map((item) => (
              <div key={item.event} className={`rounded border ${item.color} p-3`}>
                <div className="mb-2 flex items-center justify-between">
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider ${item.badge}`}>{item.type}</span>
                  <span className="font-mono text-xs font-bold text-emerald-400">{item.ev}</span>
                </div>
                <div className="mb-1 text-xs font-semibold text-zinc-200">{item.event}</div>
                <div className="text-[9px] text-zinc-500">{item.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-10 text-center">
          <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-emerald-600">Pricing</div>
          <h2 className="text-2xl font-bold text-zinc-100">Choose your edge tier</h2>
          <p className="mt-2 text-sm text-zinc-500">Start free, upgrade when you need more signal.</p>
        </div>
        <div className="grid gap-6 sm:grid-cols-3">
          {PLANS.map((plan) => (
            <div key={plan.name} className={`relative rounded border ${plan.color} bg-zinc-900/40 p-6 flex flex-col`}>
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className={`rounded-full px-3 py-0.5 text-[9px] font-bold uppercase tracking-wider ${plan.name === 'Pro' ? 'bg-emerald-600 text-white' : 'bg-amber-600 text-white'}`}>
                    {plan.badge}
                  </span>
                </div>
              )}
              <div className="mb-4">
                <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{plan.name}</div>
                <div className="mt-1 flex items-baseline gap-0.5">
                  <span className="text-3xl font-bold text-zinc-100">{plan.price}</span>
                  {plan.period && <span className="text-sm text-zinc-500">{plan.period}</span>}
                </div>
                <p className="mt-1.5 text-[11px] text-zinc-500">{plan.description}</p>
              </div>
              <ul className="mb-6 flex-1 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-xs text-zinc-400">
                    <svg className="mt-0.5 h-3 w-3 shrink-0 text-emerald-500" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth="2">
                      <polyline points="2,6 5,9 10,3" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>
              <Link href={plan.ctaHref} className={`block w-full rounded px-4 py-2 text-center text-xs font-semibold transition-all ${plan.ctaStyle}`}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="border-t border-zinc-800/60 bg-zinc-900/20 py-14">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-emerald-500">Get the edge today</span>
          </div>
          <h2 className="mb-3 text-2xl font-bold text-zinc-100">Ready to beat the closing line?</h2>
          <p className="mb-6 text-sm text-zinc-500">
            Join sharp bettors using SharpEdge to find positive expected value before the markets close.
          </p>
          <Link href="/auth/login" className="inline-flex items-center gap-2 rounded bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-emerald-500 hover:shadow-lg hover:shadow-emerald-500/20">
            Start for free
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M2 6h8M6 2l4 4-4 4" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800/40 px-6 py-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-emerald-500/10 ring-1 ring-emerald-500/20">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1,8 3.5,4.5 6,6 9,1.5" />
              </svg>
            </div>
            <span className="text-[10px] font-bold tracking-wider text-zinc-500">SharpEdge</span>
          </div>
          <p className="text-[9px] text-zinc-700">© 2026 SharpEdge Intelligence. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
