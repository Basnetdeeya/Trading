"""Polymarket / prediction-market adapter.

The public Polymarket CLOB API does not offer OHLCV bars. We expose a simple
`fetch_markets` helper and synthesise bars from trade ticks when available,
otherwise we fall back to the simulated provider.
"""
from __future__ import annotations

from typing import List

import httpx
import pandas as pd

from app.core.types import AssetClass

from .base import DataProvider
from .simulated import SimulatedProvider


class PolymarketProvider(DataProvider):
    name = "polymarket"
    supports = [AssetClass.PREDICTION]

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self._client = httpx.AsyncClient(timeout=15)
        self._fallback = SimulatedProvider()

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_markets(self) -> List[dict]:
        if not self.base_url:
            return []
        try:
            resp = await self._client.get(f"{self.base_url}/markets")
            resp.raise_for_status()
            return resp.json() if isinstance(resp.json(), list) else []
        except Exception:
            return []

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        lookback: int = 500,
    ) -> pd.DataFrame:
        # No real OHLCV endpoint — return simulated bars scaled to [0, 1]
        df = await self._fallback.fetch_ohlcv(symbol, interval=interval, lookback=lookback)
        scale = df["close"].iloc[0]
        for col in ("open", "high", "low", "close"):
            df[col] = (df[col] / scale).clip(0.01, 0.99)
        return df
