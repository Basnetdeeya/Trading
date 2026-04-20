# Quant Sentinel — Automated Trading System

A production-ready, multi-asset automated trading platform with an AI agent
layer, 15+ strategies, a strict risk manager, a backtesting engine, and a
React/Next.js dashboard.

> **Disclaimer:** Trading involves substantial risk of loss. This software is
> provided for research and educational purposes only. There are **no**
> guarantees of profitability. Always run in paper/simulation mode first, and
> never allocate capital you cannot afford to lose. See `DISCLAIMER.md`.

## Highlights

- **Multi-asset**: Crypto, Forex, Equities, Prediction markets
- **Modes**: Paper (default), Simulation, Live (explicit opt-in)
- **Strategies**: MA Crossover, RSI, MACD, Bollinger, S/R, Fibonacci, Volume
  Spike, Trend Following, Mean Reversion, Breakout, Momentum, VWAP, Grid,
  Arbitrage, News-Sentiment
- **Risk controls**: Max daily loss, max drawdown, position sizing (fixed %
  and optional Kelly), auto stop-loss, diversification caps, circuit breaker
- **AI Agent**: LLM-driven regime detection and strategy selection
  (Anthropic Claude / OpenAI compatible)
- **Backtester**: Sharpe, max drawdown, win rate, profit factor, equity curve
- **Frontend**: Next.js dashboard with live PnL, risk exposure, strategy
  comparison, AI insights, and user-controlled risk sliders
- **Deployable**: Dockerfile + docker-compose for single-command startup

## Quickstart

```bash
# 1. Configure
cp .env.example .env
# edit .env — add any API keys you have (all optional; system works with
# simulated/free data sources by default)

# 2. Run with Docker
docker compose up --build

# Backend  -> http://localhost:8000  (Swagger at /docs)
# Frontend -> http://localhost:3000
```

### Local (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Project layout

```
.
├── backend/               FastAPI service, strategy engine, AI agent
│   ├── app/
│   │   ├── agents/        LLM reasoning + strategy selector
│   │   ├── api/           REST endpoints
│   │   ├── backtest/      Backtesting engine + metrics
│   │   ├── core/          Config, logging, constants
│   │   ├── data/          Market data providers
│   │   ├── execution/     Order execution (paper + live adapters)
│   │   ├── portfolio/     Portfolio and position manager
│   │   ├── risk/          Risk manager + circuit breaker
│   │   ├── strategies/    15+ trading strategies
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/              Next.js 14 app router dashboard
│   ├── app/
│   ├── components/
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
├── docker-compose.yml
├── .env.example
└── README.md
```

See `docs/ARCHITECTURE.md` for the full system diagram and
`docs/DEPLOYMENT.md` for production deployment guidance.
