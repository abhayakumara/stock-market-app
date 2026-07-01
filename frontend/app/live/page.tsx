"use client";

import { useCallback, useEffect, useState } from "react";
import { Journey } from "@/components/Journey";
import { RiskDisclosure } from "@/components/RiskDisclosure";
import {
  Instrument,
  LiveStatus,
  PlaceOrder,
  PromotionResult,
  Template,
  api,
} from "@/lib/api";

export default function LivePage() {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const refresh = useCallback(() => {
    api.liveStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    api.instruments().then(setInstruments);
    api.templates().then((r) => setTemplates(r.templates));
  }, [refresh]);

  function flash(setter: (s: LiveStatus) => void) {
    return (s: LiveStatus) => {
      setter(s);
      setErr("");
    };
  }
  async function run(fn: () => Promise<LiveStatus>, okMsg: string) {
    setMsg("");
    setErr("");
    try {
      setStatus(await fn());
      setMsg(okMsg);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Action failed");
    }
  }

  if (!status) return <p className="muted">Loading…</p>;

  const armed = status.armed;

  return (
    <>
      <div className="page-head">
        <h1>Go live — real money</h1>
        <p className="lead">
          The final step, and the only one that risks real capital. Work through the gate
          below: acknowledge the risks, set hard limits, promote a strategy that proved
          itself, then arm the kill switch. You can stop instantly at any time.
        </p>
      </div>

      <Journey active="real" />

      <div className={`live-banner ${armed ? "armed" : "safe"}`}>
        <div>
          <strong>{armed ? "🔴 LIVE TRADING ARMED" : "🟢 LIVE TRADING DISARMED"}</strong>
          <span className="muted">
            {armed
              ? " Real orders will be sent to your Zerodha account."
              : " Real orders are blocked. This is the safe default."}
          </span>
        </div>
        {armed && (
          <button className="sell big" onClick={() => run(api.disarm, "Disarmed — real trading stopped.")}>
            ⏹ EMERGENCY STOP
          </button>
        )}
      </div>

      {!status.configured && (
        <div className="warn">
          Live trading is <strong>not configured</strong>. Add your Kite API keys to
          <code> backend/.env</code> and complete the daily login at
          <code> /auth/kite/login</code> first. You can still review the steps below.
        </div>
      )}

      {msg && <div className="ok">{msg}</div>}
      {err && <div className="error">{err}</div>}

      <Stepper status={status} />

      <Step1Acknowledge status={status} onChange={(s) => flash(setStatus)(s)} setErr={setErr} />
      <Step2Risk status={status} onSaved={(s) => run(async () => s, "Risk limits saved.")} setErr={setErr} />
      <Step3Promote
        status={status}
        instruments={instruments}
        templates={templates}
        onChange={refresh}
        setErr={setErr}
        setMsg={setMsg}
      />
      <Step4Arm status={status} run={run} />
      <Step5Order status={status} instruments={instruments} setErr={setErr} setMsg={setMsg} />

      <details className="panel">
        <summary>Full risk disclosure</summary>
        <RiskDisclosure />
      </details>

      <p className="disclaimer">
        Real-money trading can lose money rapidly. Not investment advice. See
        <code> docs/RISKS.md</code>.
      </p>
    </>
  );
}

function Stepper({ status }: { status: LiveStatus }) {
  const steps = [
    { label: "Configured", done: status.configured },
    { label: "Acknowledged", done: status.acknowledged },
    { label: "Strategy promoted", done: status.promoted.length > 0 },
    { label: "Armed", done: status.armed },
  ];
  return (
    <div className="stepper">
      {steps.map((s, i) => (
        <div key={i} className={`step ${s.done ? "done" : ""}`}>
          <span className="dot">{s.done ? "✓" : i + 1}</span>
          {s.label}
        </div>
      ))}
    </div>
  );
}

