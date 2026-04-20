"""Application configuration loaded from environment."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


TradingMode = Literal["paper", "simulation", "live"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_token: str = "change-me-in-prod"
    auth_enabled: bool = False

    # Trading mode
    trading_mode: TradingMode = "paper"
    live_trading_confirmed: str = "NO"

    # Risk defaults
    starting_capital_usd: float = 10_000.0
    max_position_pct: float = 0.05
    max_daily_loss_pct: float = 0.02
    max_drawdown_pct: float = 0.15
    max_open_positions: int = 8
    max_correlation: float = 0.85
    use_kelly: bool = False
    default_stop_loss_pct: float = 0.02
    default_take_profit_pct: float = 0.04

    # Data providers
    coingecko_api_key: str = ""
    alpha_vantage_api_key: str = ""
    yahoo_finance_enabled: bool = True
    binance_api_key: str = ""
    binance_api_secret: str = ""
    polymarket_api_url: str = ""

    # AI
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Persistence
    database_url: str = "sqlite:///./quant_sentinel.db"

    @property
    def live_trading_allowed(self) -> bool:
        return (
            self.trading_mode == "live"
            and self.live_trading_confirmed == "YES_I_UNDERSTAND_THE_RISK"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
