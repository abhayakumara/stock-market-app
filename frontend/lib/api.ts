// Minimal typed client for the trading backend.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function wsUrl(path: string): string {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}${path}`;
}

export interface Instrument {
  instrument_token: number;
  tradingsymbol: string;
  name: string;
  exchange: string;
  last_price: string | null;
}

export interface Position {
  instrument_token: number;
  tradingsymbol: string;
  net_quantity: number;
  average_price: string;
  last_price: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_charges: string;
}

export interface Account {
  cash: string;
  equity: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_charges: string;
}

export interface Order {
  order_id: string;
  tradingsymbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  filled_quantity: number;
  order_type: string;
  product: string;
  status: string;
  average_price: string | null;
  reject_reason: string;
}

export interface PlaceOrder {
  instrument_token: number;
  side: "BUY" | "SELL";
  quantity: number;
  order_type: "MARKET" | "LIMIT" | "SL" | "SL-M";
  product: "MIS" | "CNC" | "NRML";
  limit_price?: number;
  trigger_price?: number;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  instruments: () => fetch(`${API_URL}/instruments`).then(json<Instrument[]>),
  positions: () => fetch(`${API_URL}/paper/positions`).then(json<Position[]>),
  account: () => fetch(`${API_URL}/paper/account`).then(json<Account>),
  orders: () => fetch(`${API_URL}/paper/orders`).then(json<Order[]>),
  placeOrder: (payload: PlaceOrder) =>
    fetch(`${API_URL}/paper/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<Order>),
};
