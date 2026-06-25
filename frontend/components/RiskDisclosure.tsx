"use client";

/** The real-money risk disclosure. Shown before live trading can be enabled. */
export const RISK_POINTS: string[] = [
  "You can lose money — including more than you expect with leverage (intraday/MIS). Trade only money you can afford to lose.",
  "Orders placed here are REAL and routed to your live Zerodha account. Fills, prices, and charges are final and your responsibility.",
  "Past performance and backtest/paper results do NOT guarantee future results. Markets change; a strategy that worked can stop working.",
  "Backtests use historical or synthetic data and idealized fills. Real fills differ due to slippage, liquidity, gaps, and latency.",
  "This software may contain bugs. It is provided 'as is', with no warranty. You are responsible for monitoring every position.",
  "Technology can fail: internet, broker API, daily token expiry (~6 AM IST), or this app going down can leave positions unmanaged.",
  "Real orders require a static IP registered with Kite; a misconfigured or changed IP will cause orders to be rejected.",
  "The kill switch and risk limits are safety aids, not guarantees. They cannot prevent gap moves or losses on already-open positions.",
  "This is not investment advice. Nothing here is a recommendation to buy or sell. Consult a SEBI-registered advisor if unsure.",
];

export function RiskDisclosure({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`disclosure ${compact ? "compact" : ""}`}>
      <ul>
        {RISK_POINTS.map((p, i) => (
          <li key={i}>{p}</li>
        ))}
      </ul>
      <p className="muted">
        Full details: see <code>docs/RISKS.md</code> in the repository.
      </p>
    </div>
  );
}
