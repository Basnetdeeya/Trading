"""Deterministic synthetic OHLCV — used as fallback so the system always runs."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.core.types import AssetClass

from .base import DataProvider


class SimulatedProvider(DataProvider):
    name = "simulated"
    supports = [
        AssetClass.CRYPTO,
        AssetClass.FOREX,
        AssetClass.EQUITY,
        AssetClass.PREDICTION,
    ]

    _INTERVAL_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3_600,
        "4h": 14_400,
        "1d": 86_400,
    }

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        lookback: int = 500,
    ) -> pd.DataFrame:
        seed = int(hashlib.md5(f"{symbol}{interval}".encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        step = self._INTERVAL_SECONDS.get(interval, 3_600)
        end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        index = [end - timedelta(seconds=step * (lookback - i - 1)) for i in range(lookback)]

        # geometric brownian motion with mild mean-reversion and regime drift
        drift = 0.0002
        vol = 0.01
        prices = [float(100 + (seed % 500))]
        regime = rng.normal(0, 0.0005, size=lookback)
        for i in range(1, lookback):
            shock = rng.normal(drift + regime[i], vol)
            next_price = prices[-1] * (1 + shock)
            prices.append(max(next_price, 0.01))

        close = np.array(prices)
        noise = rng.normal(0, vol / 2, size=lookback)
        high = close * (1 + np.abs(noise))
        low = close * (1 - np.abs(noise))
        open_ = np.concatenate([[close[0]], close[:-1]])
        volume = rng.integers(1_000, 20_000, size=lookback).astype(float)

        df = pd.DataFrame(
            {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
            index=pd.DatetimeIndex(index, name="timestamp"),
        )
        return df
