"""Offline agent that picks a strategy based on regime + signal agreement.

This is ALWAYS available, with no external dependencies. It acts as a fallback
when no LLM key is configured, and as a safety net if an LLM call fails.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from app.core.types import Side, Signal

from .base import AgentBackend
from .features import MarketFeatures, compute_features


class HeuristicAgent(AgentBackend):
    name = "heuristic"

    _REGIME_PREFERENCES = {
        "trending": ["trend_following", "ma_crossover", "breakout", "momentum", "macd"],
        "ranging": ["mean_reversion", "grid", "bollinger_breakout", "vwap", "rsi"],
        "volatile": ["volume_spike", "atr", "bollinger_breakout", "breakout"],
        "unknown": ["rsi", "macd", "ma_crossover"],
    }

    async def decide(
        self,
        symbol: str,
        asset_class: str,
        df: pd.DataFrame,
        signals: List[Signal],
    ) -> dict:
        feats = compute_features(df, signals)
        preferred = self._REGIME_PREFERENCES.get(feats.regime, [])
        candidates = [s for s in signals if s.is_actionable()]
        candidates.sort(
            key=lambda s: (preferred.index(s.strategy) if s.strategy in preferred else 99, -s.confidence)
        )
        if not candidates:
            return self._response(Side.HOLD, 0.15, "", feats, "no actionable signals")

        chosen = candidates[0]
        # Require ensemble agreement for higher confidence
        same_side = [s for s in signals if s.side == chosen.side and s.confidence >= 0.4]
        ensemble_boost = min(len(same_side) / 6.0, 0.35)
        confidence = min(chosen.confidence * 0.7 + ensemble_boost + 0.1, 0.95)

        rationale = (
            f"regime={feats.regime} trend={feats.trend_strength:+.2%} vol={feats.volatility:.2%} "
            f"rsi={feats.rsi:.0f} | {len(same_side)} strategies agree on {chosen.side.value}"
        )
        return self._response(chosen.side, confidence, chosen.strategy, feats, rationale)

    @staticmethod
    def _response(side: Side, confidence: float, strategy: str, feats: MarketFeatures, rationale: str) -> dict:
        return {
            "side": side.value,
            "confidence": round(confidence, 3),
            "chosen_strategy": strategy,
            "regime": feats.regime,
            "rationale": rationale,
            "features": {
                "trend_strength": round(feats.trend_strength, 4),
                "volatility": round(feats.volatility, 4),
                "rsi": round(feats.rsi, 2),
                "momentum_1d": round(feats.momentum_1d, 4),
                "agreeing_bullish": feats.agreeing_bullish,
                "agreeing_bearish": feats.agreeing_bearish,
            },
        }
