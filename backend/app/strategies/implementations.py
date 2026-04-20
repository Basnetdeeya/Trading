"""Concrete strategy implementations (15)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.types import Side, Signal

from .base import BaseStrategy
from .indicators import atr, bollinger, ema, macd, rsi, sma, vwap, zscore


# 1. Moving Average Crossover ------------------------------------------------
class MACrossoverStrategy(BaseStrategy):
    name = "ma_crossover"
    description = "Fast/slow SMA crossover trend follower."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        fast_n = self.config.params.get("fast", 20)
        slow_n = self.config.params.get("slow", 50)
        fast = sma(df["close"], fast_n)
        slow = sma(df["close"], slow_n)
        price = float(df["close"].iloc[-1])
        if pd.isna(fast.iloc[-1]) or pd.isna(slow.iloc[-1]):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        spread = (fast.iloc[-1] - slow.iloc[-1]) / slow.iloc[-1]
        prev_spread = (fast.iloc[-2] - slow.iloc[-2]) / slow.iloc[-2]
        if spread > 0 and prev_spread <= 0:
            return self._signal(symbol, Side.BUY, min(abs(spread) * 50, 0.9), price, "fast crossed above slow")
        if spread < 0 and prev_spread >= 0:
            return self._signal(symbol, Side.SELL, min(abs(spread) * 50, 0.9), price, "fast crossed below slow")
        return self._signal(symbol, Side.HOLD, 0.2, price, "no crossover")


# 2. RSI ---------------------------------------------------------------------
class RSIStrategy(BaseStrategy):
    name = "rsi"
    description = "Oversold buys, overbought sells."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        n = self.config.params.get("period", 14)
        lo = self.config.params.get("oversold", 30)
        hi = self.config.params.get("overbought", 70)
        r = rsi(df["close"], n).iloc[-1]
        price = float(df["close"].iloc[-1])
        if np.isnan(r):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if r < lo:
            return self._signal(symbol, Side.BUY, min((lo - r) / lo + 0.5, 0.95), price, f"RSI {r:.1f} oversold")
        if r > hi:
            return self._signal(symbol, Side.SELL, min((r - hi) / (100 - hi) + 0.5, 0.95), price, f"RSI {r:.1f} overbought")
        return self._signal(symbol, Side.HOLD, 0.1, price, f"RSI {r:.1f} neutral")


# 3. MACD --------------------------------------------------------------------
class MACDStrategy(BaseStrategy):
    name = "macd"
    description = "MACD line / signal crossover."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        line, sig, hist = macd(df["close"])
        price = float(df["close"].iloc[-1])
        if pd.isna(hist.iloc[-1]) or pd.isna(hist.iloc[-2]):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
            return self._signal(symbol, Side.BUY, 0.7, price, "MACD turned positive")
        if hist.iloc[-1] < 0 and hist.iloc[-2] >= 0:
            return self._signal(symbol, Side.SELL, 0.7, price, "MACD turned negative")
        return self._signal(symbol, Side.HOLD, 0.15, price, "no MACD cross")


# 4. Bollinger Bands ---------------------------------------------------------
class BollingerBreakoutStrategy(BaseStrategy):
    name = "bollinger_breakout"
    description = "Trade breakouts through Bollinger Bands."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        lower, mid, upper = bollinger(df["close"], 20, 2.0)
        price = float(df["close"].iloc[-1])
        if pd.isna(upper.iloc[-1]):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if price > upper.iloc[-1]:
            return self._signal(symbol, Side.BUY, 0.65, price, "breakout above upper band")
        if price < lower.iloc[-1]:
            return self._signal(symbol, Side.SELL, 0.65, price, "breakdown below lower band")
        return self._signal(symbol, Side.HOLD, 0.1, price, "inside bands")


# 5. Support / Resistance ----------------------------------------------------
class SupportResistanceStrategy(BaseStrategy):
    name = "support_resistance"
    description = "Pivot-based S/R reversion."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        n = 50
        window = df.tail(n)
        support = window["low"].min()
        resistance = window["high"].max()
        price = float(df["close"].iloc[-1])
        rng = resistance - support
        if rng <= 0:
            return self._signal(symbol, Side.HOLD, 0.0, price, "flat range")
        if price <= support + 0.05 * rng:
            return self._signal(symbol, Side.BUY, 0.6, price, f"near support {support:.2f}")
        if price >= resistance - 0.05 * rng:
            return self._signal(symbol, Side.SELL, 0.6, price, f"near resistance {resistance:.2f}")
        return self._signal(symbol, Side.HOLD, 0.1, price, "mid-range")


# 6. Fibonacci retracement ---------------------------------------------------
class FibonacciStrategy(BaseStrategy):
    name = "fibonacci"
    description = "Buy 0.618 / sell 0.382 retracement in uptrend."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        window = df.tail(100)
        swing_high = window["high"].max()
        swing_low = window["low"].min()
        price = float(df["close"].iloc[-1])
        rng = swing_high - swing_low
        if rng <= 0:
            return self._signal(symbol, Side.HOLD, 0.0, price, "no swing")
        fib_382 = swing_high - 0.382 * rng
        fib_618 = swing_high - 0.618 * rng
        if abs(price - fib_618) / price < 0.005:
            return self._signal(symbol, Side.BUY, 0.6, price, "at 0.618 retracement")
        if abs(price - fib_382) / price < 0.005:
            return self._signal(symbol, Side.SELL, 0.55, price, "at 0.382 retracement")
        return self._signal(symbol, Side.HOLD, 0.1, price, "no fib touch")


# 7. Volume spike ------------------------------------------------------------
class VolumeSpikeStrategy(BaseStrategy):
    name = "volume_spike"
    description = "Follow price direction on abnormal volume."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        price = float(df["close"].iloc[-1])
        vol = df["volume"]
        if vol.sum() == 0:
            return self._signal(symbol, Side.HOLD, 0.0, price, "no volume data")
        vol_z = zscore(vol, 20).iloc[-1]
        ret = df["close"].pct_change().iloc[-1]
        if pd.isna(vol_z):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if vol_z > 2.0 and ret > 0:
            return self._signal(symbol, Side.BUY, min(vol_z / 5, 0.9), price, f"volume spike z={vol_z:.1f} up")
        if vol_z > 2.0 and ret < 0:
            return self._signal(symbol, Side.SELL, min(vol_z / 5, 0.9), price, f"volume spike z={vol_z:.1f} down")
        return self._signal(symbol, Side.HOLD, 0.1, price, "normal volume")


# 8. Trend following ---------------------------------------------------------
class TrendFollowingStrategy(BaseStrategy):
    name = "trend_following"
    description = "EMA-stack trend follower with ATR stops."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        e20, e50, e200 = ema(df["close"], 20), ema(df["close"], 50), ema(df["close"], 200)
        price = float(df["close"].iloc[-1])
        a = atr(df).iloc[-1]
        if pd.isna(e200.iloc[-1]) or pd.isna(a):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if e20.iloc[-1] > e50.iloc[-1] > e200.iloc[-1]:
            sl = price - 2 * a
            tp = price + 4 * a
            s = self._signal(symbol, Side.BUY, 0.75, price, "EMA 20>50>200 uptrend")
            s.stop_loss, s.take_profit = sl, tp
            return s
        if e20.iloc[-1] < e50.iloc[-1] < e200.iloc[-1]:
            sl = price + 2 * a
            tp = price - 4 * a
            s = self._signal(symbol, Side.SELL, 0.75, price, "EMA 20<50<200 downtrend")
            s.stop_loss, s.take_profit = sl, tp
            return s
        return self._signal(symbol, Side.HOLD, 0.2, price, "no trend alignment")


# 9. Mean reversion ----------------------------------------------------------
class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion"
    description = "Fade extreme z-score of returns."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        z = zscore(df["close"], 20).iloc[-1]
        price = float(df["close"].iloc[-1])
        if pd.isna(z):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if z < -2.0:
            return self._signal(symbol, Side.BUY, min(abs(z) / 4, 0.9), price, f"z={z:.2f} stretched down")
        if z > 2.0:
            return self._signal(symbol, Side.SELL, min(abs(z) / 4, 0.9), price, f"z={z:.2f} stretched up")
        return self._signal(symbol, Side.HOLD, 0.15, price, f"z={z:.2f}")


# 10. Breakout trading -------------------------------------------------------
class BreakoutStrategy(BaseStrategy):
    name = "breakout"
    description = "Donchian 20-bar channel breakout."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        hi = df["high"].rolling(20).max().iloc[-2]
        lo = df["low"].rolling(20).min().iloc[-2]
        price = float(df["close"].iloc[-1])
        if pd.isna(hi) or pd.isna(lo):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        if price > hi:
            return self._signal(symbol, Side.BUY, 0.7, price, f"breakout > {hi:.2f}")
        if price < lo:
            return self._signal(symbol, Side.SELL, 0.7, price, f"breakdown < {lo:.2f}")
        return self._signal(symbol, Side.HOLD, 0.15, price, "inside channel")


# 11. Momentum ---------------------------------------------------------------
class MomentumStrategy(BaseStrategy):
    name = "momentum"
    description = "N-period rate of change."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        n = self.config.params.get("period", 10)
        roc = df["close"].pct_change(n).iloc[-1]
        price = float(df["close"].iloc[-1])
        if pd.isna(roc):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        threshold = self.config.params.get("threshold", 0.03)
        if roc > threshold:
            return self._signal(symbol, Side.BUY, min(roc * 10, 0.9), price, f"ROC {roc:.2%}")
        if roc < -threshold:
            return self._signal(symbol, Side.SELL, min(abs(roc) * 10, 0.9), price, f"ROC {roc:.2%}")
        return self._signal(symbol, Side.HOLD, 0.15, price, f"ROC {roc:.2%}")


# 12. VWAP -------------------------------------------------------------------
class VWAPStrategy(BaseStrategy):
    name = "vwap"
    description = "Revert to the volume-weighted average price."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        v = vwap(df).iloc[-1]
        price = float(df["close"].iloc[-1])
        if pd.isna(v) or v == 0:
            return self._signal(symbol, Side.HOLD, 0.0, price, "no VWAP")
        diff = (price - v) / v
        if diff < -0.01:
            return self._signal(symbol, Side.BUY, min(abs(diff) * 30, 0.85), price, f"price {diff:.2%} below VWAP")
        if diff > 0.01:
            return self._signal(symbol, Side.SELL, min(abs(diff) * 30, 0.85), price, f"price {diff:.2%} above VWAP")
        return self._signal(symbol, Side.HOLD, 0.1, price, "at VWAP")


# 13. Grid trading -----------------------------------------------------------
class GridStrategy(BaseStrategy):
    name = "grid"
    description = "Fixed-band mean reversion for ranging markets."

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        window = df.tail(100)
        center = window["close"].mean()
        std = window["close"].std()
        price = float(df["close"].iloc[-1])
        if std == 0 or pd.isna(std):
            return self._signal(symbol, Side.HOLD, 0.0, price, "flat range")
        deviation = (price - center) / std
        if deviation < -1.0:
            return self._signal(symbol, Side.BUY, min(abs(deviation) / 3, 0.8), price, f"grid buy dev={deviation:.2f}")
        if deviation > 1.0:
            return self._signal(symbol, Side.SELL, min(abs(deviation) / 3, 0.8), price, f"grid sell dev={deviation:.2f}")
        return self._signal(symbol, Side.HOLD, 0.2, price, "inside grid")


# 14. Arbitrage detection (single-exchange pair spread heuristic) ------------
class ArbitrageStrategy(BaseStrategy):
    name = "arbitrage"
    description = (
        "Detects short-term spread between fast and slow EMAs as a proxy for "
        "cross-market dislocations; real cross-exchange arb requires multi-feed setup."
    )

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        fast = ema(df["close"], 3)
        slow = ema(df["close"], 20)
        price = float(df["close"].iloc[-1])
        if pd.isna(slow.iloc[-1]):
            return self._signal(symbol, Side.HOLD, 0.0, price, "warming up")
        spread = (fast.iloc[-1] - slow.iloc[-1]) / slow.iloc[-1]
        if abs(spread) < 0.002:
            return self._signal(symbol, Side.HOLD, 0.05, price, "spread tight")
        # Expect the spread to revert
        side = Side.SELL if spread > 0 else Side.BUY
        return self._signal(symbol, Side.HOLD, 0.3, price, f"spread {spread:.2%} — live arb disabled") if not self.config.params.get("enabled") else self._signal(
            symbol, side, min(abs(spread) * 50, 0.7), price, f"spread {spread:.2%} reversion"
        )


# 15. News sentiment (optional AI hook) --------------------------------------
class NewsSentimentStrategy(BaseStrategy):
    name = "news_sentiment"
    description = (
        "Consumes an external sentiment score (0..1) from config.params['sentiment']. "
        "If the AI agent is configured, the orchestrator fills this in; otherwise HOLD."
    )

    def _generate(self, df: pd.DataFrame, symbol: str) -> Signal:
        price = float(df["close"].iloc[-1])
        sentiment = self.config.params.get("sentiment")
        if sentiment is None:
            return self._signal(symbol, Side.HOLD, 0.0, price, "no sentiment input")
        if sentiment > 0.65:
            return self._signal(symbol, Side.BUY, (sentiment - 0.5) * 2, price, f"bullish sentiment {sentiment:.2f}")
        if sentiment < 0.35:
            return self._signal(symbol, Side.SELL, (0.5 - sentiment) * 2, price, f"bearish sentiment {sentiment:.2f}")
        return self._signal(symbol, Side.HOLD, 0.1, price, f"neutral sentiment {sentiment:.2f}")
