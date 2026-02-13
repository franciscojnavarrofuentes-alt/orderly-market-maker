"""Test different cancel endpoints"""
import asyncio
import sys
sys.path.insert(0, 'src')

from mm.config import load_config
from mm.client import OrderlyClient


async def test_cancel_endpoint(client, order_id, symbol, endpoint_path):
    """Test a specific cancel endpoint"""
    print(f"\nTesting: {endpoint_path}")
    try:
        headers = client._headers("DELETE", endpoint_path)
        url = f"{client.base_url}{endpoint_path}"

        async with client.session.delete(url, headers=headers) as resp:
            print(f"  Status: {resp.status}")
            text = await resp.text()
            print(f"  Response: {text[:200]}")
            return resp.status == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def main():
    config = load_config()

    async with OrderlyClient(
        config.base_url,
        config.account_id,
        config.api_key,
        config.api_secret
    ) as client:
        # Get first open order
        orders = await client.get_open_orders(config.symbol)
        if not orders:
            print("No orders to test with")
            return

        order_id = orders[0]['order_id']
        print(f"Testing cancellation of order: {order_id}")

        # Try different endpoint formats
        endpoints = [
            f"/v1/order?order_id={order_id}",
            f"/v1/order?order_id={order_id}&symbol={config.symbol}",
            f"/v1/order?symbol={config.symbol}&order_id={order_id}",
            f"/v1/client/order?order_id={order_id}",
            f"/v1/orders/{order_id}",
        ]

        for endpoint in endpoints:
            success = await test_cancel_endpoint(client, order_id, config.symbol, endpoint)
            if success:
                print(f"✓ SUCCESS with: {endpoint}")
                break
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
