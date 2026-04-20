"""Pydantic schemas for the HTTP API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.types import AssetClass


class WatchlistItem(BaseModel):
    symbol: str
    asset_class: AssetClass = AssetClass.CRYPTO
    interval: str = "1h"


class WatchlistUpdate(BaseModel):
    items: List[WatchlistItem]


class RiskUpdate(BaseModel):
    max_position_pct: Optional[float] = Field(None, ge=0.001, le=1.0)
    max_daily_loss_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_drawdown_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_open_positions: Optional[int] = Field(None, ge=1, le=100)
    use_kelly: Optional[bool] = None


class StrategyToggle(BaseModel):
    name: str
    enabled: bool


class BacktestRequest(BaseModel):
    symbol: str
    asset_class: AssetClass = AssetClass.CRYPTO
    interval: str = "1h"
    lookback: int = 500
    strategies: Optional[List[str]] = None  # default: all enabled


class ModeUpdate(BaseModel):
    mode: str = Field(..., pattern="^(paper|simulation|live)$")
    confirm_phrase: Optional[str] = None
