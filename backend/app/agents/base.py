"""AI agent contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from app.core.types import Signal


class AgentBackend(ABC):
    """Returns a probabilistic trading recommendation given OHLCV + signals."""

    name: str = "base"

    @abstractmethod
    async def decide(
        self,
        symbol: str,
        asset_class: str,
        df: pd.DataFrame,
        signals: List[Signal],
    ) -> dict:
        """
        Must return a dict with the shape:

            {
                "side": "BUY" | "SELL" | "HOLD",
                "confidence": 0.0 - 1.0,
                "chosen_strategy": "<strategy name or ''>",
                "regime": "trending" | "ranging" | "volatile" | "unknown",
                "rationale": "<short string>"
            }
        """
