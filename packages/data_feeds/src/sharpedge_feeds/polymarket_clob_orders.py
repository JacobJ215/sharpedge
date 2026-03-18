"""Polymarket CLOB order placement stub.

Live EIP-712 signing deferred to v3 (POLY-EXEC-01). Set
ENABLE_POLY_EXECUTION=true to attempt live mode (raises NotImplementedError).
"""

import logging
import os

logger = logging.getLogger(__name__)


class PolymarketCLOBOrderClient:
    """Order placement stub for Polymarket CLOB.

    Shadow mode (default): logs intent, returns shadow order ID.
    Live mode (ENABLE_POLY_EXECUTION=true): raises NotImplementedError.
    """

    def __init__(self) -> None:
        self.enabled: bool = (
            os.getenv("ENABLE_POLY_EXECUTION", "false").lower() == "true"
        )

    async def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        contracts: int,
    ) -> dict:
        """Place a limit order on Polymarket CLOB.

        Args:
            token_id:  ERC-1155 outcome token ID.
            side:      "YES" or "NO" (case-insensitive).
            price:     Limit price in [0, 1].
            contracts: Number of contracts to buy.

        Returns:
            Dict with at minimum an "order_id" key.

        Raises:
            NotImplementedError: In live mode — deferred to POLY-EXEC-01 (v3).
        """
        if not self.enabled:
            logger.info(
                "SHADOW Polymarket order: side=%s token=%s price=%s contracts=%s",
                side, token_id, price, contracts,
            )
            return {
                "order_id": f"SHADOW-POLY-{token_id[:8]}-{side}",
                "status": "shadow",
                "enabled": False,
            }

        raise NotImplementedError(
            "Live Polymarket EIP-712 signing not implemented"
            " — deferred to v3 (POLY-EXEC-01)"
        )
