import { NextRequest, NextResponse } from 'next/server'

/**
 * Proxy Odds API routes to the FastAPI webhook server so the browser always
 * hits the Next origin (avoids 404 when NEXT_PUBLIC_API_URL pointed at the web app).
 *
 * Set API_URL (server-only) to the webhook base, e.g. http://localhost:8000
 * Falls back to NEXT_PUBLIC_API_URL, then localhost.
 */
function upstreamBase(): string {
  const raw =
    process.env.API_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    'http://127.0.0.1:8000'
  return raw.replace(/\/+$/, '')
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
) {
  const { slug } = await context.params
  if (!slug?.length) {
    return NextResponse.json({ detail: 'Missing odds path' }, { status: 400 })
  }

  const path = slug.map((s) => encodeURIComponent(s)).join('/')
  const search = request.nextUrl.search
  const url = `${upstreamBase()}/api/v1/odds/${path}${search}`

  let res: Response
  try {
    res = await fetch(url, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Upstream fetch failed'
    return NextResponse.json(
      { detail: `Cannot reach odds API (${upstreamBase()}). ${msg}` },
      { status: 502 },
    )
  }

  const body = await res.text()
  const ct = res.headers.get('content-type') ?? 'application/json'
  return new NextResponse(body, { status: res.status, headers: { 'Content-Type': ct } })
}
