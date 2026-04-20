"""In-memory portfolio manager with equity curve tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.core.types import Position, Side, Trade


@dataclass
class EquityPoint:
    timestamp: datetime
    equity: float


@dataclass
class PortfolioState:
    cash: float
    starting_capital: float
    positions: Dict[str, Position] = field(default_factory=dict)
    closed_trades: List[Trade] = field(default_factory=list)
    equity_curve: List[EquityPoint] = field(default_factory=list)
    peak_equity: float = 0.0


class PortfolioManager:
    def __init__(self, starting_capital: float) -> None:
        self.state = PortfolioState(
            cash=starting_capital,
            starting_capital=starting_capital,
            peak_equity=starting_capital,
        )

    # ---- queries -----------------------------------------------------------
    def equity(self, last_prices: Dict[str, float]) -> float:
        mv = sum(p.market_value(last_prices.get(p.symbol, p.avg_price)) for p in self.state.positions.values())
        return self.state.cash + mv

    def position(self, symbol: str) -> Optional[Position]:
        return self.state.positions.get(symbol)

    def open_count(self) -> int:
        return len(self.state.positions)

    def drawdown(self, last_prices: Dict[str, float]) -> float:
        eq = self.equity(last_prices)
        peak = max(self.state.peak_equity, eq)
        return (peak - eq) / peak if peak > 0 else 0.0

    def daily_pnl(self, last_prices: Dict[str, float]) -> float:
        if not self.state.equity_curve:
            return 0.0
        today = datetime.utcnow().date()
        opens = [p for p in self.state.equity_curve if p.timestamp.date() == today]
        if not opens:
            return 0.0
        return self.equity(last_prices) - opens[0].equity

    # ---- state mutation ----------------------------------------------------
    def apply_fill(
        self,
        symbol: str,
        side: Side,
        qty: float,
        price: float,
        strategy: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[Trade]:
        if side == Side.BUY:
            cost = qty * price
            if cost > self.state.cash:
                return None
            self.state.cash -= cost
            pos = self.state.positions.get(symbol)
            if pos is None:
                self.state.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=qty,
                    avg_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy=strategy,
                )
            else:
                total_qty = pos.quantity + qty
                pos.avg_price = (pos.avg_price * pos.quantity + price * qty) / total_qty
                pos.quantity = total_qty
            return None
        # SELL
        pos = self.state.positions.get(symbol)
        if pos is None:
            return None
        sell_qty = min(qty, pos.quantity)
        proceeds = sell_qty * price
        self.state.cash += proceeds
        pnl = (price - pos.avg_price) * sell_qty
        trade = Trade(
            symbol=symbol,
            side=Side.SELL,
            quantity=sell_qty,
            entry_price=pos.avg_price,
            exit_price=price,
            pnl=pnl,
            opened_at=pos.opened_at,
            closed_at=datetime.utcnow(),
            strategy=strategy or pos.strategy,
        )
        self.state.closed_trades.append(trade)
        pos.quantity -= sell_qty
        if pos.quantity <= 1e-9:
            del self.state.positions[symbol]
        return trade

    def mark(self, last_prices: Dict[str, float]) -> None:
        eq = self.equity(last_prices)
        self.state.peak_equity = max(self.state.peak_equity, eq)
        self.state.equity_curve.append(EquityPoint(timestamp=datetime.utcnow(), equity=eq))
        if len(self.state.equity_curve) > 5000:
            self.state.equity_curve = self.state.equity_curve[-5000:]

    # ---- reporting ---------------------------------------------------------
    def snapshot(self, last_prices: Dict[str, float]) -> dict:
        eq = self.equity(last_prices)
        return {
            "cash": round(self.state.cash, 2),
            "equity": round(eq, 2),
            "starting_capital": self.state.starting_capital,
            "return_pct": round((eq / self.state.starting_capital - 1) * 100, 4),
            "drawdown_pct": round(self.drawdown(last_prices) * 100, 4),
            "open_positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": round(p.avg_price, 4),
                    "last_price": round(last_prices.get(p.symbol, p.avg_price), 4),
                    "unrealized_pnl": round(
                        p.unrealized_pnl(last_prices.get(p.symbol, p.avg_price)), 2
                    ),
                    "stop_loss": p.stop_loss,
                    "take_profit": p.take_profit,
                    "strategy": p.strategy,
                }
                for p in self.state.positions.values()
            ],
            "closed_trades": len(self.state.closed_trades),
        }
