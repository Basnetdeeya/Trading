"""Data provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from app.core.types import AssetClass


class DataProvider(ABC):
    """Abstract OHLCV data source."""

    name: str = "base"
    supports: List[AssetClass] = []

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        lookback: int = 500,
    ) -> pd.DataFrame:
        """Return a DataFrame with columns: open, high, low, close, volume,
        indexed by UTC timestamp, oldest first."""

    async def close(self) -> None:
        return None
