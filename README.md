# AI Trading App (Zerodha / Kite Connect)

An AI-assisted trading and investing platform for the Indian market. It connects to a
user's **Zerodha** account via the official **Kite Connect** API, lets users analyze
markets and test strategies with **paper (virtual) money**, and — only after a strategy
proves itself through a strict promotion gate — promote it to **real-money** trading.

> ⚠️ **This software is for education and research. It is NOT investment advice.**
> Trading involves a real risk of loss — with leverage you can lose more than you put in.
> Before enabling any real-money ("Live") feature, **read [`docs/RISKS.md`](docs/RISKS.md)
> in full.** Use real-money features entirely at your own risk. No warranty.

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
- **Phase 4** — real-money trading behind a **strict, layered gate**: risk-disclosure
  acknowledgement → promotion gate (a strategy must clear performance criteria) → kill
  switch (armed/disarmed, default OFF) → per-order/position/daily-loss/open-position risk
  caps. `LiveBroker` places real Kite orders only on the static-IP host. A guided **Live**
  page walks through every step with prominent warnings. Endpoints under `/live/*`.
- **Phase 5** — AI trading **coach** + trade auto-**review**, a trade **journal**, price
  **alerts** on the live feed, and **/metrics** observability. **Coach** page in the UI.

See [`docs/RISKS.md`](docs/RISKS.md) for the full risk disclosure and
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the live-trading runbook (static IP, daily
login, going-live checklist).

The whole stack runs **offline** (synthetic market data + deterministic backtests) with
no Zerodha account; add Kite/Anthropic keys to enable live data and AI features. Real
orders additionally require the static-IP setup and arming the kill switch.
