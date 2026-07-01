"use client";

import { useCallback, useEffect, useState } from "react";
import { CandleChart, RSIChart } from "@/components/Charts";
import { Journey } from "@/components/Journey";
import {
  Alert,
  Candle,
  Indicators,
  Instrument,
  ScanHit,
  api,
} from "@/lib/api";

const COUNT = 200;
const INTERVAL = 5;

const SCAN_LABELS: Record<string, string> = {
  rsi_oversold: "RSI oversold (<30)",
  rsi_overbought: "RSI overbought (>70)",
  golden_cross: "Golden cross (20/50)",
  above_200sma: "Above 200 SMA",
  breakout_20: "20-bar breakout",
};

export default function AnalysisPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [token, setToken] = useState<number | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [ind, setInd] = useState<Indicators | null>(null);

  const [scan, setScan] = useState("rsi_oversold");
  const [hits, setHits] = useState<ScanHit[] | null>(null);

  const [commentary, setCommentary] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiErr, setAiErr] = useState("");

  useEffect(() => {
    api.instruments().then((xs) => {
      setInstruments(xs);
      setToken((t) => t ?? xs[0]?.instrument_token ?? null);
    });
  }, []);

  const load = useCallback((tk: number) => {
    Promise.all([
      api.candles(tk, COUNT, INTERVAL),
      api.indicators(tk, COUNT, INTERVAL),
    ]).then(([c, i]) => {
      setCandles(c.candles);
      setInd(i);
    });
  }, []);

  useEffect(() => {
    if (token !== null) load(token);
  }, [token, load]);

  const runScan = useCallback(() => {
    api.screener(scan).then((r) => setHits(r.hits));
  }, [scan]);

  async function getCommentary() {
    if (token === null) return;
    setAiBusy(true);
    setAiErr("");
    setCommentary("");
    try {
      const r = await api.aiCommentary(token);
      setCommentary(r.commentary);
    } catch (e) {
      setAiErr(e instanceof Error ? e.message : "AI unavailable");
    } finally {
      setAiBusy(false);
    }
  }

  const symbol =
    instruments.find((i) => i.instrument_token === token)?.tradingsymbol ?? "";

  return (
    <>
      <div className="page-head">
        <h1>Analysis & charts</h1>
        <p className="lead">
          Read the price action, spot setups with the screener, and let the AI explain what
          it sees — the &ldquo;learn&rdquo; step before you ever test a strategy.
        </p>
      </div>

      <Journey active="learn" />

      <div className="panel">
        <div className="toolbar">
          <div>
            <label>Instrument</label>
            <select
              value={token ?? ""}
              onChange={(e) => setToken(Number(e.target.value))}
            >
              {instruments.map((i) => (
                <option key={i.instrument_token} value={i.instrument_token}>
                  {i.tradingsymbol} — {i.name}
                </option>
              ))}
            </select>
          </div>
          <div className="legend">
            <span className="key sma20">SMA20</span>
            <span className="key sma50">SMA50</span>
            <span className="key boll">Bollinger</span>
          </div>
        </div>

        <CandleChart
          candles={candles}
          overlays={
            ind
              ? [
                  { name: "sma20", color: "#4c8dff", data: ind.sma20 },
                  { name: "sma50", color: "#f5a623", data: ind.sma50 },
                  { name: "bu", color: "#7d8aa0", data: ind.boll_upper },
                  { name: "bl", color: "#7d8aa0", data: ind.boll_lower },
                ]
              : []
          }
        />
        <div className="subtitle">RSI (14)</div>
        {ind && <RSIChart rsi={ind.rsi14} />}
      </div>

      <div className="grid">
        <div className="panel">
          <h2>Screener</h2>
          <div className="toolbar">
            <select value={scan} onChange={(e) => setScan(e.target.value)}>
              {Object.entries(SCAN_LABELS).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
            <button className="primary" onClick={runScan}>
              Run scan
            </button>
          </div>
          {hits !== null &&
            (hits.length === 0 ? (
              <p className="muted">No matches right now.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {hits.map((h) => (
                    <tr key={h.instrument_token}>
                      <td>{h.tradingsymbol}</td>
                      <td>
                        {Object.entries(h.detail)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ))}
        </div>

        <div className="panel">
          <h2>AI commentary</h2>
          <button className="primary" disabled={aiBusy} onClick={getCommentary}>
            {aiBusy ? "Analyzing…" : `Analyze ${symbol}`}
          </button>
          {commentary && <p className="ai-text">{commentary}</p>}
          {aiErr && (
            <p className="muted">
              {aiErr.includes("ANTHROPIC") || aiErr.includes("anthropic")
                ? "Set ANTHROPIC_API_KEY (and install the AI extra) to enable Claude commentary."
                : aiErr}
            </p>
          )}
        </div>
      </div>

      <AlertsPanel token={token} symbol={symbol} />

      <p className="disclaimer">
        For education and research only. Not investment advice.
      </p>
    </>
  );
}

function AlertsPanel({ token, symbol }: { token: number | null; symbol: string }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [triggered, setTriggered] = useState<Alert[]>([]);
  const [op, setOp] = useState<">" | "<">(">");
  const [price, setPrice] = useState("");

  const load = useCallback(() => {
    api.alerts().then((r) => {
      setAlerts(r.alerts);
      setTriggered(r.triggered);
    });
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [load]);

  async function add() {
    if (token === null || !price) return;
    await api.addAlert({ instrument_token: token, op, price: parseFloat(price) });
    setPrice("");
    load();
  }

  return (
    <div className="panel">
      <h2>Price alerts</h2>
      <div className="toolbar">
        <span className="muted">
          Alert on <strong>{symbol}</strong> when price
        </span>
        <select value={op} onChange={(e) => setOp(e.target.value as ">" | "<")}>
          <option value=">">rises above</option>
          <option value="<">falls below</option>
        </select>
        <input
          type="number"
          placeholder="price"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        <button className="primary" onClick={add}>
          Add alert
        </button>
      </div>
      {alerts.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Condition</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td>{a.tradingsymbol}</td>
                <td>
                  {a.op} {a.price}
                </td>
                <td>{a.active ? "active" : "triggered"}</td>
                <td>
                  <button
                    className="link"
                    onClick={() => api.removeAlert(a.id).then(load)}
                  >
                    remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {triggered.length > 0 && (
        <p className="ok">
          🔔 Recently triggered:{" "}
          {triggered
            .slice(0, 5)
            .map((a) => `${a.tradingsymbol} ${a.op} ${a.price}`)
            .join(", ")}
        </p>
      )}
    </div>
  );
}
