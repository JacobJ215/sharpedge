/**
 * Product copy for upgrade flows, tier gates, and odds tools.
 * Keep in sync with apps/mobile/lib/copy/microcopy.dart (same keys / meaning).
 * Discord tier embeds: apps/bot/src/sharpedge_bot/microcopy.py (same Whop URL + PM = Pro).
 */
export const microcopy = {
  /** Prediction markets surfaces (web /prediction-markets, mobile Markets, Discord /pm-*): Pro minimum */
  predictionMarketsMinTier: 'pro' as const,
  upgradePageTitle: 'Upgrade to unlock this feature',
  upgradePageSubtitle:
    'This feature requires a Pro or Sharp subscription. Upgrade on Whop to get instant access.',
  upgradeCtaWhop: 'Upgrade on Whop',
  upgradeBackDashboard: 'Back to dashboard',
  upgradeSignOut: 'Sign out',
  upgradeFootnote:
    'Already subscribed? Your access updates automatically within 30 seconds. Try refreshing the page.',

  mobileUpgradeDefaultBody: 'This feature requires a Pro subscription.',
  mobileUpgradeWebHint: 'Upgrade on the web to unlock full access.',

  linesPageTitle: 'Line shop',
  linesPageSubtitle: 'Best prices across books for spreads, totals, and moneylines.',
  propsPageTitle: 'Props explorer',
  propsPageSubtitle: 'Player and alternate markets from The Odds API — pick a sport, game, and prop type.',

  oddsApiUnavailable: 'Odds data is temporarily unavailable. Check ODDS_API_KEY and try again.',

  /** Default Whop storefront when env is unset — keep aligned with mobile upgrade_prompt.dart */
  whopStorefrontUrl: 'https://whop.com/sharpedge/',
} as const
