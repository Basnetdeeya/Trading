"""Routes a (symbol, asset_class) request to the best available provider."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.types import AssetClass

from .alpha_vantage import AlphaVantageProvider
from .base import DataProvider
from .coingecko import CoinGeckoProvider
from .polymarket import PolymarketProvider
from .simulated import SimulatedProvider
from .yahoo import YahooProvider

logger = get_logger(__name__)


class DataRouter:
    """Tries providers in priority order per asset class, falling back to
    the simulated provider so the system always has data to analyse."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.settings = s
        self._sim = SimulatedProvider()
        self._providers: Dict[AssetClass, List[DataProvider]] = {
            AssetClass.CRYPTO: [CoinGeckoProvider(s.coingecko_api_key)],
            AssetClass.EQUITY: [],
            AssetClass.FOREX: [],
            AssetClass.PREDICTION: [PolymarketProvider(s.polymarket_api_url)],
        }
        if s.alpha_vantage_api_key:
            av = AlphaVantageProvider(s.alpha_vantage_api_key)
            self._providers[AssetClass.EQUITY].append(av)
            self._providers[AssetClass.FOREX].append(av)
        if s.yahoo_finance_enabled:
            yahoo = YahooProvider()
            self._providers[AssetClass.EQUITY].append(yahoo)
            self._providers[AssetClass.FOREX].append(yahoo)
            self._providers[AssetClass.CRYPTO].append(yahoo)

    async def fetch_ohlcv(
        self,
        symbol: str,
        asset_class: AssetClass,
        interval: str = "1h",
        lookback: int = 500,
    ) -> pd.DataFrame:
        for provider in self._providers.get(asset_class, []):
            try:
                df = await provider.fetch_ohlcv(symbol, interval=interval, lookback=lookback)
                if df is not None and not df.empty:
                    return df
            except Exception as exc:  # noqa: BLE001
                logger.warning("provider %s failed for %s: %s", provider.name, symbol, exc)
        logger.info("falling back to simulated data for %s (%s)", symbol, asset_class.value)
        return await self._sim.fetch_ohlcv(symbol, interval=interval, lookback=lookback)

    async def close(self) -> None:
        for providers in self._providers.values():
            for p in providers:
                await p.close()
