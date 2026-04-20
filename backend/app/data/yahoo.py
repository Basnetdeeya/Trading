"""Yahoo Finance fallback using yfinance."""
from __future__ import annotations

import asyncio

import pandas as pd

from app.core.types import AssetClass

from .base import DataProvider


class YahooProvider(DataProvider):
    name = "yahoo"
    supports = [AssetClass.EQUITY, AssetClass.FOREX, AssetClass.CRYPTO]

    _INTERVAL = {
        "1m": ("1m", "7d"),
        "5m": ("5m", "60d"),
        "15m": ("15m", "60d"),
        "1h": ("60m", "730d"),
        "1d": ("1d", "max"),
    }

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        lookback: int = 500,
    ) -> pd.DataFrame:
        yf_interval, period = self._INTERVAL.get(interval, ("60m", "730d"))

        def _download() -> pd.DataFrame:
            import yfinance as yf  # lazy import: optional dependency
            df = yf.download(
                symbol,
                period=period,
                interval=yf_interval,
                progress=False,
                auto_adjust=False,
            )
            if df is None or df.empty:
                raise ValueError(f"yahoo: empty response for {symbol}")
            df = df.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )[["open", "high", "low", "close", "volume"]]
            df.index = pd.to_datetime(df.index, utc=True)
            df.index.name = "timestamp"
            return df.tail(lookback)

        return await asyncio.to_thread(_download)