function Step1Acknowledge({
  status,
  onChange,
  setErr,
}: {
  status: LiveStatus;
  onChange: (s: LiveStatus) => void;
  setErr: (s: string) => void;
}) {
  const [checked, setChecked] = useState(false);
  return (
    <div className="panel">
      <h2>1 · Understand & acknowledge the risks</h2>
      <RiskDisclosure compact />
      {status.acknowledged ? (
        <p className="ok">✓ You have acknowledged the real-money risks.</p>
      ) : (
        <>
          <label className="check">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            I have read and understood all of the above. I accept full responsibility for
            real-money losses.
          </label>
          <button
            className="primary"
            disabled={!checked}
            onClick={() =>
              api.acknowledge().then(onChange).catch((e) => setErr(String(e.message ?? e)))
            }
          >
            I acknowledge the risks
          </button>
        </>
      )}
    </div>
  );
}

function Step2Risk({
  status,
  onSaved,
  setErr,
}: {
  status: LiveStatus;
  onSaved: (s: LiveStatus) => void;
  setErr: (s: string) => void;
}) {
  const [orderV, setOrderV] = useState(status.limits.max_order_value);
  const [posV, setPosV] = useState(status.limits.max_position_value);
  const [lossV, setLossV] = useState(status.limits.max_daily_loss);
  const [maxPos, setMaxPos] = useState(status.limits.max_open_positions);

  return (
    <div className="panel">
      <h2>2 · Set your safety limits</h2>
      <p className="muted">
        These caps are enforced on every real order. Start small. They cannot prevent
        losses on positions you already hold.
      </p>
      <div className="risk-grid">
        <Field label="Max per order (₹)" value={orderV} onChange={setOrderV} />
        <Field label="Max per position (₹)" value={posV} onChange={setPosV} />
        <Field label="Max daily loss (₹)" value={lossV} onChange={setLossV} />
        <Field label="Max open positions" value={String(maxPos)} onChange={(v) => setMaxPos(Number(v))} />
      </div>
      <button
        className="primary"
        onClick={() =>
          api
            .setRisk({
              max_order_value: Number(orderV),
              max_position_value: Number(posV),
              max_daily_loss: Number(lossV),
              max_open_positions: Number(maxPos),
            })
            .then(onSaved)
            .catch((e) => setErr(String(e.message ?? e)))
        }
      >
        Save limits
      </button>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label>{label}</label>
      <input type="number" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Step3Promote({
  status,
  instruments,
  templates,
  onChange,
  setErr,
  setMsg,
}: {
  status: LiveStatus;
  instruments: Instrument[];
  templates: Template[];
  onChange: () => void;
  setErr: (s: string) => void;
  setMsg: (s: string) => void;
}) {
  const [template, setTemplate] = useState("sma_crossover");
  const [token, setToken] = useState<number | null>(null);
  const [result, setResult] = useState<PromotionResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (token === null && instruments[0]) setToken(instruments[0].instrument_token);
  }, [instruments, token]);

  async function evaluate() {
    if (token === null) return;
    setBusy(true);
    setErr("");
    setResult(null);
    try {
      const bt = await api.backtest({ instrument_token: token, template, quantity: 50 });
      const res = await api.evaluate(bt.report);
      setResult(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  async function promote() {
    if (token === null) return;
    setErr("");
    try {
      const bt = await api.backtest({ instrument_token: token, template, quantity: 50 });
      await api.promote(template, bt.report);
      setMsg(`Strategy '${template}' promoted for real-money trading.`);
      onChange();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Promotion blocked");
    }
  }

  return (
    <div className="panel">
      <h2>3 · Earn real money — the promotion gate</h2>
      <p className="muted">
        A strategy must clear strict performance criteria on a backtest before it can be
        promoted to real-money automation. This is a discipline aid, not a guarantee of
        profit.
      </p>
      <div className="toolbar">
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
          <select value={token ?? ""} onChange={(e) => setToken(Number(e.target.value))}>
            {instruments.map((i) => (
              <option key={i.instrument_token} value={i.instrument_token}>
                {i.tradingsymbol}
              </option>
            ))}
          </select>
        </div>
        <button className="primary" disabled={busy} onClick={evaluate}>
          {busy ? "Testing…" : "Evaluate"}
        </button>
      </div>

      {result && (
        <>
          <ul className="checklist">
            {result.checks.map((c) => (
              <li key={c.name} className={c.passed ? "pass" : "fail"}>
                <span>{c.passed ? "✓" : "✗"}</span>
                <span className="cname">{c.name}</span>
                <span className="muted">
                  {c.actual === null ? "∞" : c.actual} (need {c.threshold})
                </span>
              </li>
            ))}
          </ul>
          {result.eligible ? (
            <button className="buy" onClick={promote}>
              Promote “{template}” to real money
            </button>
          ) : (
            <p className="muted">Not eligible yet — improve the strategy and re-test.</p>
          )}
        </>
      )}

      {status.promoted.length > 0 && (
        <p className="ok">Promoted: {status.promoted.join(", ")}</p>
      )}
    </div>
  );
}

function Step4Arm({
  status,
  run,
}: {
  status: LiveStatus;
  run: (fn: () => Promise<LiveStatus>, okMsg: string) => void;
}) {
  const canArm = status.configured && status.acknowledged && !status.armed;
  return (
    <div className="panel">
      <h2>4 · Arm live trading (kill switch)</h2>
      <p className="muted">
        Arming enables real orders. Disarming is the emergency stop and is always allowed.
        Arming requires configuration and acknowledgement.
      </p>
      {status.armed ? (
        <button className="sell big" onClick={() => run(api.disarm, "Disarmed.")}>
          ⏹ Disarm (stop real trading)
        </button>
      ) : (
        <button
          className="danger big"
          disabled={!canArm}
          onClick={() => {
            if (confirm("Enable REAL-MONEY trading? Real orders will be sent to Zerodha."))
              run(api.arm, "Armed — real trading enabled.");
          }}
        >
          ⚠ Arm real-money trading
        </button>
      )}
    </div>
  );
}

function Step5Order({
  status,
  instruments,
  setErr,
  setMsg,
}: {
  status: LiveStatus;
  instruments: Instrument[];
  setErr: (s: string) => void;
  setMsg: (s: string) => void;
}) {
  const [token, setToken] = useState<number | null>(null);
  const [qty, setQty] = useState(1);
  const [product, setProduct] = useState<PlaceOrder["product"]>("CNC");
  const [limit, setLimit] = useState("");

  useEffect(() => {
    if (token === null && instruments[0]) setToken(instruments[0].instrument_token);
  }, [instruments, token]);

  const enabled = status.configured && status.acknowledged && status.armed;

  async function place(side: "BUY" | "SELL") {
    if (token === null) return;
    if (!confirm(`Place a REAL ${side} order for ${qty}? This uses real money.`)) return;
    setErr("");
    setMsg("");
    try {
      const r = await api.placeLiveOrder({
        instrument_token: token,
        side,
        quantity: qty,
        order_type: limit ? "LIMIT" : "MARKET",
        product,
        limit_price: limit ? parseFloat(limit) : undefined,
      });
      setMsg(`Real order submitted: ${r.order_id} (${r.symbol})`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Order rejected");
    }
  }

  return (
    <div className={`panel real-ticket ${enabled ? "" : "locked"}`}>
      <h2>5 · Real-money order ticket</h2>
      {!enabled && (
        <p className="muted">
          Locked until configured, acknowledged, and armed (steps 1–4).
        </p>
      )}
      <div className="risk-grid">
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
          <label>Quantity</label>
          <input type="number" min={1} value={qty} onChange={(e) => setQty(Math.max(1, Number(e.target.value)))} />
        </div>
        <div>
          <label>Product</label>
          <select value={product} onChange={(e) => setProduct(e.target.value as PlaceOrder["product"])}>
            <option value="CNC">CNC (delivery)</option>
            <option value="MIS">MIS (intraday)</option>
          </select>
        </div>
        <div>
          <label>Limit (blank = market)</label>
          <input type="number" value={limit} onChange={(e) => setLimit(e.target.value)} />
        </div>
      </div>
      <div className="btns">
        <button className="buy" disabled={!enabled} onClick={() => place("BUY")}>
          REAL Buy
        </button>
        <button className="sell" disabled={!enabled} onClick={() => place("SELL")}>
          REAL Sell
        </button>
      </div>
    </div>
  );
}
