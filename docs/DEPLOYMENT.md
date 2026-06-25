# Deployment & Operations

> Before enabling real-money trading, read [`RISKS.md`](RISKS.md) in full.

This is a **single-user** application. The whole stack runs offline (synthetic data,
deterministic backtests) with no Zerodha/Anthropic accounts. Live data and real orders
require additional setup below.

## Components

| Component | Where it runs | Notes |
|---|---|---|
| FastAPI backend | any host | REST + WebSocket gateway; paper engine; analysis/backtest. |
| Next.js frontend | any host / static | Talks to the backend via `NEXT_PUBLIC_API_URL`. |
| Postgres + TimescaleDB | container/managed | Tick/candle storage (compose file in `infra/`). |
| Redis | container/managed | Pub/sub + cache. |
| **Live-order service** | **host with a registered static IP** | The only component that *must* sit on the whitelisted IP. |

## Local development

```bash
cd infra && docker compose up -d           # Postgres+TimescaleDB, Redis
cd ../backend && python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" && pytest && uvicorn app.main:app --reload
cd ../frontend && npm install && npm run dev
```

## Enabling live market data + real orders

1. **Kite Connect app** — create one at https://kite.trade (₹500/month per API key; live
   + historical data bundled). Set in `backend/.env`:
   ```
   KITE_API_KEY=...
   KITE_API_SECRET=...
   KITE_REDIRECT_URL=https://your-host/auth/kite/callback
   USE_MOCK_MARKET_DATA=false
   ```
2. **Static IP (mandatory for orders).** Run the backend (specifically the order path) on
   a host with a fixed public IP and **register that exact IP** in the Kite developer
   console. Orders from unregistered IPs are rejected. If your IP changes, update it there
   or orders will fail.
3. **Install the optional extras** on the live host:
   ```
   pip install -e ".[kite,ai]"
   ```
4. **Daily login.** Kite access tokens expire ~6 AM IST. Each trading day:
   - Open `/auth/kite/login` → authorize → Kite redirects to `/auth/kite/callback`.
   - The token is held in memory and flips live trading to **configured** (the kill switch
     still defaults OFF). There is no fully headless token generation.
5. **Anthropic (optional, for AI features).** Set `ANTHROPIC_API_KEY` to enable commentary,
   coaching, trade review, and NL→strategy authoring. Without it, those endpoints return a
   clean 503 and the rest of the app works.

## Going live safely (operational runbook)

1. Confirm market data is flowing (watchlist updates; `/metrics` `ticks_processed` rising).
2. In the **Live** page: read and acknowledge the risk disclosure (step 1).
3. Set conservative risk limits (step 2) — start with the smallest size you can.
4. Promote a strategy only after it clears the gate (step 3) — and remember the gate does
   not guarantee profit.
5. Arm the kill switch (step 4) only when you intend to trade and can monitor positions.
6. **Disarm** (emergency stop) ends new orders instantly; it does not close open
   positions — exit those manually if needed (here or in the Zerodha Kite app).

## Security & secrets

- Never commit `.env`. Store `KITE_API_SECRET`, `ANTHROPIC_API_KEY`, and the daily access
  token securely. The plan calls for encrypting the access token at rest — do this before
  any multi-tenant or hosted deployment.
- Restrict who can reach the backend; it can place real orders once armed.
- Keep the live host patched; treat its static IP and credentials as sensitive.

## Observability

- `GET /health` — mock vs live mode.
- `GET /metrics` — uptime + counters (ticks processed, alerts triggered, live orders).
- Backend logs at INFO via stdlib logging.

## Production hardening (later)

- Replace the in-process market hub with Redis pub/sub so multiple workers share the one
  Kite WebSocket connection (one per API key).
- Persist accounts, orders, strategies, journal, and the daily token (encrypted) in
  Postgres.
- Add auth if exposing beyond localhost; add alerting on the live host's health and on the
  daily token expiry.
- Add a watchdog that disarms automatically if market data stops flowing.
