"use client";

import { useEffect, useState } from "react";
import { LineChart } from "@/components/Charts";
import {
  BacktestResult,
  Instrument,
  Template,
  api,
} from "@/lib/api";

function pct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

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

  return (
    <>
      <div className="panel">
        <h2>Backtest a strategy</h2>
        <div className="bt-form">
          <div>
            <label>Strategy</label>
            <select value={template} onChange={(e) => setTemplate(e.target.value)}>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Instrument</label>
            <select
              value={token ?? ""}
              onChange={(e) => setToken(Number(e.target.value))}
            >
              {instruments.map((i) => (
                <option key={i.instrument_token} value={i.instrument_token}>
                  {i.tradingsymbol}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Quantity</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
            />
          </div>
          <button className="primary" disabled={busy} onClick={run}>
            {busy ? "Running…" : "Run backtest"}
          </button>
        </div>
        {selectedTpl && <p className="muted">{selectedTpl.description}</p>}
        {error && <div className="error">{error}</div>}
      </div>

      {rep && result && (
        <>
          <div className="panel">
            <h2>Report card</h2>
            <div className="stats wrap">
              <Stat label="Total return" value={pct(rep.total_return_pct)} cls={rep.total_return_pct >= 0 ? "pos" : "neg"} />
              <Stat label="Trades" value={String(rep.num_trades)} />
              <Stat label="Win rate" value={`${rep.win_rate}%`} />
              <Stat
                label="Profit factor"
                value={rep.profit_factor === null ? "∞" : rep.profit_factor.toFixed(2)}
              />
              <Stat label="Expectancy" value={`₹${rep.expectancy}`} cls={rep.expectancy >= 0 ? "pos" : "neg"} />
              <Stat label="Max drawdown" value={`${rep.max_drawdown_pct}%`} cls="neg" />
              <Stat label="Sharpe (per bar)" value={rep.sharpe.toFixed(3)} />
              <Stat label="Charges" value={`₹${rep.total_charges}`} />
            </div>
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
        </>
      )}

      <p className="disclaimer">
        Backtests use synthetic data offline and the same fill + charges model as paper
        trading. Past performance does not guarantee future results.
      </p>
    </>
  );
}

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className={`value ${cls ?? ""}`}>{value}</div>
    </div>
  );
}
