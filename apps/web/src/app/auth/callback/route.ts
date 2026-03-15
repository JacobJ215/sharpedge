/**
 * GET /auth/callback — Supabase email confirmation callback handler.
 * Exchanges the one-time code for a session and redirects to the dashboard.
 */
import { NextResponse, type NextRequest } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  if (code) {
    await supabase.auth.exchangeCodeForSession(code)
  }

  // Always redirect to dashboard — successful exchange or not
  return NextResponse.redirect(`${origin}/`)
}
