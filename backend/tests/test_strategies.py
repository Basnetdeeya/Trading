"""Smoke-test every strategy against synthetic data."""
from __future__ import annotations

import asyncio

import pandas as pd

from app.core.types import Side
from app.data.simulated import SimulatedProvider
from app.strategies.registry import all_strategies


def _df() -> pd.DataFrame:
    return asyncio.run(SimulatedProvider().fetch_ohlcv("TEST", "1h", 400))


def test_all_strategies_produce_valid_signals():
    df = _df()
    for strategy in all_strategies():
        sig = strategy.generate(df, "TEST")
        assert sig.side in Side
        assert 0.0 <= sig.confidence <= 1.0
        assert sig.strategy == strategy.name


def test_backtest_runs_end_to_end():
    from app.backtest.engine import BacktestEngine

    df = _df()
    engine = BacktestEngine(starting_capital=10_000.0)
    for strategy in all_strategies():
        result = engine.run(strategy, df, "TEST")
        assert len(result.equity_curve) > 0
        assert result.metrics.max_drawdown >= 0.0
