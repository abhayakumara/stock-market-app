# AI Trading App (Zerodha / Kite Connect)

An AI-assisted trading and investing platform for the Indian market. It connects to a
user's **Zerodha** account via the official **Kite Connect** API, lets users analyze
markets and test strategies with **paper (virtual) money**, and — only after a strategy
proves itself through a strict promotion gate — promote it to **real-money** trading.

> ⚠️ This software is for education and research. It is **not** investment advice.
> Trading involves risk of loss. Use real-money features at your own risk.

## Why this architecture

Zerodha provides **no sandbox / paper-trading API**, so the paper engine is built
entirely in-house: it simulates fills against the live WebSocket tick feed and models
real brokerage + statutory charges. Real order placement requires a **static IP**
registered with Kite, so the live-order service is the only component that must run on
a whitelisted host.

See [`docs/PLAN.md`](docs/PLAN.md) for the full plan of action and phasing.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic, `pykiteconnect`, Anthropic SDK
- **Data:** PostgreSQL + TimescaleDB (ticks/candles), Redis (pub/sub + cache)
- **Frontend:** Next.js (React, TypeScript)
- **AI:** Claude (`claude-opus-4-8`)

## Repository layout

```
backend/    FastAPI service: Kite integration, market data, paper engine, API gateway
frontend/   Next.js app (UI)
infra/      docker-compose + DB init
docs/       plan and design docs
```

## Quick start (local, no Zerodha credentials needed)

The paper-trading engine and a synthetic tick replay source run without any Zerodha
account, so you can develop and test the core offline.

```bash
# 1. Infra (Postgres+TimescaleDB, Redis)
cd infra && docker compose up -d

# 2. Backend
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # fill in keys when you have them
pytest                          # run the test suite (offline)
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 3. Frontend
cd ../frontend
npm install
npm run dev                     # http://localhost:3000
```

## Connecting Zerodha (when ready)

1. Create a Kite Connect app at https://kite.trade (₹500/month per API key; live +
   historical data bundled).
2. Put `KITE_API_KEY` / `KITE_API_SECRET` in `backend/.env`.
3. For **real-money** order placement, run the live-order service on a host with a
   **static IP** and register that IP in the Kite developer console.
4. Log in via the app's `/auth/kite/login` flow each day (Kite access tokens expire
   daily, ~6 AM IST).

## Status

Single-user application. Implemented so far (see `docs/PLAN.md`):

- **Phase 0–1** — Kite auth flow, live/mock market-data hub, in-house paper-trading
  engine (slippage + brokerage/STT/charges model), REST + WebSocket gateway, trade UI.
- **Phase 2** — technical indicators (SMA/EMA/RSI/MACD/Bollinger/ATR/VWAP), candle
  aggregation + synthetic/Kite history, screeners, candlestick + RSI charts, AI market
  commentary. Endpoints under `/analysis/*` and `/ai/commentary`.
- **Phase 3** — rule-DSL strategies + built-in templates, an event-driven backtester
  that reuses the paper-engine fill/charges model (backtest↔paper parity), strategy
  report-card metrics, and AI natural-language → strategy authoring. Endpoints under
  `/strategy/*` and `/ai/strategy`; **Analysis** and **Backtest** pages in the UI.

Next: **Phase 4** — real-money trading behind the strict promotion gate (live-order
service on the static-IP host, position caps, kill switch).

The whole stack runs **offline** (synthetic market data + deterministic backtests) with
no Zerodha account; add Kite/Anthropic keys to enable live data and AI features.
