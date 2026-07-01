"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { LineChart } from "@/components/Charts";
import { Journey } from "@/components/Journey";
import {
  BacktestResult,
  Instrument,
  ReportCard,
  Template,
  api,
} from "@/lib/api";

function pct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

// Plain-English, trader's-eye explanations for every number on the report card.
const METRIC_HELP: Record<string, string> = {
  "Total return":
    "How much the account grew or shrank over the test. The headline number — but read it alongside drawdown.",
  Trades: "How many complete buy→sell round-trips happened. Too few and the result is just luck.",
  "Win rate": "Share of trades that made money. High isn't everything — one big loss can sink many small wins.",
  "Profit factor":
    "Rupees won for every rupee lost. Above 1 is profitable; above 1.5 is genuinely good; ∞ means no losers yet.",
  Expectancy: "Average rupees you'd expect to make per trade. If this is positive, the edge is real over many trades.",
  "Max drawdown": "The worst peak-to-trough drop. This is the pain you must be able to stomach. Lower is calmer.",
  "Sharpe (per bar)": "Return earned per unit of risk (wobble). Higher means smoother, more reliable gains.",
  Charges: "Brokerage, STT and other costs — modelled exactly like real Zerodha trading, so nothing is sugar-coated.",
};

export default function BacktestPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [token, setToken] = useState<number | null>(null);
  const [template, setTemplate] = useState("sma_crossover");
  const [quantity, setQuantity] = useState(50);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.instruments().then((xs) => {
      setInstruments(xs);
      setToken((t) => t ?? xs[0]?.instrument_token ?? null);
    });
    api.templates().then((r) => setTemplates(r.templates));
  }, []);

  // Group strategies by category for a scannable, beginner-friendly picker.
  const grouped = useMemo(() => {
    const g: Record<string, Template[]> = {};
    for (const t of templates) (g[t.category ?? "Other"] ??= []).push(t);
    return g;
  }, [templates]);

  async function run() {
    if (token === null) return;
    setBusy(true);
    setError("");
    try {
      const r = await api.backtest({
        instrument_token: token,
        template,
        quantity,
        candle_count: 300,
        interval_minutes: 5,
        warmup: 50,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setBusy(false);
    }
  }

  const selectedTpl = templates.find((t) => t.id === template);
  const rep = result?.report;
  const profitable = rep ? rep.total_return_pct > 0 : false;

  return (
    <>
      <div className="page-head">
        <h1>Strategy Lab</h1>
        <p className="lead">
          Pick a ready-made strategy, test it on historical data in seconds, then take the
          winners to paper trading — and only the proven ones to real money.
        </p>
      </div>

      <Journey active="backtest" />

      <div className="panel">
        <h2>1 · Choose a strategy</h2>
        <p className="muted">Click a card to select it. Each one is a complete, tested set of buy/sell rules.</p>
        {Object.entries(grouped).map(([cat, items]) => (
          <div key={cat} className="cat-group">
            <div className="cat-title">{cat}</div>
            <div className="strat-grid">
              {items.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`strat-card ${template === t.id ? "selected" : ""}`}
                  onClick={() => setTemplate(t.id)}
                >
                  <div className="strat-name">{t.name}</div>
                  <div className="strat-desc">{t.description}</div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>2 · Test it</h2>
        <div className="bt-form">
          <div>
            <label>Instrument</label>
            <select value={token ?? ""} onChange={(e) => setToken(Number(e.target.value))}>
              {instruments.map((i) => (
                <option key={i.instrument_token} value={i.instrument_token}>
                  {i.tradingsymbol}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Quantity (shares per trade)</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
            />
          </div>
          <button className="primary big" disabled={busy} onClick={run}>
            {busy ? "Running…" : `▶ Backtest ${selectedTpl ? `“${selectedTpl.name}”` : ""}`}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {rep && result && (
        <>
          <div className="panel">
            <h2>Report card</h2>
            <div className={`verdict ${profitable ? "good" : "bad"}`}>
              {profitable
                ? `✓ This strategy made ${pct(rep.total_return_pct)} over the test, across ${rep.num_trades} trade(s).`
                : `✗ This strategy lost ${pct(rep.total_return_pct)} over the test. Try another one, or a different instrument.`}
            </div>
            <div className="stats wrap">
              <Stat label="Total return" value={pct(rep.total_return_pct)} cls={rep.total_return_pct >= 0 ? "pos" : "neg"} />
              <Stat label="Trades" value={String(rep.num_trades)} />
              <Stat label="Win rate" value={`${rep.win_rate}%`} />
              <Stat label="Profit factor" value={rep.profit_factor === null ? "∞" : rep.profit_factor.toFixed(2)} />
              <Stat label="Expectancy" value={`₹${rep.expectancy}`} cls={rep.expectancy >= 0 ? "pos" : "neg"} />
              <Stat label="Max drawdown" value={`${rep.max_drawdown_pct}%`} cls="neg" />
              <Stat label="Sharpe (per bar)" value={rep.sharpe.toFixed(3)} />
              <Stat label="Charges" value={`₹${rep.total_charges}`} />
            </div>
            <p className="muted hint">💡 Hover any tile to learn what it means. Rule of thumb: want a positive return, profit factor above 1, and a drawdown you could sit through calmly.</p>
          </div>

          <div className="panel">
            <h2>Equity curve</h2>
            <LineChart
              values={result.equity_curve.map((p) => p.equity)}
              baseline={rep.initial_capital}
              color={rep.total_return_pct >= 0 ? "var(--green)" : "var(--red)"}
            />
            <p className="muted">
              {result.equity_curve.length} bars · starting ₹
              {rep.initial_capital.toLocaleString("en-IN")} · ending ₹
              {rep.final_equity.toLocaleString("en-IN")}
            </p>
          </div>

          <NextSteps report={rep} profitable={profitable} strategyName={selectedTpl?.name ?? template} />
        </>
      )}

      <p className="disclaimer">
        Backtests use synthetic data offline and the same fill + charges model as paper
        trading. Past performance does not guarantee future results. Not investment advice.
      </p>
    </>
  );
}

function NextSteps({
  report,
  profitable,
  strategyName,
}: {
  report: ReportCard;
  profitable: boolean;
  strategyName: string;
}) {
  return (
    <div className="panel next-steps">
      <h2>3 · Your next step</h2>
      {profitable ? (
        <p className="muted">
          “{strategyName}” looks promising on history. A professional never jumps straight
          to real money — you prove it forward first. Do these in order:
        </p>
      ) : (
        <p className="muted">
          This one didn&apos;t work on this instrument. That&apos;s exactly what the lab is
          for — fail on paper, not with your savings. Pick another strategy above and re-test.
        </p>
      )}
      <div className="next-cards">
        <Link href="/" className="next-card">
          <div className="next-icon">📝</div>
          <div>
            <div className="next-title">Paper trade it</div>
            <div className="muted">
              Place the same buy/sell moves with virtual money on live prices. Watch how it
              behaves in real time — no risk.
            </div>
          </div>
        </Link>
        <Link href="/live" className="next-card">
          <div className="next-icon">💰</div>
          <div>
            <div className="next-title">Promote to real money</div>
            <div className="muted">
              The Live page checks this strategy against strict rules (enough trades, win
              rate, drawdown) before it can ever place a real order.
            </div>
          </div>
        </Link>
      </div>
      <p className="muted hint">
        This backtest scored: {report.num_trades} trades · {report.win_rate}% win rate ·
        {report.max_drawdown_pct}% max drawdown. The Live page uses these exact numbers at
        the promotion gate.
      </p>
    </div>
  );
}

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div className="stat" title={METRIC_HELP[label] ?? ""}>
      <div className="label">{label}</div>
      <div className={`value ${cls ?? ""}`}>{value}</div>
    </div>
  );
}
