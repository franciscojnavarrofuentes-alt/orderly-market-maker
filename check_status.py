import asyncio
import sys
sys.path.insert(0, 'src')
from mm.config import load_config
from mm.client import OrderlyClient

async def main():
    config = load_config()
    async with OrderlyClient(config.base_url, config.account_id, config.api_key, config.api_secret) as client:
        # Get position
        pos = await client.get_position(config.symbol)
        print('=== POSICIÓN ACTUAL ===')
        print(f'Cantidad: {pos.get("position_qty", 0)} ETH')
        print(f'Precio entrada: ${pos.get("average_open_price", 0)}')
        print(f'PnL no realizado: ${pos.get("unrealized_pnl", 0)}')
        print(f'Notional: ${pos.get("position_notional", 0)}')

        # Get mark price
        mark = await client.get_mark_price(config.symbol)
        print(f'\nMark price actual: ${mark}')

        # Get open orders
        orders = await client.get_open_orders(config.symbol)
        print(f'\nÓrdenes abiertas: {len(orders)}')

asyncio.run(main())
