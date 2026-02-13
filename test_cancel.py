"""Test cancel order functionality"""
import asyncio
import sys
sys.path.insert(0, 'src')

from mm.config import load_config
from mm.client import OrderlyClient


async def main():
    config = load_config()

    async with OrderlyClient(
        config.base_url,
        config.account_id,
        config.api_key,
        config.api_secret
    ) as client:
        # Get open orders
        print("Fetching open orders...")
        orders = await client.get_open_orders(config.symbol)
        print(f"Found {len(orders)} orders")

        if orders:
            for order in orders[:3]:
                print(f"\nOrder: {order.get('order_id')}")
                print(f"  Status: {order.get('status')}")
                print(f"  Side: {order.get('side')}")
                print(f"  Price: {order.get('price')}")

            # Try to cancel the first order
            if orders:
                order_id = orders[0]['order_id']
                print(f"\nTrying to cancel order {order_id}...")
                try:
                    await client.cancel_order(order_id, config.symbol)
                    print("✓ Cancel successful!")
                except Exception as e:
                    print(f"✗ Cancel failed: {e}")
                    # Try to get more details
                    if hasattr(e, 'status'):
                        print(f"  Status: {e.status}")
                    if hasattr(e, 'message'):
                        print(f"  Message: {e.message}")


if __name__ == "__main__":
    asyncio.run(main())
