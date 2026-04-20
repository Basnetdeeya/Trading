"""Live broker stub.

Intentionally **not** wired to a real exchange. This is a guardrail: users
must drop in their own exchange integration and flip `LIVE_TRADING_CONFIRMED`
to the required string. Until then, any live order request raises.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.types import Order

from .base import Broker

logger = get_logger(__name__)


class LiveBrokerStub(Broker):
    name = "live-stub"

    async def place(self, order: Order) -> Order:
        logger.error("LiveBrokerStub refused to place an order. Implement a real adapter.")
        raise RuntimeError(
            "Live trading is not configured. Implement a real broker adapter before "
            "setting TRADING_MODE=live."
        )
