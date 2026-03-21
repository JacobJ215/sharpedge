import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'

const TIER_ORDER = { free: 0, pro: 1, sharp: 2 } as const
type Tier = keyof typeof TIER_ORDER

// Route prefixes requiring a minimum subscriber tier
const ROUTE_MIN_TIER: Record<string, Tier> = {
  '/portfolio':          'pro',
  '/value-plays':        'pro',
  '/bankroll':           'pro',
  '/copilot':            'pro',
  '/prediction-markets': 'pro',
  '/analytics':          'pro',
  '/lines':              'pro',
  '/props':              'pro',
}

// Route prefixes that are OPERATOR-ONLY (platform owner only — never shown to subscribers)
// Covers all execution, swarm, paper-trading, capital-gate, and ablation surfaces.
const OPERATOR_ROUTES = [
  '/execution',
  '/swarm',
  '/paper-trading',
  '/capital-gate',
  '/ablation',
  '/shadow-ledger',
]

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check operator-only routes first
  const isOperatorRoute = OPERATOR_ROUTES.some(prefix => pathname.startsWith(prefix))

  // Find matching subscriber tier route
  const requiredTier = Object.entries(ROUTE_MIN_TIER)
    .find(([prefix]) => pathname.startsWith(prefix))?.[1]

  // No restriction for this route — pass through
  if (!isOperatorRoute && !requiredTier) return NextResponse.next()

  const response = NextResponse.next({
    request: { headers: request.headers },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  // Operator route check — only the platform owner (is_operator: true) may access
  if (isOperatorRoute) {
    const isOperator = session.user.app_metadata?.is_operator === true
    if (!isOperator) {
      // Silently redirect to dashboard root — no upgrade prompt for restricted routes
      return NextResponse.redirect(new URL('/', request.url))
    }
    return response
  }

  // Subscriber tier check
  const userTier = (session.user.app_metadata?.tier ?? 'free') as Tier
  const hasAccess = TIER_ORDER[userTier] >= TIER_ORDER[requiredTier!]

  if (!hasAccess) {
    return NextResponse.redirect(new URL('/upgrade', request.url))
  }

  return response
}

export const config = {
  matcher: [
    // Subscriber-tier routes
    '/portfolio/:path*',
    '/value-plays/:path*',
    '/bankroll/:path*',
    '/copilot/:path*',
    '/prediction-markets/:path*',
    '/analytics/:path*',
    '/lines/:path*',
    '/props/:path*',
    '/account/:path*',
    // Operator-only routes (execution / swarm surfaces)
    '/execution/:path*',
    '/swarm/:path*',
    '/paper-trading/:path*',
    '/capital-gate/:path*',
    '/ablation/:path*',
    '/shadow-ledger/:path*',
  ],
}
