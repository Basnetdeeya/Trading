"""Pre-trade risk checks, position sizing, and circuit breaker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from app.core.logging import get_logger
from app.core.types import Side, Signal
from app.portfolio.manager import PortfolioManager

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    max_position_pct: float
    max_daily_loss_pct: float
    max_drawdown_pct: float
    max_open_positions: int
    use_kelly: bool = False


@dataclass
class RiskDecision:
    approved: bool
    quantity: float
    reason: str
    signal: Signal


class RiskManager:
    """Stateless checks given portfolio state + last prices."""

    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits
        self._halted = False
        self._halt_reason = ""

    # ---- circuit breaker ---------------------------------------------------
    def is_halted(self) -> bool:
        return self._halted

    def halt(self, reason: str) -> None:
        logger.warning("risk: HALT — %s", reason)
        self._halted = True
        self._halt_reason = reason

    def resume(self) -> None:
        logger.info("risk: resumed")
        self._halted = False
        self._halt_reason = ""

    def status(self) -> dict:
        return {"halted": self._halted, "reason": self._halt_reason, "limits": self.limits.__dict__}

    def check_portfolio_health(self, pm: PortfolioManager, last_prices: Dict[str, float]) -> None:
        if pm.drawdown(last_prices) >= self.limits.max_drawdown_pct:
            self.halt(f"max drawdown hit ({pm.drawdown(last_prices):.2%})")
            return
        daily = pm.daily_pnl(last_prices)
        if daily < 0 and abs(daily) / max(pm.state.starting_capital, 1) >= self.limits.max_daily_loss_pct:
            self.halt(f"max daily loss hit ({daily:.2f})")

    # ---- sizing ------------------------------------------------------------
    def size(
        self,
        signal: Signal,
        pm: PortfolioManager,
        last_prices: Dict[str, float],
        kelly_edge: Optional[float] = None,
    ) -> float:
        equity = pm.equity(last_prices)
        if equity <= 0 or signal.price <= 0:
            return 0.0
        cap = equity * self.limits.max_position_pct
        if self.limits.use_kelly and kelly_edge is not None and kelly_edge > 0:
            # Half-Kelly
            cap = min(cap, equity * min(kelly_edge / 2, self.limits.max_position_pct))
        # Confidence scaling
        cap *= max(0.1, min(signal.confidence, 1.0))
        qty = cap / signal.price
        # never risk more cash than we have for BUYs
        if signal.side == Side.BUY:
            qty = min(qty, pm.state.cash / signal.price)
        return max(qty, 0.0)

    # ---- full gate ---------------------------------------------------------
    def evaluate(
        self,
        signal: Signal,
        pm: PortfolioManager,
        last_prices: Dict[str, float],
    ) -> RiskDecision:
        if self._halted:
            return RiskDecision(False, 0.0, f"halted: {self._halt_reason}", signal)
        if not signal.is_actionable():
            return RiskDecision(False, 0.0, "non-actionable signal", signal)
        if signal.confidence < 0.3:
            return RiskDecision(False, 0.0, f"confidence {signal.confidence:.2f} below threshold", signal)

        self.check_portfolio_health(pm, last_prices)
        if self._halted:
            return RiskDecision(False, 0.0, f"halted: {self._halt_reason}", signal)

        if signal.side == Side.BUY and pm.open_count() >= self.limits.max_open_positions:
            if pm.position(signal.symbol) is None:
                return RiskDecision(False, 0.0, "max open positions reached", signal)

        qty = self.size(signal, pm, last_prices)
        if qty <= 0:
            return RiskDecision(False, 0.0, "sized to zero", signal)

        # For SELL: only allow closing existing long positions
        if signal.side == Side.SELL:
            pos = pm.position(signal.symbol)
            if pos is None:
                return RiskDecision(False, 0.0, "no long position to sell", signal)
            qty = min(qty, pos.quantity)
        return RiskDecision(True, qty, "approved", signal)
