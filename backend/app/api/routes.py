"""REST API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backtest.engine import BacktestEngine
from app.core.config import Settings, get_settings
from app.core.types import AssetClass
from app.engine.orchestrator import Orchestrator, WatchItem
from app.strategies.registry import all_strategies

from .schemas import (
    BacktestRequest,
    ModeUpdate,
    RiskUpdate,
    StrategyToggle,
    WatchlistUpdate,
)

router = APIRouter(prefix="/api/v1")


def get_orchestrator() -> Orchestrator:
    from app.main import app  # avoid circular
    return app.state.orchestrator


# ---------------------------------------------------------------- health
@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/config")
async def config(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "trading_mode": settings.trading_mode,
        "live_trading_allowed": settings.live_trading_allowed,
        "starting_capital": settings.starting_capital_usd,
        "providers": {
            "coingecko": True,
            "alpha_vantage": bool(settings.alpha_vantage_api_key),
            "yahoo": settings.yahoo_finance_enabled,
            "polymarket": bool(settings.polymarket_api_url),
        },
    }


# ---------------------------------------------------------------- snapshot
@router.get("/dashboard")
async def dashboard(orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    return orch.snapshot()


@router.post("/engine/tick")
async def run_tick(orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    """Force one orchestration cycle immediately."""
    return {"cycle": await orch.run_once(), "snapshot": orch.snapshot()}


# ---------------------------------------------------------------- control
@router.post("/control/halt")
async def halt(reason: str = "manual", orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    orch.risk.halt(reason)
    return orch.risk.status()


@router.post("/control/resume")
async def resume(orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    orch.risk.resume()
    return orch.risk.status()


@router.post("/control/mode")
async def set_mode(req: ModeUpdate, orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    if req.mode == "live" and req.confirm_phrase != "YES_I_UNDERSTAND_THE_RISK":
        raise HTTPException(
            status_code=400,
            detail="Live mode requires confirm_phrase='YES_I_UNDERSTAND_THE_RISK'",
        )
    orch.settings.trading_mode = req.mode  # runtime override
    if req.mode == "live":
        orch.settings.live_trading_confirmed = "YES_I_UNDERSTAND_THE_RISK"
    orch.broker = orch._make_broker()  # swap broker
    return {"mode": orch.settings.trading_mode, "broker": orch.broker.name}


# ---------------------------------------------------------------- watchlist
@router.post("/watchlist")
async def update_watchlist(req: WatchlistUpdate, orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    orch.set_watchlist([WatchItem(i.symbol, AssetClass(i.asset_class), i.interval) for i in req.items])
    return {"watchlist": [w.__dict__ for w in orch.state.watchlist]}


# ---------------------------------------------------------------- risk
@router.post("/risk")
async def update_risk(req: RiskUpdate, orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    orch.update_limits(**req.model_dump(exclude_none=True))
    return orch.risk.status()


# ---------------------------------------------------------------- strategies
@router.get("/strategies")
async def list_strategies(orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    return {"strategies": orch.registry.describe()}


@router.post("/strategies/toggle")
async def toggle_strategy(req: StrategyToggle, orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    if orch.registry.get(req.name) is None:
        raise HTTPException(status_code=404, detail=f"unknown strategy: {req.name}")
    orch.registry.set_enabled(req.name, req.enabled)
    return {"strategies": orch.registry.describe()}


# ---------------------------------------------------------------- backtest
@router.post("/backtest")
async def backtest(req: BacktestRequest, orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    df = await orch.data.fetch_ohlcv(
        req.symbol, AssetClass(req.asset_class), interval=req.interval, lookback=req.lookback
    )
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="no data returned")
    engine = BacktestEngine(
        starting_capital=orch.settings.starting_capital_usd,
        position_pct=orch.settings.max_position_pct * 3,
    )
    wanted = set(req.strategies or [s.name for s in all_strategies(orch.settings)])
    results = []
    for strat in all_strategies(orch.settings):
        if strat.name not in wanted:
            continue
        r = engine.run(strat, df, req.symbol)
        results.append({
            "strategy": r.strategy,
            "symbol": r.symbol,
            "metrics": r.metrics.__dict__,
            "equity_curve_sample": r.equity_curve[:: max(1, len(r.equity_curve) // 100)],
            "trade_count": len(r.trades),
        })
    results.sort(key=lambda x: x["metrics"]["sharpe"], reverse=True)
    return {"symbol": req.symbol, "bars": len(df), "results": results}


# ---------------------------------------------------------------- agent insights
@router.get("/insights")
async def insights(orch: Orchestrator = Depends(get_orchestrator)) -> dict:
    return {
        "decisions": orch.state.last_agent_decisions,
        "last_run_at": orch.state.last_run_at.isoformat() if orch.state.last_run_at else None,
        "agent": orch.agent.name,
    }
