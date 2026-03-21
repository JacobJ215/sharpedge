/// Product copy for upgrade flows, tier gates, and odds tools.
/// Keep in sync with apps/web/src/lib/microcopy.ts (same keys / meaning).
/// Discord tier embeds: apps/bot/src/sharpedge_bot/microcopy.py (same Whop URL; PM = Pro).
class Microcopy {
  Microcopy._();

  static const upgradePageTitle = 'Upgrade to unlock this feature';
  static const upgradePageSubtitle =
      'This feature requires a Pro or Sharp subscription. Upgrade on Whop to get instant access.';
  static const upgradeCtaWhop = 'Upgrade on Whop';

  static const mobileUpgradeDefaultBody =
      'This feature requires a Pro subscription.';
  static const mobileUpgradeWebHint =
      'Upgrade on the web to unlock full access.';

  static const linesPageTitle = 'Line shop';
  static const linesPageSubtitle =
      'Best prices across books for spreads, totals, and moneylines.';

  static const propsPageTitle = 'Props explorer';
  static const propsPageSubtitle =
      'Player and alternate markets (pass a market key from The Odds API).';

  static const oddsApiUnavailable =
      'Odds data is temporarily unavailable. Try again later.';

  /// Keep aligned with apps/web microcopy.whopStorefrontUrl
  static const whopStorefrontUrl = 'https://whop.com/sharpedge/';

  /// Web /prediction-markets, mobile Markets, Discord /pm-* — all Pro minimum.
  static const predictionMarketsMinTier = 'pro';
}
