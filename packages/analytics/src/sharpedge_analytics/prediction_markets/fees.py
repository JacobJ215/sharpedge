"""Fee structures and fee calculation for prediction market platforms."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Platform(Enum):
    """Supported prediction market platforms."""
    KALSHI = "kalshi"
    POLYMARKET = "polymarket"
    POLYMARKET_US = "polymarket_us"
    METACULUS = "metaculus"
    PREDICTIT = "predictit"


@dataclass
class PlatformFees:
    """Fee structure for a prediction market platform."""

    platform: Platform
    taker_fee_pct: float  # Percentage fee on trades
    maker_fee_pct: float  # Fee for providing liquidity
    settlement_fee_per_contract: float  # Fee per winning contract
    withdrawal_fee: float  # Fixed withdrawal fee

    # Platform-specific fee formulas
    fee_formula: Callable[[float, float], float] | None = None

    def calculate_trade_fee(self, price: float, contracts: int) -> float:
        """Calculate fee for a trade.

        Args:
            price: Contract price (0-1 probability)
            contracts: Number of contracts

        Returns:
            Total fee in dollars
        """
        if self.fee_formula:
            return self.fee_formula(price, contracts)

        # Default: simple percentage
        notional = price * contracts
        return notional * self.taker_fee_pct

    def calculate_settlement_fee(self, winning_contracts: int) -> float:
        """Calculate fee on winning contracts."""
        return winning_contracts * self.settlement_fee_per_contract


# Platform fee configurations
def _kalshi_fee_formula(price: float, contracts: int) -> float:
    """Kalshi's probability-weighted fee: 0.07 × contracts × price × (1-price)"""
    return 0.07 * contracts * price * (1 - price)


def _kalshi_reduced_fee_formula(price: float, contracts: int) -> float:
    """Kalshi's reduced fee for S&P/Nasdaq markets: 0.035 multiplier"""
    return 0.035 * contracts * price * (1 - price)


PLATFORM_FEES: dict[Platform, PlatformFees] = {
    Platform.KALSHI: PlatformFees(
        platform=Platform.KALSHI,
        taker_fee_pct=0.01,  # ~1% effective (varies with price)
        maker_fee_pct=0.0,
        settlement_fee_per_contract=0.01,
        withdrawal_fee=2.0,  # $2 wire fee
        fee_formula=_kalshi_fee_formula,
    ),
    Platform.POLYMARKET: PlatformFees(
        platform=Platform.POLYMARKET,
        taker_fee_pct=0.0,  # No trading fees on standard markets
        maker_fee_pct=0.0,
        settlement_fee_per_contract=0.0,  # No settlement fee
        withdrawal_fee=0.50,  # Approximate gas fee
    ),
    Platform.POLYMARKET_US: PlatformFees(
        platform=Platform.POLYMARKET_US,
        taker_fee_pct=0.001,  # 0.10% = 10 bps
        maker_fee_pct=0.0,
        settlement_fee_per_contract=0.0,
        withdrawal_fee=0.50,
    ),
    Platform.PREDICTIT: PlatformFees(
        platform=Platform.PREDICTIT,
        taker_fee_pct=0.05,  # 5% on trades
        maker_fee_pct=0.05,
        settlement_fee_per_contract=0.10,  # 10% on profits
        withdrawal_fee=0.0,
    ),
}


def probability_to_price(prob: float) -> float:
    """Convert probability to prediction market price."""
    return prob


def price_to_probability(price: float) -> float:
    """Convert prediction market price to probability."""
    return price


def calculate_fee_adjusted_price(
    price: float,
    contracts: int,
    platform: Platform,
    is_buy: bool = True,
) -> float:
    """Calculate effective price after platform fees.

    Args:
        price: Raw contract price (0-1)
        contracts: Number of contracts
        platform: Trading platform
        is_buy: True if buying, False if selling

    Returns:
        Fee-adjusted effective price
    """
    fees = PLATFORM_FEES.get(platform)
    if not fees:
        return price

    trade_fee = fees.calculate_trade_fee(price, contracts)
    fee_per_contract = trade_fee / contracts if contracts > 0 else 0

    if is_buy:
        # Buying: effective price is higher
        return price + fee_per_contract
    else:
        # Selling: effective price is lower
        return price - fee_per_contract
