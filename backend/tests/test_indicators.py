from app.analysis import indicators as ind


def test_sma_padding_and_values():
    out = ind.sma([1, 2, 3, 4, 5], 3)
    assert out == [None, None, 2.0, 3.0, 4.0]


def test_ema_seeds_with_sma():
    out = ind.ema([1, 2, 3, 4, 5], 3)
    # seed at index 2 = (1+2+3)/3 = 2; k = 0.5 thereafter
    assert out[:2] == [None, None]
    assert out[2] == 2.0
    assert out[3] == 3.0
    assert out[4] == 4.0


def test_rsi_uptrend_is_100_downtrend_near_zero():
    up = ind.rsi(list(range(1, 30)), 14)
    assert up[-1] == 100.0
    down = ind.rsi(list(range(30, 1, -1)), 14)
    assert down[-1] is not None and down[-1] < 1.0


def test_rsi_bounds():
    values = [10, 11, 10.5, 12, 11.5, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18]
    out = ind.rsi(values, 14)
    for v in out:
        if v is not None:
            assert 0.0 <= v <= 100.0


def test_macd_histogram_consistency():
    values = [float(x) for x in range(1, 60)]
    macd_line, signal_line, hist = ind.macd(values)
    for m, s, h in zip(macd_line, signal_line, hist, strict=True):
        if m is not None and s is not None:
            assert abs(h - (m - s)) < 1e-9


def test_bollinger_constant_series_has_zero_width():
    mid, upper, lower = ind.bollinger([5.0] * 25, period=20)
    assert mid[-1] == 5.0
    assert upper[-1] == 5.0
    assert lower[-1] == 5.0


def test_bollinger_orders_bands():
    values = [float(x % 7) for x in range(40)]
    mid, upper, lower = ind.bollinger(values, period=20)
    for m, u, low in zip(mid, upper, lower, strict=True):
        if m is not None:
            assert low <= m <= u


def test_atr_positive_when_defined():
    highs = [float(10 + (i % 3)) for i in range(30)]
    lows = [float(8 + (i % 2)) for i in range(30)]
    closes = [float(9 + (i % 3)) for i in range(30)]
    out = ind.atr(highs, lows, closes, 14)
    assert out[-1] is not None and out[-1] > 0


def test_vwap_single_bar_equals_typical_price():
    out = ind.vwap([12.0], [8.0], [10.0], [100.0])
    assert out[0] == (12.0 + 8.0 + 10.0) / 3
