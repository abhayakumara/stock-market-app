"""Technical indicators implemented in pure Python (no numpy/pandas dependency).

Every function returns a list the **same length** as its input, left-padded with ``None``
until the indicator has enough data. This makes series trivially alignable with the
candle list they were derived from (index *i* of the output corresponds to candle *i*).
"""

from __future__ import annotations

Series = list[float | None]


def sma(values: list[float], period: int) -> Series:
    """Simple moving average."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    window = sum(values[:period])
    out[period - 1] = window / period
    for i in range(period, len(values)):
        window += values[i] - values[i - period]
        out[i] = window / period
    return out


def ema(values: list[float], period: int) -> Series:
    """Exponential moving average. Seeded with the SMA of the first ``period`` values."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(values: list[float], period: int = 14) -> Series:
    """Wilder's Relative Strength Index."""
    out: Series = [None] * len(values)
    if len(values) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[Series, Series, Series]:
    """MACD line, signal line, and histogram."""
    fast_e = ema(values, fast)
    slow_e = ema(values, slow)
    macd_line: Series = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(fast_e, slow_e, strict=True)
    ]
    # Signal line is an EMA of the (defined portion of the) MACD line.
    defined = [v for v in macd_line if v is not None]
    sig_defined = ema(defined, signal)
    signal_line: Series = [None] * len(macd_line)
    j = 0
    for i, v in enumerate(macd_line):
        if v is None:
            continue
        signal_line[i] = sig_defined[j]
        j += 1
    hist: Series = [
        (m - s) if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line, strict=True)
    ]
    return macd_line, signal_line, hist


def bollinger(
    values: list[float], period: int = 20, mult: float = 2.0
) -> tuple[Series, Series, Series]:
    """Bollinger Bands: (middle SMA, upper, lower)."""
    mid = sma(values, period)
    upper: Series = [None] * len(values)
    lower: Series = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        m = mid[i]
        assert m is not None
        variance = sum((x - m) ** 2 for x in window) / period
        sd = variance**0.5
        upper[i] = m + mult * sd
        lower[i] = m - mult * sd
    return mid, upper, lower


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Series:
    """Average True Range (Wilder's smoothing)."""
    n = len(closes)
    out: Series = [None] * n
    if n <= period:
        return out
    trs: list[float] = [highs[0] - lows[0]]
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    prev = sum(trs[1 : period + 1]) / period
    out[period] = prev
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + trs[i]) / period
        out[i] = prev
    return out


def vwap(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> Series:
    """Cumulative Volume-Weighted Average Price over the supplied window."""
    out: Series = [None] * len(closes)
    cum_pv = 0.0
    cum_v = 0.0
    for i in range(len(closes)):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += typical * volumes[i]
        cum_v += volumes[i]
        out[i] = cum_pv / cum_v if cum_v > 0 else None
    return out
