# AI Trading App with Zerodha Connectivity — Plan of Action

## Context

An AI-assisted trading/investing application for the Indian market that connects to a
user's **Zerodha** account via the official **Kite Connect** API. Users analyze markets,
design and test strategies with **paper (virtual) money**, and — only after a strategy
proves itself — promote it to **real-money** trading.

### Decisions

- **Phase 1 = paper-trading + data core** (foundation everything else depends on).
- **Stack = Python (FastAPI) + Next.js/React + TypeScript.**
- **Real money behind a strict promotion gate** (paper criteria + opt-in + caps + kill switch).
- **Single-user application** (decided): one paper account, one market hub, one candle
  aggregator per process. No per-user scoping or auth — the local operator is the only
  user. State lives in `app/state.py` behind small interfaces so DB persistence can be
  added later without reshaping callers.

### Hard constraints from Zerodha (shape the architecture)

1. **No Zerodha sandbox / paper API** → paper engine is in-house, simulating fills on the live tick feed.
2. **Static IP mandatory for order placement** (since 2025-04-01) → live-order service runs on a whitelisted host.
3. **Billing:** ₹500/month per API key; live + historical data bundled (since 2025-02-08).
4. **WebSocket:** one connection/key, up to 3,000 instruments, 5-level depth.
5. **Access token expires daily** (~6 AM IST); interactive login required.

## Architecture

```
Next.js frontend ──HTTPS/WSS──► FastAPI gateway
   ┌──────────────┬──────────────┬───────────────┬──────────────┐
   ▼              ▼              ▼               ▼              ▼
 Kite auth   Market-data svc  Paper engine   Strategy/AI   Live-order svc
 (daily)     (WS→Timescale     (sim fills,    (signals,     (real orders,
              +Redis pub/sub)   virtual P&L)   backtest)     STATIC IP host)
   └──────────── Postgres + TimescaleDB + Redis ─────────────────┘
```

## Phases

- **Phase 0 ✅** — repo scaffold, docker-compose (Postgres+TimescaleDB, Redis), config, CI.
- **Phase 1 ✅** — Kite auth/session, instrument master, market-data service,
  **paper-trading engine** (core), frontend MVP, fill-engine tests.
- **Phase 2 ✅** — indicator library (SMA/EMA/RSI/MACD/Bollinger/ATR/VWAP), candle
  aggregation + synthetic/Kite history, screeners, candlestick + RSI charts, AI market
  commentary (`/analysis/*`, `/ai/commentary`).
- **Phase 3 ✅** — rule-DSL strategies + templates, event-driven backtester that reuses
  the paper-engine fill/charges model, report-card metrics, AI NL→strategy authoring
  (`/strategy/*`, `/ai/strategy`); Analysis + Backtest UI pages.
- **Phase 4** — real-money trading behind the promotion gate; live-order service; risk controls.
- **Phase 5** — AI coach, journaling, alerts, observability, productionization.

## Feature set

- **Learning/safety:** realistic paper fills (slippage + charges), strategy report cards,
  AI trading coach, risk-education nudges.
- **Analysis:** live charts + 50+ indicators, scanners, sector/index dashboards, F&O analytics.
- **Trading:** strategy builder + backtesting, paper→real promotion, order management
  (market/limit/SL/GTT), basket/SIP, portfolio analytics (XIRR, rebalancing).
- **AI (Claude):** NL strategy authoring, signal explanations, trade auto-review,
  optional Kite MCP for account Q&A.

## Risks & mitigations

- Daily token expiry → re-auth flow; read-only degrade.
- Static-IP SPOF → isolate live-order service; paper unaffected.
- Paper↔live divergence → one shared fill/charge model across backtest/paper/live.
- 3,000-instrument cap → subscribe only to watchlist + active strategy symbols.
- Financial/compliance risk → real money gated; full audit trail; not investment advice.

## Verification

- Phase 1 acceptance: login → ticks land in Timescale + stream to UI → place paper
  limit/SL → fills trigger correctly, charges applied, virtual P&L matches hand-computed.
- Backtest/paper parity check on the same candles.
- Real-order path validated last on static-IP host, smallest size, kill switch armed.

## Sources

- Kite Connect product & pricing: https://zerodha.com/products/api/
- No API sandbox: https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/api-sandbox
- WebSocket docs: https://kite.trade/docs/connect/v3/websocket/
- pykiteconnect: https://github.com/zerodha/pykiteconnect
- Kite MCP: https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp
