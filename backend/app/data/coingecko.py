"""CoinGecko provider (public API, no key required for basic quotas)."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pandas as pd

from app.core.logging import get_logger
from app.core.types import AssetClass

from .base import DataProvider

logger = get_logger(__name__)


class CoinGeckoProvider(DataProvider):
    name = "coingecko"
    supports = [AssetClass.CRYPTO]
    BASE = "https://api.coingecko.com/api/v3"

    _INTERVAL_DAYS = {
        "5m": 1,
        "15m": 1,
        "1h": 7,
        "4h": 30,
        "1d": 90,
    }

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=15)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        lookback: int = 500,
    ) -> pd.DataFrame:
        coin_id = symbol.lower().replace("usdt", "").replace("usd", "").strip("-/") or symbol.lower()
        days = self._INTERVAL_DAYS.get(interval, 7)
        url = f"{self.BASE}/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": days}
        headers = {"x-cg-demo-api-key": self.api_key} if self.api_key else {}
        resp = await self._client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            raise ValueError(f"coingecko: empty response for {symbol}")
        df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df = df.drop(columns=["ts"]).set_index("timestamp").tail(lookback)
        df["volume"] = 0.0  # ohlc endpoint does not include volume
        return df[["open", "high", "low", "close", "volume"]]
