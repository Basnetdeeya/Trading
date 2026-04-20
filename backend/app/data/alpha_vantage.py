"""Alpha Vantage provider (requires free API key)."""
from __future__ import annotations

import httpx
import pandas as pd

from app.core.types import AssetClass

from .base import DataProvider


class AlphaVantageProvider(DataProvider):
    name = "alpha_vantage"
    supports = [AssetClass.EQUITY, AssetClass.FOREX]
    BASE = "https://www.alphavantage.co/query"

    _FN_INTRADAY = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "60min"}

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise RuntimeError("alpha vantage requires an API key")
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
        params = {"symbol": symbol, "apikey": self.api_key, "outputsize": "compact"}
        if interval in self._FN_INTRADAY:
            params["function"] = "TIME_SERIES_INTRADAY"
            params["interval"] = self._FN_INTRADAY[interval]
            key = f"Time Series ({self._FN_INTRADAY[interval]})"
        else:
            params["function"] = "TIME_SERIES_DAILY"
            key = "Time Series (Daily)"
        resp = await self._client.get(self.BASE, params=params)
        resp.raise_for_status()
        payload = resp.json()
        series = payload.get(key)
        if not series:
            raise ValueError(f"alpha_vantage: unexpected response for {symbol}: {payload}")
        df = pd.DataFrame(series).T.rename(
            columns={
                "1. open": "open",
                "2. high": "high",
                "3. low": "low",
                "4. close": "close",
                "5. volume": "volume",
            }
        )[["open", "high", "low", "close", "volume"]].astype(float)
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "timestamp"
        return df.sort_index().tail(lookback)
