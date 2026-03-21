const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface ValuePlay {
  id: string
  event: string
  market: string
  team: string
  our_odds: number
  book_odds: number
  expected_value: number
  book: string
  timestamp: string
  alpha_score: number
  alpha_badge: 'PREMIUM' | 'HIGH' | 'MEDIUM' | 'SPECULATIVE'
  regime_state: string
}

export interface Portfolio {
  user_id: string
  roi: number
  win_rate: number
  clv_average: number
  drawdown: number
  total_bets: number
  wins: number
  losses: number
  active_bets: Array<{ id: string; event: string; stake: number; book: string }>
}

export interface MonteCarloResult {
  ruin_probability: number
  p5_outcome: number
  p50_outcome: number
  p95_outcome: number
  max_drawdown: number
  paths_simulated: number
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

export async function getValuePlays(params?: {
  min_alpha?: number
  sport?: string
  limit?: number
}): Promise<ValuePlay[]> {
  const qs = new URLSearchParams()
  if (params?.min_alpha != null) qs.set('min_alpha', String(params.min_alpha))
  if (params?.sport) qs.set('sport', params.sport)
  if (params?.limit) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  return apiFetch<ValuePlay[]>(`/api/v1/value-plays${query}`)
}

export async function getPortfolio(userId: string, token: string): Promise<Portfolio> {
  return apiFetch<Portfolio>(`/api/v1/users/${userId}/portfolio`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function simulateBankroll(params: {
  bankroll: number
  bet_size: number
  num_bets: number
  win_rate: number
}): Promise<MonteCarloResult> {
  return apiFetch<MonteCarloResult>('/api/v1/bankroll/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

export interface SwarmFilterStep {
  step: number
  name: string
  description: string
  status: 'complete' | 'active' | 'pending'
  passed: number | null
  removed: number | null
}

export interface SwarmQualifiedMarket {
  market_id: string
  title: string
  edge: number
  platform: string
}

export interface SwarmPipeline {
  agent_status: string
  active_markets: number
  steps: SwarmFilterStep[]
  qualified_markets: SwarmQualifiedMarket[]
}

export interface SwarmCalibrationFeatures {
  sentiment_score: number
  time_decay: number
  market_correlation: number
}

export interface SwarmModelConfidence {
  data_quality: 'High' | 'Medium' | 'Low'
  feature_signal: 'Strong' | 'Moderate' | 'Weak'
  uncertainty: 'Low' | 'Moderate' | 'High'
}

export interface SwarmCalibrationLatest {
  market_id: string
  market_title: string
  resolve_date: string | null
  volume: number | null
  base_prob: number
  calibrated_prob: number
  market_price: number
  edge: number
  direction: 'BUY' | 'SELL' | null
  confidence_score: number
  features: SwarmCalibrationFeatures
  llm_adjustment: number
  model_confidence: SwarmModelConfidence
}

export interface SwarmCalibrationRecent {
  market_id: string
  base_prob: number
  calibrated_prob: number
  created_at: string
}

export interface SwarmCalibration {
  latest: SwarmCalibrationLatest | null
  recent: SwarmCalibrationRecent[]
}

export async function getSwarmPipeline(): Promise<SwarmPipeline> {
  return apiFetch<SwarmPipeline>('/api/v1/swarm/pipeline')
}

export async function getSwarmCalibration(): Promise<SwarmCalibration> {
  return apiFetch<SwarmCalibration>('/api/v1/swarm/calibration')
}
