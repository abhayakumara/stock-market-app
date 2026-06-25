"""Market analysis: technical indicators, candle aggregation, and screeners.

Indicators operate on plain ``float`` series (precision is not money-critical here and
floats keep the math fast and dependency-free). Candle OHLC values are kept as ``float``
for the same reason; order prices in the trading engine remain ``Decimal``.
"""
