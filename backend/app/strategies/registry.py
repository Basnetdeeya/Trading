"""Registry that instantiates all strategies from configuration."""
from __future__ import annotations

from typing import Dict, List

from app.core.config import Settings, get_settings

from .base import BaseStrategy, StrategyConfig
from .implementations import (
    ArbitrageStrategy,
    BollingerBreakoutStrategy,
    BreakoutStrategy,
    FibonacciStrategy,
    GridStrategy,
    MACDStrategy,
    MACrossoverStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    NewsSentimentStrategy,
    RSIStrategy,
    SupportResistanceStrategy,
    TrendFollowingStrategy,
    VolumeSpikeStrategy,
    VWAPStrategy,
)

ALL_CLASSES: List[type[BaseStrategy]] = [
    MACrossoverStrategy,
    RSIStrategy,
    MACDStrategy,
    BollingerBreakoutStrategy,
    SupportResistanceStrategy,
    FibonacciStrategy,
    VolumeSpikeStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    MomentumStrategy,
    VWAPStrategy,
    GridStrategy,
    ArbitrageStrategy,
    NewsSentimentStrategy,
]


def all_strategies(settings: Settings | None = None) -> List[BaseStrategy]:
    s = settings or get_settings()
    cfg = StrategyConfig(
        stop_loss_pct=s.default_stop_loss_pct,
        take_profit_pct=s.default_take_profit_pct,
    )
    return [cls(config=cfg) for cls in ALL_CLASSES]


class StrategyRegistry:
    """Holds enabled strategies keyed by name."""

    def __init__(self, strategies: List[BaseStrategy] | None = None) -> None:
        self._strategies: Dict[str, BaseStrategy] = {
            s.name: s for s in (strategies or all_strategies())
        }
        self._enabled: Dict[str, bool] = {name: True for name in self._strategies}

    def names(self) -> List[str]:
        return list(self._strategies)

    def enabled(self) -> List[BaseStrategy]:
        return [s for name, s in self._strategies.items() if self._enabled.get(name, True)]

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name in self._strategies:
            self._enabled[name] = enabled

    def get(self, name: str) -> BaseStrategy | None:
        return self._strategies.get(name)

    def describe(self) -> List[dict]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "enabled": self._enabled.get(s.name, True),
            }
            for s in self._strategies.values()
        ]
