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

// --- Analysis ---

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type Series = (number | null)[];

export interface Indicators {
  instrument_token: number;
  timestamps: string[];
  close: number[];
  sma20: Series;
  sma50: Series;
  ema20: Series;
  rsi14: Series;
  macd: Series;
  macd_signal: Series;
  macd_hist: Series;
  boll_upper: Series;
  boll_mid: Series;
  boll_lower: Series;
}

export interface ScanHit {
  instrument_token: number;
  tradingsymbol: string;
  detail: Record<string, number>;
}

export interface ScreenerResult {
  scan: string;
  available_scans: string[];
  hits: ScanHit[];
}

// --- Strategy / backtest ---

export interface Template {
  id: string;
  name: string;
  description: string;
  config: Record<string, unknown>;
}

export interface ReportCard {
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  num_trades: number;
  win_rate: number;
  profit_factor: number | null;
  expectancy: number;
  avg_win: number;
  avg_loss: number;
  max_drawdown_pct: number;
  sharpe: number;
  total_charges: number;
}

export interface BacktestResult {
  strategy: string;
  report: ReportCard;
  equity_curve: { timestamp: string; equity: number }[];
  trades: {
    timestamp: string;
    side: string;
    quantity: number;
    price: string;
    charges: string;
  }[];
  warmup: number;
}

export interface BacktestRequest {
  instrument_token: number;
  template?: string;
  config?: Record<string, unknown>;
  quantity?: number;
  initial_capital?: number;
  product?: "MIS" | "CNC";
  candle_count?: number;
  interval_minutes?: number;
  warmup?: number;
}

// --- Live trading / risk / promotion ---

export interface RiskLimitsDto {
  max_order_value: string;
  max_position_value: string;
  max_daily_loss: string;
  max_open_positions: number;
}

export interface LiveStatus {
  configured: boolean;
  acknowledged: boolean;
  armed: boolean;
  promoted: string[];
  daily_loss: string;
  limits: RiskLimitsDto;
  mock_mode: boolean;
}

export interface PromotionCheck {
  name: string;
  passed: boolean;
  actual: number | null;
  threshold: number;
  detail: string;
}

export interface PromotionResult {
  eligible: boolean;
  checks: PromotionCheck[];
}

export interface Alert {
  id: number;
  instrument_token: number;
  tradingsymbol: string;
  op: ">" | "<";
  price: string;
  note: string;
  active: boolean;
  triggered_at: string | null;
  triggered_price: string | null;
}

export interface JournalEntry {
  id: number;
  text: string;
  tags: string[];
  created_at: string;
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

  candles: (token: number, count = 300, interval = 5) =>
    fetch(
      `${API_URL}/analysis/candles/${token}?count=${count}&interval_minutes=${interval}`,
    ).then(json<{ candles: Candle[] }>),
  indicators: (token: number, count = 300, interval = 5) =>
    fetch(
      `${API_URL}/analysis/indicators/${token}?count=${count}&interval_minutes=${interval}`,
    ).then(json<Indicators>),
  screener: (scan: string) =>
    fetch(`${API_URL}/analysis/screener?scan=${scan}`).then(json<ScreenerResult>),

  templates: () =>
    fetch(`${API_URL}/strategy/templates`).then(json<{ templates: Template[] }>),
  backtest: (payload: BacktestRequest) =>
    fetch(`${API_URL}/strategy/backtest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<BacktestResult>),

  aiCommentary: (token: number) =>
    fetch(`${API_URL}/ai/commentary/${token}`).then(
      json<{ symbol: string; commentary: string }>,
    ),
  aiStrategy: (prompt: string) =>
    fetch(`${API_URL}/ai/strategy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    }).then(json<{ config: Record<string, unknown> }>),
  aiCoach: () => fetch(`${API_URL}/ai/coach`).then(json<{ coaching: string }>),
  aiReview: () => fetch(`${API_URL}/ai/review`).then(json<{ review: string }>),

  // Live trading
  liveStatus: () => fetch(`${API_URL}/live/status`).then(json<LiveStatus>),
  liveCriteria: () =>
    fetch(`${API_URL}/live/criteria`).then(json<Record<string, number>>),
  acknowledge: () =>
    fetch(`${API_URL}/live/acknowledge`, { method: "POST" }).then(json<LiveStatus>),
  arm: () => fetch(`${API_URL}/live/arm`, { method: "POST" }).then(json<LiveStatus>),
  disarm: () =>
    fetch(`${API_URL}/live/disarm`, { method: "POST" }).then(json<LiveStatus>),
  setRisk: (limits: {
    max_order_value: number;
    max_position_value: number;
    max_daily_loss: number;
    max_open_positions: number;
  }) =>
    fetch(`${API_URL}/live/risk`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(limits),
    }).then(json<LiveStatus>),
  evaluate: (report: ReportCard) =>
    fetch(`${API_URL}/live/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report }),
    }).then(json<PromotionResult>),
  promote: (strategy_id: string, report: ReportCard) =>
    fetch(`${API_URL}/live/promote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategy_id, report }),
    }).then(json<LiveStatus & { promoted: string[] }>),
  placeLiveOrder: (payload: PlaceOrder & { strategy_id?: string }) =>
    fetch(`${API_URL}/live/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<{ order_id: string; status: string; symbol: string }>),

  // Alerts
  alerts: () =>
    fetch(`${API_URL}/alerts`).then(json<{ alerts: Alert[]; triggered: Alert[] }>),
  addAlert: (payload: { instrument_token: number; op: ">" | "<"; price: number; note?: string }) =>
    fetch(`${API_URL}/alerts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<Alert>),
  removeAlert: (id: number) =>
    fetch(`${API_URL}/alerts/${id}`, { method: "DELETE" }).then(json<{ removed: number }>),

  // Journal
  journal: () => fetch(`${API_URL}/journal`).then(json<{ entries: JournalEntry[] }>),
  addJournal: (text: string, tags: string[] = []) =>
    fetch(`${API_URL}/journal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, tags }),
    }).then(json<JournalEntry>),
};
