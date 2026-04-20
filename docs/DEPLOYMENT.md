# Deployment Guide

## Docker (recommended)

```bash
cp .env.example .env
docker compose up --build -d
```

Services:
- `backend` — FastAPI on :8000
- `frontend` — Next.js on :3000
- `db` — Postgres (optional; SQLite is used by default)

## Production checklist

1. Set `TRADING_MODE=paper` until you have validated a strategy in backtest
   **and** paper for at least 30 days.
2. Rotate API keys. Never commit `.env`.
3. Put the backend behind a reverse proxy (Nginx/Caddy) with TLS.
4. Enable auth in `backend/app/core/config.py` (`AUTH_ENABLED=true`) and
   provide a bearer token via `API_TOKEN`.
5. Configure log shipping (stdout is JSON-formatted).
6. Monitor the `/healthz` and `/metrics` endpoints.
7. Back up the database daily.
8. Leave the circuit breaker thresholds strict. Widen them only after you
   understand why they were tripping.

## Going live (dangerous)

Live trading is disabled by default. To enable:

1. Set `TRADING_MODE=live` in `.env`.
2. Set `LIVE_TRADING_CONFIRMED=YES_I_UNDERSTAND_THE_RISK`.
3. Provide exchange credentials (`BINANCE_API_KEY`, etc.) with **withdraw
   disabled** at the exchange.
4. Start small: `MAX_POSITION_USD=50`.
5. Watch the dashboard. Kill-switch is `POST /api/v1/control/halt`.

If any of these steps feels uncomfortable, stay in paper mode.
