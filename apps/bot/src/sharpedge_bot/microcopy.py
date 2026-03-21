"""Product copy for Discord tier gates.

Keep aligned with apps/web/src/lib/microcopy.ts and
apps/mobile/lib/copy/microcopy.dart (Whop URL + upgrade tone).

Policy: prediction-market slash commands are **Pro** minimum (same as web
/prediction-markets and mobile Markets).
"""

from __future__ import annotations

from sharpedge_shared.types import Tier

# Same default as web microcopy.whopStorefrontUrl / Microcopy.whopStorefrontUrl
WHOP_STOREFRONT_URL = "https://whop.com/sharpedge/"

_TIER_LABEL = {
    Tier.FREE: "Free",
    Tier.PRO: "Pro",
    Tier.SHARP: "Sharp",
}


def tier_gate_title(min_tier: Tier) -> str:
    return f"{_TIER_LABEL.get(min_tier, min_tier.value.title())} feature"


def tier_gate_description(min_tier: Tier, current_tier: Tier) -> str:
    need = _TIER_LABEL.get(min_tier, min_tier.value.title())
    have = _TIER_LABEL.get(current_tier, current_tier.value.title())
    if min_tier == Tier.SHARP:
        req_line = f"This feature requires **{need}** tier."
    else:
        req_line = f"This feature requires **{need}** or higher."
    return (
        f"{req_line}\n"
        f"Your current tier: **{have}**\n\n"
        "Use `/subscribe` to upgrade on Whop and unlock:\n"
        "• Prediction markets (Kalshi / Polymarket)\n"
        "• Game analysis & value plays\n"
        "• Bet logging and performance tracking\n"
        "• Line movement and value alerts"
    )


def tier_gate_footer(min_tier: Tier) -> str:
    if min_tier == Tier.SHARP:
        return f"SharpEdge Sharp — {WHOP_STOREFRONT_URL}"
    if min_tier == Tier.PRO:
        return f"SharpEdge Pro — {WHOP_STOREFRONT_URL}"
    return f"SharpEdge — {WHOP_STOREFRONT_URL}"
