# Trading strategies, in plain English

A "strategy" here is just a set of rules that decides **when to buy** and **when to
sell** — automatically, with no emotion. You can test any of these on past data
(backtest) or run them with paper money before risking anything real.

Every strategy below is a one-click preset on the **Backtest** page. They never short
(bet on prices falling) by default — they only buy and later sell.

A quick vocabulary, then the strategies:

- **Bar / candle** — one chunk of time (e.g. 5 minutes) showing the price.
- **Average** — add up the price over the last N bars and divide by N. It smooths out
  the noise so you can see the underlying direction.
- **Volume** — how many shares changed hands. High volume = lots of people trading =
  the move is "for real". Low volume = a move that might fizzle out.
- **Breakout** — the price escaping above (or below) the range it's been stuck in.

---

## Strategies based on averages (trend-following)

### Ride the trend (price above its average)
Buy when the price is **above its own average of the last 50 bars** — that usually means
it's trending up. Sell when it drops back below the average.
*Idea:* stay in while it's going up, step aside when it turns down. The simplest
trend-follower there is.

### Fast vs slow average (quick trend change)
Track two averages: a **fast** one (last 12 bars) and a **slow** one (last 26 bars).
When the fast crosses **above** the slow, the recent mood is turning up → buy. When it
crosses back **below**, sell.
*Idea:* the fast average reacts to fresh moves sooner than the slow one, so their
crossing is an early "trend just changed" signal.

### SMA 20/50 crossover *(already built in)*
Same idea as above but with 20- and 50-bar averages — slower and steadier, fewer false
alarms but later signals.

---

## Strategies based on volume (is the crowd behind the move?)

### Big-volume push (crowd is buying)
Buy only when **two** things happen at once:
1. A lot more shares than usual trade (volume is over **2× the recent average**), and
2. The price is **above its short-term average** (it's moving up).

Sell when the price falls back below that short-term average.
*Idea:* a price rise on heavy volume means real buying interest, not a random wiggle.
The volume filter keeps you out of weak, low-conviction moves.

### Above the fair price (VWAP)
**VWAP** is the average price weighted by how many shares traded at each level — a good
"fair value" for the session. Buy when the price is **above VWAP** (buyers in control),
get out when it drops below.
*Idea:* a favourite of intraday traders for telling whether the day "belongs" to buyers
or sellers.

---

## Strategies based on market movement (breakouts)

### New-high breakout (price escapes its range)
Buy when the price climbs **above the highest point of the last 20 bars** — it has
broken out of its recent range to a new high, which can start a fresh move up. Get out
if it sinks **below the lowest point of the last 10 bars**, meaning the breakout failed.
*Idea:* big moves often begin the moment price breaks out of a long quiet range.

### RSI mean reversion / Bollinger reversion / MACD trend *(already built in)*
- **RSI mean reversion** — buy when the stock looks "oversold" (beaten down too far,
  too fast) and is likely to bounce.
- **Bollinger reversion** — buy when price drops to the bottom of its usual range and
  exit when it returns to the middle.
- **MACD trend** — another momentum-based way to follow trends.

---

## How to try one

1. Open the **Backtest** page, pick an instrument, and choose a strategy from the list.
2. Run it — you'll get a report card: how much it made, win rate, biggest drop
   (drawdown), etc.
3. Like the result? Run it in **paper** mode (fake money, real-time) to watch it work
   before ever using real money.

> ⚠️ None of this is investment advice. Backtests show what *would have* happened on past
> data; the future can differ. Always paper-trade first, and read `docs/RISKS.md` before
> turning on real money.

---

## For the curious: how a strategy is defined

Under the hood each strategy is a small, readable config (no programming needed) — this
is also what the AI strategy author produces from a plain-English request. Example:

```json
{
  "name": "Ride the trend (price above its average)",
  "indicators": { "average": { "kind": "sma", "period": 50 } },
  "entry_long": [ { "left": "close", "op": ">", "right": "average" } ],
  "exit_long":  [ { "left": "close", "op": "<", "right": "average" } ]
}
```

Operands can be an indicator name, a number, or a source: `close`/`price` or `volume`.
Available indicator `kind`s: `sma`, `ema`, `rsi`, `macd`, `macd_signal`,
`boll_upper`/`boll_mid`/`boll_lower`, `vol_sma` (average volume), `vwap`, `atr`
(volatility), and `highest`/`lowest` (the breakout level over the previous N bars). Add
`"mult": 2.0` to a spec to scale its line — e.g. a "twice the average volume" threshold.
