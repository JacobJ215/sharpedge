/**
 * Human labels for The Odds API alternate / prop market keys.
 * Keys must match Odds API documentation for the selected sport.
 */
export type PropMarketOption = { label: string; value: string; sports?: string[] }

export const PROP_MARKET_OPTIONS: PropMarketOption[] = [
  { label: 'Player points', value: 'player_points', sports: ['NBA', 'NCAAB'] },
  { label: 'Player rebounds', value: 'player_rebounds', sports: ['NBA', 'NCAAB'] },
  { label: 'Player assists', value: 'player_assists', sports: ['NBA', 'NCAAB'] },
  { label: 'Player made threes', value: 'player_threes', sports: ['NBA', 'NCAAB'] },
  {
    label: 'Points + rebounds + assists',
    value: 'player_points_rebounds_assists',
    sports: ['NBA', 'NCAAB'],
  },
  { label: 'Passing yards', value: 'player_pass_yds', sports: ['NFL', 'NCAAF'] },
  { label: 'Passing touchdowns', value: 'player_pass_tds', sports: ['NFL', 'NCAAF'] },
  { label: 'Rushing yards', value: 'player_rush_yds', sports: ['NFL', 'NCAAF'] },
  { label: 'Receiving yards', value: 'player_reception_yds', sports: ['NFL', 'NCAAF'] },
]

export function propMarketsForSport(sport: string): PropMarketOption[] {
  const s = sport.toUpperCase()
  const filtered = PROP_MARKET_OPTIONS.filter((o) => !o.sports || o.sports.includes(s))
  return filtered.length ? filtered : PROP_MARKET_OPTIONS
}
