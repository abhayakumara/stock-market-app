"use client";

import { Candle, Series } from "@/lib/api";

const W = 1000;

interface Overlay {
  name: string;
  color: string;
  data: Series;
}

function extent(values: number[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of values) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (!isFinite(lo) || !isFinite(hi)) return [0, 1];
  if (lo === hi) return [lo - 1, hi + 1];
  return [lo, hi];
}

function linePath(
  data: Series,
  n: number,
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  let d = "";
  let started = false;
  for (let i = 0; i < n; i++) {
    const v = data[i];
    if (v === null || v === undefined) {
      started = false;
      continue;
    }
    d += `${started ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    started = true;
  }
  return d;
}

/** SVG candlestick chart with optional overlay lines (SMA/EMA/Bollinger). */
export function CandleChart({
  candles,
  overlays = [],
  height = 360,
}: {
  candles: Candle[];
  overlays?: Overlay[];
  height?: number;
}) {
  if (candles.length === 0) return <div className="chart-empty">No data</div>;
  const pad = { top: 10, right: 8, bottom: 18, left: 8 };
  const innerW = W - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const n = candles.length;

  const overlayVals = overlays.flatMap((o) =>
    o.data.filter((v): v is number => v !== null && v !== undefined),
  );
  const [lo, hi] = extent([
    ...candles.map((c) => c.low),
    ...candles.map((c) => c.high),
    ...overlayVals,
  ]);

  const x = (i: number) => pad.left + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const y = (v: number) => pad.top + ((hi - v) / (hi - lo)) * innerH;
  const bw = Math.max(1, (innerW / n) * 0.6);

  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="chart" preserveAspectRatio="none">
      {[0.25, 0.5, 0.75].map((f) => (
        <line
          key={f}
          x1={pad.left}
          x2={W - pad.right}
          y1={pad.top + f * innerH}
          y2={pad.top + f * innerH}
          className="grid"
        />
      ))}
      {candles.map((c, i) => {
        const up = c.close >= c.open;
        const color = up ? "var(--green)" : "var(--red)";
        const cx = x(i);
        return (
          <g key={i}>
            <line x1={cx} x2={cx} y1={y(c.high)} y2={y(c.low)} stroke={color} strokeWidth={1} />
            <rect
              x={cx - bw / 2}
              width={bw}
              y={y(Math.max(c.open, c.close))}
              height={Math.max(1, Math.abs(y(c.open) - y(c.close)))}
              fill={color}
            />
          </g>
        );
      })}
      {overlays.map((o) => (
        <path
          key={o.name}
          d={linePath(o.data, n, x, y)}
          fill="none"
          stroke={o.color}
          strokeWidth={1.4}
        />
      ))}
    </svg>
  );
}

/** RSI subchart with 30/70 reference bands. */
export function RSIChart({ rsi, height = 110 }: { rsi: Series; height?: number }) {
  const pad = { top: 8, right: 8, bottom: 14, left: 8 };
  const innerW = W - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const n = rsi.length;
  const x = (i: number) => pad.left + (n <= 1 ? 0 : (i / (n - 1)) * innerW);
  const y = (v: number) => pad.top + ((100 - v) / 100) * innerH;
  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="chart" preserveAspectRatio="none">
      {[30, 50, 70].map((lvl) => (
        <line
          key={lvl}
          x1={pad.left}
          x2={W - pad.right}
          y1={y(lvl)}
          y2={y(lvl)}
          className={lvl === 50 ? "grid" : "grid band"}
        />
      ))}
      <path d={linePath(rsi, n, x, y)} fill="none" stroke="var(--accent)" strokeWidth={1.4} />
    </svg>
  );
}

/** Simple equity / line chart. */
export function LineChart({
  values,
  height = 260,
  color = "var(--accent)",
  baseline,
}: {
  values: number[];
  height?: number;
  color?: string;
  baseline?: number;
}) {
  if (values.length === 0) return <div className="chart-empty">No data</div>;
  const pad = { top: 10, right: 8, bottom: 16, left: 8 };
  const innerW = W - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const n = values.length;
  const all = baseline !== undefined ? [...values, baseline] : values;
  const [lo, hi] = extent(all);
  const x = (i: number) => pad.left + (n <= 1 ? 0 : (i / (n - 1)) * innerW);
  const y = (v: number) => pad.top + ((hi - v) / (hi - lo)) * innerH;
  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="chart" preserveAspectRatio="none">
      {baseline !== undefined && (
        <line x1={pad.left} x2={W - pad.right} y1={y(baseline)} y2={y(baseline)} className="grid" />
      )}
      <path d={linePath(values, n, x, y)} fill="none" stroke={color} strokeWidth={1.6} />
    </svg>
  );
}
