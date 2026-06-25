# ⚠️ Risk Disclosure, Warnings & Cautions — READ BEFORE USING REAL MONEY

> **This software is for education and research. It is NOT investment advice and NOT a
> recommendation to buy or sell any security.** Trading and investing in financial
> markets carries a real and substantial risk of loss. You can lose part or all of your
> capital — and, with leverage, more than your initial outlay. **Only trade money you can
> afford to lose entirely.** By enabling real-money ("Live") trading you accept full
> responsibility for every order, fill, and outcome.

If you are not certain you understand these risks, **do not enable Live trading.** Use the
paper-trading mode (virtual money) to learn first, and consult a SEBI-registered
investment adviser if you need personalized advice.

---

## 1. Market & financial risks

- **You can lose money.** Prices move against you. Losses can be rapid and large,
  especially in volatile or illiquid instruments.
- **Leverage magnifies losses (intraday / MIS).** Margin/leverage products can lose more
  than the cash you committed. A small adverse move can wipe out a leveraged position and
  leave you owing money.
- **Gaps and overnight risk.** Prices can jump between the previous close and the next
  open (news, results, global events). Stop-losses do **not** protect against gaps — your
  fill can be far worse than your trigger.
- **Liquidity risk.** In thin instruments you may not be able to exit at a fair price, or
  at all, when you want to.
- **No guaranteed profits.** No strategy, indicator, AI suggestion, or backtest result
  guarantees future gains. Anyone promising guaranteed returns is wrong or lying.

## 2. Strategy, backtest & paper-trading limitations

- **Past performance ≠ future results.** A strategy that performed well historically can
  fail immediately and persistently going forward. Markets regime-shift.
- **Backtests are idealized.** This app's backtester (and, by default, its market data
  when offline) uses **synthetic or historical** data and **modeled** fills. Real
  execution differs because of slippage, partial fills, queue position, latency, and
  liquidity. **Backtest profit does not imply live profit.**
- **The promotion gate is a discipline aid, not a safety guarantee.** Clearing the
  promotion criteria (minimum trades, win rate, drawdown, return, profit factor, Sharpe)
  means a strategy looked robust *in testing*. It does **not** mean it will be profitable
  with real money. Promotion only *unlocks* the ability to risk real capital — the risk
  remains entirely yours.
- **Overfitting.** A strategy tuned to look good on one dataset often performs worse live.
  Be skeptical of strategies that only work with very specific parameters.
- **Paper trading is optimistic.** Simulated fills assume your order would have executed.
  Real markets may not have filled you at that price, or at all.

## 3. Technology & operational risks

- **Software may contain bugs.** This project is provided **"as is", without warranty of
  any kind.** Despite tests, defects can cause wrong orders, missed exits, incorrect P&L,
  or unexpected behavior. **You must monitor every open position yourself.**
- **Outages leave positions unmanaged.** If your internet, the broker API, the data feed,
  or this application goes down, automated logic stops — but your **open positions stay
  open** and continue to gain or lose money. Have a manual fallback (the Zerodha Kite app)
  to exit positions.
- **Daily token expiry.** Kite access tokens expire every day (~6 AM IST). If you do not
  re-login, live data and order placement stop working until you do. Do not assume the app
  is "watching" your positions if you have not logged in.
- **Static-IP requirement.** Zerodha requires order placement from a **static IP
  registered in the Kite developer console** (since 2025-04-01). If the IP is wrong,
  changes, or is not whitelisted, **real orders will be rejected** — possibly leaving you
  unable to exit when you need to. See `docs/DEPLOYMENT.md`.
- **Latency & race conditions.** There is a delay between a signal, an order, and a fill.
  Fast markets can move through your intended price in that window.
- **Single point of failure.** The live-order service runs on one host. If it fails, no
  automated orders are placed. The paper engine is unaffected, but real positions are not
  managed automatically.

## 4. The risk controls — what they do and do NOT do

The app enforces a strict, layered gate before any real order is sent. **None of these is
a guarantee against loss.**

| Control | What it does | What it does NOT do |
|---|---|---|
| **Kill switch (arm/disarm)** | Blocks all real orders unless explicitly armed; disarm is an instant emergency stop for **new** orders. | Does not close or protect positions you already hold. Disarming stops new entries, not existing risk. |
| **Risk-disclosure acknowledgement** | Forces you to confirm you understand the risks before arming. | Does not reduce risk. |
| **Promotion gate** | Prevents a strategy from automating real money until it clears performance criteria in testing. | Does not predict the future or prevent live losses. |
| **Per-order value cap** | Rejects orders above a notional you set. | Does not limit total loss across many orders or from price moves. |
| **Per-position value cap** | Limits exposure per instrument. | Does not cap mark-to-market loss on that position. |
| **Daily-loss cap** | Halts *new* exposure-increasing orders once realized losses reach your limit for the day. | Does not auto-close positions; unrealized losses can keep growing. |
| **Max open positions** | Limits how many instruments you can hold at once. | Does not limit loss per position. |

**Set conservative limits and start with the smallest possible size.** Increase only after
sustained, real experience — never based on backtest results alone.

## 5. AI feature cautions

- The AI (Claude) provides **educational commentary, coaching, and strategy drafting
  only.** It can be wrong, incomplete, or out of date. It does **not** have real-time
  awareness of your full situation or the market.
- **The AI never places orders and never bypasses the risk gate or your limits.** Every
  real order still requires your explicit action and passes every control above.
- Do not treat AI output as advice or a recommendation. Verify everything independently.

## 6. Legal, tax & regulatory

- Nothing in this software is investment, legal, or tax advice. Markets and brokerage are
  regulated (in India, by SEBI); you are responsible for complying with all applicable
  laws, exchange rules, and your broker's terms.
- You are responsible for your own taxes (e.g. STT, capital gains, GST on charges). The
  charge figures shown are **approximations** for education and may not match your contract
  note.
- Use of the Zerodha Kite Connect API is subject to Zerodha's terms and pricing.

## 7. Your responsibilities checklist

- [ ] I will only risk money I can afford to lose entirely.
- [ ] I have practiced extensively in **paper mode** before considering real money.
- [ ] I have set conservative risk limits and will start with the smallest size.
- [ ] I will **monitor my open positions myself** and not rely on the app being up.
- [ ] I have a manual fallback (Zerodha Kite app/web) to exit positions if this app fails.
- [ ] I understand backtest/paper/AI results do not predict real results.
- [ ] I accept full responsibility for all real-money orders and outcomes.

---

**No warranty.** This software is provided "as is", without warranty of any kind, express
or implied. The authors are not liable for any losses or damages arising from its use.
Trading is risky; the decision to trade real money is yours alone.
