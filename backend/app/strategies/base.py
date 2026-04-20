"""Strategy base class and helpers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd

from app.core.types import Side, Signal


@dataclass
class StrategyConfig:
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    params: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Contract: generate a Signal from OHLCV. Pure function of the dataframe."""

    name: str = "base"
    description: str = ""

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        self.config = config or StrategyConfig()

    # ------------------------------------------------------------------ API
    def generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        if df is None or df.empty or len(df) < self.min_bars():
            return Signal(
                symbol=symbol,
                side=Side.HOLD,
                confidence=0.0,
                price=float(df["close"].iloc[-1]) if df is not None and not df.empty else 0.0,
                strategy=self.name,
                rationale="insufficient data",
            )
        return self._generate(df, symbol)

    @abstractmethod
    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal: ...

    def min_bars(self) -> int:
        return 60

    # --------------------------------------------------------------- helpers
    def _levels(self, side: Side, price: float) -> tuple[Optional[float], Optional[float]]:
        if side == Side.HOLD:
            return None, None
        sl_pct = self.config.stop_loss_pct
        tp_pct = self.config.take_profit_pct
        if side == Side.BUY:
            return price * (1 - sl_pct), price * (1 + tp_pct)
        return price * (1 + sl_pct), price * (1 - tp_pct)

    def _signal(
        self,
        symbol: str,
        side: Side,
        confidence: float,
        price: float,
        rationale: str,
    ) -> Signal:
        sl, tp = self._levels(side, price)
        return Signal(
            symbol=symbol,
            side=side,
            confidence=max(0.0, min(1.0, confidence)),
            price=price,
            stop_loss=sl,
            take_profit=tp,
            strategy=self.name,
            rationale=rationale,
        )
