"""Shared domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    EQUITY = "equity"
    PREDICTION = "prediction"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    """A strategy's trading recommendation for a single symbol."""

    symbol: str
    side: Side
    confidence: float  # 0.0 - 1.0
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = ""
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def is_actionable(self) -> bool:
        return self.side in (Side.BUY, Side.SELL) and self.confidence > 0.0


@dataclass
class Order:
    symbol: str
    side: Side
    quantity: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = ""
    order_id: Optional[str] = None
    status: str = "new"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: datetime = field(default_factory=datetime.utcnow)
    strategy: str = ""

    def market_value(self, last_price: float) -> float:
        return self.quantity * last_price

    def unrealized_pnl(self, last_price: float) -> float:
        return (last_price - self.avg_price) * self.quantity


@dataclass
class Trade:
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    exit_price: float
    pnl: float
    opened_at: datetime
    closed_at: datetime
    strategy: str = ""
