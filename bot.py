"""
bot.py
Simplified Binance Futures (USDT-M) trading bot using REST calls to testnet.
Implements: market, limit, stop-limit (bonus).
"""

import os
import time
import hmac
import hashlib
import logging
import requests
from urllib.parse import urlencode

# Read env vars (you can also import from dotenv)
API_KEY = os.environ.get("BINANCE_API_KEY")
API_SECRET = os.environ.get("BINANCE_API_SECRET")

# Testnet base URL for Binance Futures (USDT-M)
BASE_URL = "https://testnet.binancefuture.com"

# Logging setup (module-level)
logger = logging.getLogger("BasicBot")
logger.setLevel(logging.DEBUG)
_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

_console = logging.StreamHandler()
_console.setFormatter(_formatter)
logger.addHandler(_console)

_file = logging.FileHandler("bot_logs.log")
_file.setFormatter(_formatter)
logger.addHandler(_file)


class BasicBot:
    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL, recv_window: int = 5000):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must be provided.")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})
        logger.info("BasicBot initialized")

    def _sign(self, params: dict) -> str:
        """Return signature string for params dict (query string)"""
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature

    def _post(self, path: str, params: dict):
        url = f"{self.base_url}{path}"
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        params["signature"] = self._sign(params)
        logger.debug("REQUEST POST %s?%s", url, urlencode({k: v for k, v in params.items() if k != "signature"}))
        try:
            resp = self.session.post(url, params=params, timeout=10)
            logger.debug("STATUS %s | RESPONSE %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.exception("Request failed: %s", str(e))
            raise

    def place_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False):
        """
        Place a market order on futures endpoint:
        side: BUY or SELL
        """
        path = "/fapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),  # BUY or SELL
            "type": "MARKET",
            "quantity": float(quantity),
            "reduceOnly": str(reduce_only).lower(),  # lowercase 'true'/'false'
        }
        logger.info("Placing MARKET order: %s %s %s", side, quantity, symbol)
        return self._post(path, params)

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float, time_in_force: str = "GTC"):
        """
        Place a limit order:
        time_in_force: GTC / IOC / FOK
        """
        path = "/fapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": float(quantity),
            "price": float(price),
            "timeInForce": time_in_force,
        }
        logger.info("Placing LIMIT order: %s %s %s @ %s", side, quantity, symbol, price)
        return self._post(path, params)

    def place_stop_limit_order(self, symbol: str, side: str, quantity: float, stop_price: float, limit_price: float, time_in_force: str = "GTC"):
        """
        Stop-Limit: trigger at stop_price, place a LIMIT at limit_price.
        For Futures this uses type=STOP and closePosition false (or type=STOP_MARKET for stop-market).
        We'll implement using stopPrice and type=STOP (the behavior depends on API flags).
        """
        path = "/fapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "STOP",
            "quantity": float(quantity),
            "price": float(limit_price),
            "stopPrice": float(stop_price),
            "timeInForce": time_in_force,
        }
        logger.info("Placing STOP-LIMIT order: %s %s %s stop=%s limit=%s", side, quantity, symbol, stop_price, limit_price)
        return self._post(path, params)

    # Utility: get account/futures position (optional)
    def get_account_info(self):
        path = "/fapi/v2/account"
        params = {"timestamp": int(time.time() * 1000), "recvWindow": self.recv_window}
        params["signature"] = self._sign(params)
        url = f"{self.base_url}{path}"
        logger.debug("REQUEST GET %s?%s", url, urlencode({k: v for k, v in params.items() if k != "signature"}))
        try:
            resp = self.session.get(url, params=params, timeout=10)
            logger.debug("STATUS %s | RESPONSE %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.exception("Failed to fetch account info: %s", e)
            raise
