"""Async event bus for trading pipeline coordination."""
import asyncio
from .types import (
    OpportunityEvent,
    ResearchEvent,
    PredictionEvent,
    ApprovedEvent,
    ExecutionEvent,
    ResolutionEvent,
)


class EventBus:
    """Typed asyncio.Queue channels for the trading pipeline.

    Each channel supports a single producer and a single consumer.
    Concurrent calls to the same get_* method are not supported —
    only one coroutine should read from each channel at a time.
    """

    def __init__(self, maxsize: int = 0):
        """Initialize event bus with async queues.

        Args:
            maxsize: Maximum queue size per channel. 0 = unlimited.
        """
        self._opportunity: asyncio.Queue[OpportunityEvent] = asyncio.Queue(maxsize)
        self._research: asyncio.Queue[ResearchEvent] = asyncio.Queue(maxsize)
        self._prediction: asyncio.Queue[PredictionEvent] = asyncio.Queue(maxsize)
        self._approved: asyncio.Queue[ApprovedEvent] = asyncio.Queue(maxsize)
        self._execution: asyncio.Queue[ExecutionEvent] = asyncio.Queue(maxsize)
        self._resolution: asyncio.Queue[ResolutionEvent] = asyncio.Queue(maxsize)

    async def put_opportunity(self, e: OpportunityEvent) -> None:
        """Put opportunity event on bus."""
        await self._opportunity.put(e)

    async def get_opportunity(self) -> OpportunityEvent:
        """Get next opportunity event from bus."""
        return await self._opportunity.get()

    async def put_research(self, e: ResearchEvent) -> None:
        """Put research event on bus."""
        await self._research.put(e)

    async def get_research(self) -> ResearchEvent:
        """Get next research event from bus."""
        return await self._research.get()

    async def put_prediction(self, e: PredictionEvent) -> None:
        """Put prediction event on bus."""
        await self._prediction.put(e)

    async def get_prediction(self) -> PredictionEvent:
        """Get next prediction event from bus."""
        return await self._prediction.get()

    async def put_approved(self, e: ApprovedEvent) -> None:
        """Put approved event on bus."""
        await self._approved.put(e)

    async def get_approved(self) -> ApprovedEvent:
        """Get next approved event from bus."""
        return await self._approved.get()

    async def put_execution(self, e: ExecutionEvent) -> None:
        """Put execution event on bus."""
        await self._execution.put(e)

    async def get_execution(self) -> ExecutionEvent:
        """Get next execution event from bus."""
        return await self._execution.get()

    async def put_resolution(self, e: ResolutionEvent) -> None:
        """Put resolution event on bus."""
        await self._resolution.put(e)

    async def get_resolution(self) -> ResolutionEvent:
        """Get next resolution event from bus."""
        return await self._resolution.get()
