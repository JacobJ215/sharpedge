/**
 * Browser-side base URL for Odds API calls.
 * Uses same-origin proxy (see app/api/v1/odds/[...slug]/route.ts).
 */
export const ODDS_API_BASE = ''

export function oddsUrl(pathWithQuery: string): string {
  const q = pathWithQuery.startsWith('/') ? pathWithQuery : `/${pathWithQuery}`
  return `${ODDS_API_BASE}/api/v1/odds${q}`
}

export async function readOddsError(res: Response): Promise<string> {
  const t = await res.text()
  try {
    const j = JSON.parse(t) as { detail?: unknown }
    if (typeof j.detail === 'string') {
      if (j.detail === 'Not Found') {
        return (
          'Odds routes were not found. The Next app proxies to your FastAPI server: set API_URL ' +
          '(server-side on Vercel) to the webhook base URL, or run the webhook server locally on port 8000.'
        )
      }
      return j.detail
    }
  } catch {
    /* not JSON */
  }
  return t.trim() || `${res.status} ${res.statusText}`
}
