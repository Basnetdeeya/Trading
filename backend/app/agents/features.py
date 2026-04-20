"""Market regime and feature extraction — shared by all agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from app.core.types import Signal
from app.strategies.indicators import atr, rsi


@dataclass
class MarketFeatures:
    regime: str
    trend_strength: float
    volatility: float
    rsi: float
    momentum_1d: float
    agreeing_bullish: int
    agreeing_bearish: int
    top_strategy: str
    top_confidence: float


def compute_features(df: pd.DataFrame, signals: List[Signal]) -> MarketFeatures:
    close = df["close"]
    ret = close.pct_change().dropna()
    vol = float(ret.tail(50).std() or 0.0)
    trend = float((close.iloc[-1] - close.iloc[-50]) / close.iloc[-50]) if len(close) > 50 else 0.0
    r = float(rsi(close).iloc[-1] or 50)
    a = float((atr(df).iloc[-1] or 0.0) / max(close.iloc[-1], 1e-9))

    if a > 0.03:
        regime = "volatile"
    elif abs(trend) > 0.03:
        regime = "trending"
    elif vol < 0.005:
        regime = "ranging"
    else:
        regime = "unknown"

    bullish = sum(1 for s in signals if s.side.value == "BUY" and s.confidence >= 0.5)
    bearish = sum(1 for s in signals if s.side.value == "SELL" and s.confidence >= 0.5)
    actionable = [s for s in signals if s.is_actionable()]
    actionable.sort(key=lambda s: s.confidence, reverse=True)
    top = actionable[0] if actionable else None

    mom_1d = float(close.pct_change(24).iloc[-1] or 0.0) if len(close) > 24 else 0.0

    return MarketFeatures(
        regime=regime,
        trend_strength=trend,
        volatility=vol,
        rsi=r,
        momentum_1d=mom_1d,
        agreeing_bullish=bullish,
        agreeing_bearish=bearish,
        top_strategy=top.strategy if top else "",
        top_confidence=top.confidence if top else 0.0,
    )
