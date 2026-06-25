"""Zerodha Kite Connect integration (auth, REST, ticker).

The ``kiteconnect`` package is an *optional* dependency (``pip install
trading-backend[kite]``) so the core engine installs without it. Modules here import it
lazily.
"""

from .auth import KiteAuth

__all__ = ["KiteAuth"]
