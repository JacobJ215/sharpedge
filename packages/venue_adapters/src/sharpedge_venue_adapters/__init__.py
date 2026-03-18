"""sharpedge_venue_adapters — canonical multi-venue adapter layer."""

from sharpedge_venue_adapters.exposure import (
    AllocationDecision,
    ExposureBook,
    apply_drawdown_throttle,
    compute_allocation,
)
from sharpedge_venue_adapters.ledger import (
    LedgerEntry,
    LedgerEventType,
    SettlementLedger,
    replay_position_pnl,
)
from sharpedge_venue_adapters.snapshot_store import (
    SnapshotRecord,
    SnapshotStore,
)
from sharpedge_venue_adapters.execution_engine import (
    DayExposureGuard,
    MarketExposureGuard,
    OrderIntent,
    ShadowExecutionEngine,
    ShadowLedger,
    ShadowLedgerEntry,
)

__all__ = [
    # exposure
    "AllocationDecision",
    "ExposureBook",
    "apply_drawdown_throttle",
    "compute_allocation",
    # ledger
    "LedgerEntry",
    "LedgerEventType",
    "SettlementLedger",
    "replay_position_pnl",
    # snapshot store
    "SnapshotRecord",
    "SnapshotStore",
    # execution engine
    "DayExposureGuard",
    "MarketExposureGuard",
    "OrderIntent",
    "ShadowExecutionEngine",
    "ShadowLedger",
    "ShadowLedgerEntry",
]
