"""Top-level orchestrator: fetch -> strategies -> agent -> risk -> execute."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.agents.base import AgentBackend
from app.agents.heuristic import HeuristicAgent
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.types import AssetClass, Order, Side, Signal
from app.data.router import DataRouter
from app.execution.base import Broker
from app.execution.live import LiveBrokerStub
from app.execution.paper import PaperBroker
from app.portfolio.manager import PortfolioManager
from app.risk.manager import RiskLimits, RiskManager
from app.strategies.registry import StrategyRegistry

logger = get_logger(__name__)


@dataclass
class WatchItem:
    symbol: str
    asset_class: AssetClass
    interval: str = "1h"


@dataclass
class EngineState:
    watchlist: List[WatchItem] = field(default_factory=list)
    last_prices: Dict[str, float] = field(default_factory=dict)
    last_signals: Dict[str, List[Signal]] = field(default_factory=dict)
    last_agent_decisions: Dict[str, dict] = field(default_factory=dict)
    last_fills: List[dict] = field(default_factory=list)
    last_run_at: Optional[datetime] = None


class Orchestrator:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        data: Optional[DataRouter] = None,
        registry: Optional[StrategyRegistry] = None,
        agent: Optional[AgentBackend] = None,
        broker: Optional[Broker] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.data = data or DataRouter(self.settings)
        self.registry = registry or StrategyRegistry()
        self.agent = agent or HeuristicAgent()
        self.broker = broker or self._make_broker()
        self.portfolio = PortfolioManager(starting_capital=self.settings.starting_capital_usd)
        self.risk = RiskManager(
            RiskLimits(
                max_position_pct=self.settings.max_position_pct,
                max_daily_loss_pct=self.settings.max_daily_loss_pct,
                max_drawdown_pct=self.settings.max_drawdown_pct,
                max_open_positions=self.settings.max_open_positions,
                use_kelly=self.settings.use_kelly,
            )
        )
        self.state = EngineState(
            watchlist=[
                WatchItem("BTC-USD", AssetClass.CRYPTO, "1h"),
                WatchItem("ETH-USD", AssetClass.CRYPTO, "1h"),
                WatchItem("AAPL", AssetClass.EQUITY, "1h"),
                WatchItem("EURUSD=X", AssetClass.FOREX, "1h"),
            ]
        )
        self._lock = asyncio.Lock()

    # ----------------------------------------------------------------- setup
    def _make_broker(self) -> Broker:
        if self.settings.live_trading_allowed:
            logger.warning("LIVE trading enabled — using LiveBrokerStub until an adapter is wired in")
            return LiveBrokerStub()
        return PaperBroker()

    # ----------------------------------------------------------------- ctrl
    def set_watchlist(self, items: List[WatchItem]) -> None:
        self.state.watchlist = items

    def update_limits(self, **overrides) -> None:
        for key, value in overrides.items():
            if hasattr(self.risk.limits, key) and value is not None:
                setattr(self.risk.limits, key, value)

    # ----------------------------------------------------------------- loop
    async def run_once(self) -> dict:
        async with self._lock:
            results: Dict[str, dict] = {}
            for item in self.state.watchlist:
                try:
                    df = await self.data.fetch_ohlcv(item.symbol, item.asset_class, item.interval)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("fetch failed for %s: %s", item.symbol, exc)
                    continue
                if df is None or df.empty:
                    continue
                last_price = float(df["close"].iloc[-1])
                self.state.last_prices[item.symbol] = last_price

                signals = [s.generate(df, item.symbol) for s in self.registry.enabled()]
                self.state.last_signals[item.symbol] = signals

                decision = await self.agent.decide(
                    symbol=item.symbol,
                    asset_class=item.asset_class.value,
                    df=df,
                    signals=signals,
                )
                self.state.last_agent_decisions[item.symbol] = decision

                chosen = self._compose_signal(item.symbol, signals, decision, last_price)
                rd = self.risk.evaluate(chosen, self.portfolio, self.state.last_prices)
                results[item.symbol] = {
                    "price": last_price,
                    "signals": [self._signal_to_dict(s) for s in signals],
                    "agent": decision,
                    "chosen": self._signal_to_dict(chosen),
                    "risk": {"approved": rd.approved, "quantity": rd.quantity, "reason": rd.reason},
                }
                if rd.approved:
                    await self._execute(chosen, rd.quantity)

            self.portfolio.mark(self.state.last_prices)
            self.state.last_run_at = datetime.utcnow()
            # auto-exit on SL/TP
            await self._check_stops()
            return results

    async def _check_stops(self) -> None:
        for symbol, pos in list(self.portfolio.state.positions.items()):
            price = self.state.last_prices.get(symbol)
            if price is None:
                continue
            triggered = None
            if pos.stop_loss and price <= pos.stop_loss:
                triggered = "stop_loss"
            elif pos.take_profit and price >= pos.take_profit:
                triggered = "take_profit"
            if triggered:
                order = Order(symbol=symbol, side=Side.SELL, quantity=pos.quantity, price=price, strategy=pos.strategy)
                filled = await self.broker.place(order)
                trade = self.portfolio.apply_fill(
                    symbol=symbol, side=Side.SELL, qty=filled.quantity, price=filled.price,
                    strategy=pos.strategy,
                )
                self.state.last_fills.append({
                    "symbol": symbol, "side": "SELL", "qty": filled.quantity,
                    "price": filled.price, "reason": triggered, "strategy": pos.strategy,
                    "pnl": trade.pnl if trade else 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                })

    async def _execute(self, signal: Signal, quantity: float) -> None:
        order = Order(
            symbol=signal.symbol,
            side=signal.side,
            quantity=quantity,
            price=signal.price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy=signal.strategy,
        )
        try:
            filled = await self.broker.place(order)
        except Exception as exc:  # noqa: BLE001
            logger.error("broker rejected order: %s", exc)
            return
        trade = self.portfolio.apply_fill(
            symbol=filled.symbol, side=filled.side, qty=filled.quantity,
            price=filled.price, strategy=filled.strategy,
            stop_loss=filled.stop_loss, take_profit=filled.take_profit,
        )
        self.state.last_fills.append({
            "symbol": filled.symbol,
            "side": filled.side.value,
            "qty": filled.quantity,
            "price": round(filled.price, 4),
            "strategy": filled.strategy,
            "pnl": trade.pnl if trade else None,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self.state.last_fills) > 500:
            self.state.last_fills = self.state.last_fills[-500:]

    # -------------------------------------------------------------- helpers
    def _compose_signal(
        self,
        symbol: str,
        signals: List[Signal],
        decision: dict,
        price: float,
    ) -> Signal:
        chosen_name = decision.get("chosen_strategy")
        for s in signals:
            if s.strategy == chosen_name and s.is_actionable():
                # Blend strategy confidence with agent confidence
                agent_conf = float(decision.get("confidence", 0.5))
                s.confidence = 0.5 * s.confidence + 0.5 * agent_conf
                s.rationale = f"{s.rationale} | agent: {decision.get('rationale', '')}"
                return s
        side_str = decision.get("side", "HOLD")
        side = Side(side_str) if side_str in Side.__members__ else Side.HOLD
        return Signal(
            symbol=symbol,
            side=side,
            confidence=float(decision.get("confidence", 0.0)),
            price=price,
            strategy=chosen_name or "agent",
            rationale=decision.get("rationale", ""),
        )

    @staticmethod
    def _signal_to_dict(s: Signal) -> dict:
        return {
            "symbol": s.symbol,
            "side": s.side.value,
            "confidence": round(s.confidence, 3),
            "price": round(s.price, 4),
            "stop_loss": s.stop_loss,
            "take_profit": s.take_profit,
            "strategy": s.strategy,
            "rationale": s.rationale,
        }

    # -------------------------------------------------------------- reports
    def snapshot(self) -> dict:
        return {
            "mode": self.settings.trading_mode,
            "broker": self.broker.name,
            "last_run_at": self.state.last_run_at.isoformat() if self.state.last_run_at else None,
            "portfolio": self.portfolio.snapshot(self.state.last_prices),
            "risk": self.risk.status(),
            "strategies": self.registry.describe(),
            "watchlist": [
                {"symbol": w.symbol, "asset_class": w.asset_class.value, "interval": w.interval}
                for w in self.state.watchlist
            ],
            "recent_fills": self.state.last_fills[-50:],
        }

    async def close(self) -> None:
        await self.data.close()
        await self.broker.close()
