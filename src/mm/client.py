"""Async Orderly API client"""
import asyncio
import base64
import json
import time
from typing import Any, Optional

import aiohttp
import base58
import nacl.signing


class OrderlyClient:
    """Simple async client for Orderly API"""

    def __init__(self, base_url: str, account_id: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip("/")
        self.account_id = account_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _sign(self, timestamp: int, method: str, path: str, body: str = "") -> str:
        """Sign request with ed25519"""
        message = f"{timestamp}{method.upper()}{path}{body}"

        secret_key = self.api_secret.replace("ed25519:", "")
        seed = base58.b58decode(secret_key)
        signing_key = nacl.signing.SigningKey(seed)
        signature = signing_key.sign(message.encode()).signature

        return base64.urlsafe_b64encode(signature).decode()

    def _headers(self, method: str, path: str, body: str = "") -> dict:
        """Generate request headers"""
        timestamp = int(time.time() * 1000)
        signature = self._sign(timestamp, method, path, body)

        headers = {
            "orderly-account-id": self.account_id,
            "orderly-key": self.api_key,
            "orderly-signature": signature,
            "orderly-timestamp": str(timestamp),
        }

        # Set Content-Type based on method
        if method.upper() in ["POST", "PUT"]:
            headers["Content-Type"] = "application/json"
        elif method.upper() in ["DELETE"]:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        return headers

    async def get_mark_price(self, symbol: str) -> float:
        """Get current mark price"""
        url = f"{self.base_url}/v1/public/futures/{symbol}"
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()

            # Handle different response formats
            if "data" in data:
                if "rows" in data["data"] and data["data"]["rows"]:
                    return float(data["data"]["rows"][0]["mark_price"])
                elif "mark_price" in data["data"]:
                    return float(data["data"]["mark_price"])

            raise ValueError(f"Could not find mark_price in response: {data}")

    async def get_market_info(self, symbol: str) -> dict:
        """Get market info (tick sizes, etc)"""
        url = f"{self.base_url}/v1/public/info/{symbol}"
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["data"]

    async def get_open_orders(self, symbol: str) -> list[dict]:
        """Get open orders - returns all non-filled orders"""
        # Remove status filter to get all orders, then filter by status
        path = f"/v1/orders?symbol={symbol}"
        headers = self._headers("GET", path)

        url = f"{self.base_url}{path}"
        async with self.session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            rows = data.get("data", {}).get("rows", [])
            # Filter for orders that are not FILLED or CANCELLED
            return [
                r for r in rows
                if r.get("status") not in ["FILLED", "CANCELLED", "REJECTED", "PARTIAL_FILLED"]
            ]

    async def get_position(self, symbol: str) -> dict:
        """Get current position for a symbol"""
        path = f"/v1/position/{symbol}"
        headers = self._headers("GET", path)

        url = f"{self.base_url}{path}"
        async with self.session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", {})

    async def create_order(self, symbol: str, side: str, price: float, quantity: float) -> dict:
        """Create a POST_ONLY limit order"""
        path = "/v1/order"
        payload = {
            "symbol": symbol,
            "order_type": "LIMIT",
            "side": side,
            "order_price": price,
            "order_quantity": quantity,
        }
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._headers("POST", path, body)

        url = f"{self.base_url}{path}"
        async with self.session.post(url, data=body, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def cancel_order(self, order_id: int, symbol: str) -> None:
        """Cancel an order"""
        path = f"/v1/order?order_id={order_id}&symbol={symbol}"
        headers = self._headers("DELETE", path)

        url = f"{self.base_url}{path}"
        async with self.session.delete(url, headers=headers) as resp:
            resp.raise_for_status()

    async def cancel_batch(self, order_ids: list[int], symbol: str) -> None:
        """Cancel multiple orders by their IDs (max 10 per request)"""
        if not order_ids:
            return

        # Take max 10 orders per batch
        order_ids = order_ids[:10]
        ids_str = ",".join(str(oid) for oid in order_ids)

        # Try without symbol parameter
        path = f"/v1/batch-order?order_ids={ids_str}"
        headers = self._headers("DELETE", path)

        url = f"{self.base_url}{path}"
        async with self.session.delete(url, headers=headers) as resp:
            resp.raise_for_status()

    async def cancel_all(self, symbol: str) -> None:
        """Cancel all open orders for a symbol"""
        orders = await self.get_open_orders(symbol)
        if not orders:
            return

        # Cancel all orders individually
        cancel_tasks = [
            self.cancel_order(order["order_id"], symbol)
            for order in orders
            if "order_id" in order
        ]
        await asyncio.gather(*cancel_tasks, return_exceptions=True)
