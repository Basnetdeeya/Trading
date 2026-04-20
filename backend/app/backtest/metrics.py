"""Common performance metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass
class Metrics:
    total_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades: int


def compute_metrics(equity: pd.Series, pnls: List[float], periods_per_year: int = 252 * 24) -> Metrics:
    if equity.empty:
        return Metrics(0, 0, 0, 0, 0, 0)
    rets = equity.pct_change().dropna()
    total_ret = float(equity.iloc[-1] / equity.iloc[0] - 1)
    if rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(periods_per_year))
    else:
        sharpe = 0.0
    running_peak = equity.cummax()
    drawdown = (running_peak - equity) / running_peak
    max_dd = float(drawdown.max() or 0.0)

    pnl_arr = np.array(pnls) if pnls else np.array([0.0])
    wins = pnl_arr[pnl_arr > 0]
    losses = pnl_arr[pnl_arr < 0]
    win_rate = float(len(wins) / len(pnl_arr)) if len(pnl_arr) else 0.0
    profit_factor = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf") if wins.sum() > 0 else 0.0

    return Metrics(
        total_return=round(total_ret, 6),
        sharpe=round(sharpe, 4),
        max_drawdown=round(max_dd, 6),
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4) if np.isfinite(profit_factor) else 999.0,
        trades=len(pnl_arr) if pnls else 0,
    )
