from __future__ import annotations

from app.core.types import Side, Signal
from app.portfolio.manager import PortfolioManager
from app.risk.manager import RiskLimits, RiskManager


def _limits() -> RiskLimits:
    return RiskLimits(
        max_position_pct=0.1,
        max_daily_loss_pct=0.05,
        max_drawdown_pct=0.2,
        max_open_positions=5,
    )


def test_risk_blocks_low_confidence():
    pm = PortfolioManager(10_000)
    rm = RiskManager(_limits())
    sig = Signal(symbol="BTC-USD", side=Side.BUY, confidence=0.1, price=100.0, strategy="x")
    decision = rm.evaluate(sig, pm, {"BTC-USD": 100.0})
    assert not decision.approved


def test_portfolio_buy_sell_cycle():
    pm = PortfolioManager(10_000)
    pm.apply_fill("BTC-USD", Side.BUY, qty=1.0, price=100.0, strategy="x")
    assert pm.position("BTC-USD") is not None
    trade = pm.apply_fill("BTC-USD", Side.SELL, qty=1.0, price=110.0, strategy="x")
    assert trade is not None
    assert trade.pnl == 10.0
    assert pm.position("BTC-USD") is None


def test_circuit_breaker_trips_on_drawdown():
    pm = PortfolioManager(10_000)
    rm = RiskManager(RiskLimits(0.1, 0.5, 0.05, 5))
    # Simulate equity drop
    pm.state.peak_equity = 10_000
    pm.state.cash = 9_000
    rm.check_portfolio_health(pm, {})
    assert rm.is_halted()
