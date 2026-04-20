"""Bar-by-bar backtesting engine for a single strategy on a single symbol."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd

from app.core.types import Side
from app.strategies.base import BaseStrategy

from .metrics import Metrics, compute_metrics


@dataclass
class BacktestResult:
    strategy: str
    symbol: str
    equity_curve: List[float]
    metrics: Metrics
    trades: List[dict] = field(default_factory=list)


class BacktestEngine:
    """Simple long-only backtester with stop-loss/take-profit exits."""

    def __init__(
        self,
        starting_capital: float = 10_000.0,
        fee_bps: float = 5.0,
        position_pct: float = 0.1,
    ) -> None:
        self.starting_capital = starting_capital
        self.fee_bps = fee_bps
        self.position_pct = position_pct

    def run(self, strategy: BaseStrategy, df: pd.DataFrame, symbol: str) -> BacktestResult:
        cash = self.starting_capital
        position_qty = 0.0
        entry_price = 0.0
        stop = take = None
        equity_curve: List[float] = []
        trades: List[dict] = []
        pnls: List[float] = []

        window = strategy.min_bars()
        for i in range(window, len(df)):
            slice_df = df.iloc[: i + 1]
            price = float(slice_df["close"].iloc[-1])

            if position_qty > 0:
                if (stop and price <= stop) or (take and price >= take):
                    proceeds = position_qty * price
                    fees = proceeds * self.fee_bps / 10_000
                    cash += proceeds - fees
                    pnl = (price - entry_price) * position_qty - fees
                    pnls.append(pnl)
                    trades.append({
                        "entry": entry_price, "exit": price, "qty": position_qty,
                        "pnl": pnl, "reason": "sl" if stop and price <= stop else "tp",
                    })
                    position_qty = 0.0
                    entry_price = 0.0
                    stop = take = None

            signal = strategy.generate(slice_df, symbol)
            if signal.side == Side.BUY and position_qty == 0.0 and signal.confidence >= 0.4:
                alloc = cash * self.position_pct * max(signal.confidence, 0.4)
                qty = alloc / price
                fees = qty * price * self.fee_bps / 10_000
                if qty > 0 and alloc + fees <= cash:
                    cash -= qty * price + fees
                    position_qty = qty
                    entry_price = price
                    stop = signal.stop_loss
                    take = signal.take_profit
            elif signal.side == Side.SELL and position_qty > 0:
                proceeds = position_qty * price
                fees = proceeds * self.fee_bps / 10_000
                cash += proceeds - fees
                pnl = (price - entry_price) * position_qty - fees
                pnls.append(pnl)
                trades.append({"entry": entry_price, "exit": price, "qty": position_qty, "pnl": pnl, "reason": "signal"})
                position_qty = 0.0
                entry_price = 0.0
                stop = take = None

            mv = position_qty * price
            equity_curve.append(cash + mv)

        equity = pd.Series(equity_curve)
        metrics = compute_metrics(equity, pnls)
        return BacktestResult(
            strategy=strategy.name,
            symbol=symbol,
            equity_curve=list(equity),
            metrics=metrics,
            trades=trades,
        )
