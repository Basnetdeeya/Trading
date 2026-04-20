# Architecture

```
                        ┌──────────────────────────────────┐
                        │            Frontend              │
                        │  Next.js 14 Dashboard (React)    │
                        │  - Portfolio / PnL / Risk        │
                        │  - Strategy perf charts          │
                        │  - AI insights panel             │
                        │  - Risk slider + allocation      │
                        └───────────────┬──────────────────┘
                                        │  HTTPS / WebSocket
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                              Backend (FastAPI)                      │
│                                                                     │
│  ┌────────────┐   ┌───────────────┐   ┌──────────────────────────┐ │
│  │ REST API   │   │ WebSocket Hub │   │ Scheduler (APScheduler)  │ │
│  └─────┬──────┘   └──────┬────────┘   └────────────┬─────────────┘ │
│        │                 │                         │               │
│        ▼                 ▼                         ▼               │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Strategy Engine / Orchestrator              │ │
│  │  loops: fetch -> analyze -> agent-select -> risk -> execute    │ │
│  └───┬───────────┬────────────┬───────────┬──────────────┬───────┘ │
│      │           │            │           │              │         │
│      ▼           ▼            ▼           ▼              ▼         │
│  ┌─────────┐ ┌────────┐  ┌──────────┐ ┌──────────┐  ┌──────────┐  │
│  │ Data    │ │ 15+    │  │   AI     │ │  Risk    │  │Portfolio │  │
│  │ Layer   │ │Strateg.│  │  Agent   │ │ Manager  │  │ Manager  │  │
│  └────┬────┘ └────────┘  └─────┬────┘ └────┬─────┘  └────┬─────┘  │
│       │                        │           │             │        │
│  CoinGecko / Alpha Vantage     │       Circuit           │        │
│  Yahoo / Binance / Polymarket  │       breaker           │        │
│       │                        ▼           │             ▼        │
│       │                  Claude / OpenAI   │        Execution     │
│       │                  (LLM reasoning)   │        (paper/live)  │
│       ▼                                    ▼                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │             Backtesting Engine (historical replay)             │ │
│  │             Metrics: Sharpe, MaxDD, WinRate, PF                │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────┐
                         │ Storage (SQLite/Postgres)│
                         │  - trades, orders, pnl   │
                         │  - configs, logs         │
                         └──────────────────────────┘
```

## Loop

1. **Ingest**: Data layer pulls OHLCV bars and order-book snapshots.
2. **Analyze**: Each enabled strategy emits `Signal(side, confidence, sl, tp)`.
3. **Agent**: The AI agent reads the market regime + all signals and selects
   the best strategy mix, returning a probabilistic recommendation.
4. **Risk**: The Risk Manager validates against max-DD, daily loss,
   diversification, and sizing rules.
5. **Execute**: Orders are routed to the Paper broker (default) or a live
   adapter if the user has explicitly enabled live trading.
6. **Persist**: Fills, PnL, and telemetry are written to the database and
   streamed to the frontend via WebSocket.

## Modules

| Module | Path | Responsibility |
|---|---|---|
| API | `backend/app/api` | REST endpoints for frontend |
| Data | `backend/app/data` | Provider adapters (CoinGecko, AV, Yahoo, Polymarket) |
| Strategies | `backend/app/strategies` | 15+ signal generators |
| Agent | `backend/app/agents` | LLM reasoning + strategy selector |
| Risk | `backend/app/risk` | Pre-trade + portfolio-level checks |
| Portfolio | `backend/app/portfolio` | Positions, PnL, equity curve |
| Execution | `backend/app/execution` | Paper + live broker adapters |
| Backtest | `backend/app/backtest` | Historical simulation + metrics |
| Core | `backend/app/core` | Config, logging, types |

## Extending

- **New strategy**: subclass `BaseStrategy` in `strategies/base.py` and
  register it in `strategies/registry.py`.
- **New data source**: implement `DataProvider` in `data/base.py`.
- **New broker**: implement `Broker` in `execution/base.py`.
- **New agent**: implement `AgentBackend` in `agents/base.py` (Claude and
  OpenAI adapters are provided; an offline heuristic fallback is always on).
