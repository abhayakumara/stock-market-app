"""Kite Connect login flow.

Kite uses an interactive OAuth-like login: redirect the user to the Kite login URL, they
authorize, Kite redirects back with a ``request_token``, which we exchange (with the API
secret) for an ``access_token``. **Access tokens expire daily (~6 AM IST)**, so this flow
must be repeated each trading day — there is no fully headless token generation.

The access token must be encrypted at rest; here we only return it. Persisting it
(encrypted, per user) is handled by the storage layer in a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KiteSession:
    access_token: str
    user_id: str
    user_name: str = ""


class KiteAuth:
    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("KITE_API_KEY and KITE_API_SECRET must be configured")
        self.api_key = api_key
        self.api_secret = api_secret

    def login_url(self) -> str:
        """The URL to send the user to in order to begin login."""
        from kiteconnect import KiteConnect  # lazy optional import

        return KiteConnect(api_key=self.api_key).login_url()

    def exchange_request_token(self, request_token: str) -> KiteSession:
        """Exchange the ``request_token`` from the redirect for a daily access token."""
        from kiteconnect import KiteConnect

        kite = KiteConnect(api_key=self.api_key)
        data = kite.generate_session(request_token, api_secret=self.api_secret)
        return KiteSession(
            access_token=data["access_token"],
            user_id=data.get("user_id", ""),
            user_name=data.get("user_name", ""),
        )
