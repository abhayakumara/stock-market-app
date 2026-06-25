"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Account,
  Instrument,
  Order,
  PlaceOrder,
  Position,
  api,
  wsUrl,
} from "@/lib/api";

type Prices = Record<number, string>;

function money(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const n = typeof v === "string" ? parseFloat(v) : v;
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function pnlClass(v: string): string {
  return parseFloat(v) >= 0 ? "pos" : "neg";
}

export default function Dashboard() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [prices, setPrices] = useState<Prices>({});
  const [positions, setPositions] = useState<Position[]>([]);
  const [account, setAccount] = useState<Account | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [selected, setSelected] = useState<Instrument | null>(null);
  const [error, setError] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);

  // Initial load.
  useEffect(() => {
    api.instruments().then((xs) => {
      setInstruments(xs);
      setSelected((s) => s ?? xs[0] ?? null);
    });
  }, []);

  // Live ticks over WebSocket.
  useEffect(() => {
    const ws = new WebSocket(wsUrl("/ws/ticks"));
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      const t = JSON.parse(ev.data) as {
        instrument_token: number;
        last_price: string;
      };
      setPrices((p) => ({ ...p, [t.instrument_token]: t.last_price }));
    };
    return () => ws.close();
  }, []);

  // Poll account / positions / orders.
  const refresh = useCallback(() => {
    api.account().then(setAccount).catch(() => {});
    api.positions().then(setPositions).catch(() => {});
    api.orders().then(setOrders).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <>
      {account && (
        <div className="panel">
          <div className="stats">
            <div className="stat">
              <div className="label">Equity</div>
              <div className="value">{money(account.equity)}</div>
            </div>
            <div className="stat">
              <div className="label">Cash</div>
              <div className="value">{money(account.cash)}</div>
            </div>
            <div className="stat">
              <div className="label">Realized P&L</div>
              <div className={`value ${pnlClass(account.realized_pnl)}`}>
                {money(account.realized_pnl)}
              </div>
            </div>
            <div className="stat">
              <div className="label">Unrealized P&L</div>
              <div className={`value ${pnlClass(account.unrealized_pnl)}`}>
                {money(account.unrealized_pnl)}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid">
        <div>
          <Watchlist
            instruments={instruments}
            prices={prices}
            onSelect={setSelected}
          />
          <Positions positions={positions} prices={prices} />
          <Orders orders={orders} />
        </div>
        <div>
          <OrderTicket
            instrument={selected}
            onPlaced={() => {
              setError("");
              refresh();
            }}
            onError={setError}
          />
          {error && <div className="error">{error}</div>}
        </div>
      </div>

      <p className="disclaimer">
        For education and research only. Not investment advice. Trading involves
        risk of loss.
      </p>
    </>
  );
}

function Watchlist({
  instruments,
  prices,
  onSelect,
}: {
  instruments: Instrument[];
  prices: Prices;
  onSelect: (i: Instrument) => void;
}) {
  return (
    <div className="panel">
      <h2>Watchlist</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Exchange</th>
            <th>LTP</th>
          </tr>
        </thead>
        <tbody>
          {instruments.map((i) => (
            <tr
              key={i.instrument_token}
              className="selectable"
              onClick={() => onSelect(i)}
            >
              <td>{i.tradingsymbol}</td>
              <td>{i.exchange}</td>
              <td>{money(prices[i.instrument_token] ?? i.last_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Positions({
  positions,
  prices,
}: {
  positions: Position[];
  prices: Prices;
}) {
  return (
    <div className="panel">
      <h2>Positions</h2>
      {positions.length === 0 ? (
        <p style={{ color: "var(--muted)", fontSize: 14 }}>No open positions.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Qty</th>
              <th>Avg</th>
              <th>LTP</th>
              <th>P&L</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.instrument_token}>
                <td>{p.tradingsymbol}</td>
                <td>{p.net_quantity}</td>
                <td>{money(p.average_price)}</td>
                <td>{money(prices[p.instrument_token] ?? p.last_price)}</td>
                <td className={pnlClass(p.unrealized_pnl)}>
                  {money(p.unrealized_pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Orders({ orders }: { orders: Order[] }) {
  if (orders.length === 0) return null;
  return (
    <div className="panel">
      <h2>Orders</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Type</th>
            <th>Status</th>
            <th>Avg</th>
          </tr>
        </thead>
        <tbody>
          {orders
            .slice()
            .reverse()
            .map((o) => (
              <tr key={o.order_id}>
                <td>{o.tradingsymbol}</td>
                <td className={o.side === "BUY" ? "pos" : "neg"}>{o.side}</td>
                <td>{o.quantity}</td>
                <td>{o.order_type}</td>
                <td>{o.status}</td>
                <td>{money(o.average_price)}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function OrderTicket({
  instrument,
  onPlaced,
  onError,
}: {
  instrument: Instrument | null;
  onPlaced: () => void;
  onError: (msg: string) => void;
}) {
  const [quantity, setQuantity] = useState(1);
  const [orderType, setOrderType] = useState<PlaceOrder["order_type"]>("MARKET");
  const [product, setProduct] = useState<PlaceOrder["product"]>("MIS");
  const [limitPrice, setLimitPrice] = useState("");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [busy, setBusy] = useState(false);

  const needsLimit = orderType === "LIMIT" || orderType === "SL";
  const needsTrigger = orderType === "SL" || orderType === "SL-M";

  async function submit(side: "BUY" | "SELL") {
    if (!instrument) return;
    setBusy(true);
    try {
      await api.placeOrder({
        instrument_token: instrument.instrument_token,
        side,
        quantity,
        order_type: orderType,
        product,
        limit_price: needsLimit ? parseFloat(limitPrice) : undefined,
        trigger_price: needsTrigger ? parseFloat(triggerPrice) : undefined,
      });
      onPlaced();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Order failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2>Order Ticket</h2>
      <form className="ticket" onSubmit={(e) => e.preventDefault()}>
        <label>Instrument</label>
        <input value={instrument?.tradingsymbol ?? ""} readOnly />

        <div className="row2">
          <div>
            <label>Quantity</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
            />
          </div>
          <div>
            <label>Product</label>
            <select
              value={product}
              onChange={(e) =>
                setProduct(e.target.value as PlaceOrder["product"])
              }
            >
              <option value="MIS">MIS (intraday)</option>
              <option value="CNC">CNC (delivery)</option>
            </select>
          </div>
        </div>

        <label>Order type</label>
        <select
          value={orderType}
          onChange={(e) =>
            setOrderType(e.target.value as PlaceOrder["order_type"])
          }
        >
          <option value="MARKET">Market</option>
          <option value="LIMIT">Limit</option>
          <option value="SL">Stop-loss (SL)</option>
          <option value="SL-M">Stop-loss market (SL-M)</option>
        </select>

        {needsLimit && (
          <>
            <label>Limit price</label>
            <input
              type="number"
              value={limitPrice}
              onChange={(e) => setLimitPrice(e.target.value)}
            />
          </>
        )}
        {needsTrigger && (
          <>
            <label>Trigger price</label>
            <input
              type="number"
              value={triggerPrice}
              onChange={(e) => setTriggerPrice(e.target.value)}
            />
          </>
        )}

        <div className="btns">
          <button
            type="button"
            className="buy"
            disabled={busy || !instrument}
            onClick={() => submit("BUY")}
          >
            Buy
          </button>
          <button
            type="button"
            className="sell"
            disabled={busy || !instrument}
            onClick={() => submit("SELL")}
          >
            Sell
          </button>
        </div>
      </form>
    </div>
  );
}
