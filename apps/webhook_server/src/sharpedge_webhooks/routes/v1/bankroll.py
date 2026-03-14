"""POST /api/v1/bankroll/simulate — Monte Carlo bankroll simulation (public)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["v1"])


def simulate_bankroll(
    bankroll: float,
    bet_size: float,
    num_bets: int,
    win_rate: float,
    num_paths: int = 2000,
) -> dict:
    """Lazy wrapper around Phase 1 monte_carlo simulate_bankroll."""
    from sharpedge_bot.monte_carlo import simulate_bankroll as _fn
    return _fn(
        bankroll=bankroll,
        bet_size=bet_size,
        num_bets=num_bets,
        win_rate=win_rate,
        num_paths=num_paths,
    )


class BankrollSimulateRequest(BaseModel):
    bankroll: float = Field(gt=0, description="Starting bankroll in dollars")
    bet_size: float = Field(gt=0, description="Fixed bet size in dollars")
    num_bets: int = Field(gt=0, le=10000, description="Number of bets to simulate")
    win_rate: float = Field(gt=0, lt=1, description="Win probability (0-1)")
    num_paths: int = Field(default=2000, ge=100, le=5000)


@router.post("/bankroll/simulate")
async def bankroll_simulate(request: BankrollSimulateRequest) -> dict:
    """Run Monte Carlo bankroll simulation. Public endpoint — no auth required."""
    result = simulate_bankroll(
        bankroll=request.bankroll,
        bet_size=request.bet_size,
        num_bets=request.num_bets,
        win_rate=request.win_rate,
        num_paths=request.num_paths,
    )
    # simulate_bankroll returns dict from Phase 1 — normalize field names
    return {
        "ruin_probability": float(result.get("ruin_probability", 0.0)),
        "p5_outcome": float(result.get("p5_outcome", 0.0)),
        "p50_outcome": float(result.get("p50_outcome", 0.0)),
        "p95_outcome": float(result.get("p95_outcome", 0.0)),
        "max_drawdown": float(result.get("max_drawdown", 0.0)),
        "paths_simulated": request.num_paths,
    }
