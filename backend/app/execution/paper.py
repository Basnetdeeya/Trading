"""Paper broker — fills at the signal price minus configurable slippage."""
from __future__ import annotations

import uuid

from app.core.types import Order, Side

from .base import Broker


class PaperBroker(Broker):
    name = "paper"

    def __init__(self, slippage_bps: float = 5.0, fee_bps: float = 2.0) -> None:
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps

    async def place(self, order: Order) -> Order:
        slip = order.price * self.slippage_bps / 10_000
        if order.side == Side.BUY:
            fill_price = order.price + slip
        else:
            fill_price = order.price - slip
        fee = fill_price * order.quantity * self.fee_bps / 10_000
        order.price = fill_price
        order.order_id = order.order_id or f"paper-{uuid.uuid4().hex[:12]}"
        order.status = "filled"
        # fees are absorbed by price adjustment in this simple model; record for telemetry
        order.__dict__["fee"] = round(fee, 6)
        return order
