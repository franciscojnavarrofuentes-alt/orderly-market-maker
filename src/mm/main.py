"""Market Maker Bot - Entry Point"""
import asyncio
import logging
import signal
import sys

from mm.bot import MarketMaker
from mm.client import OrderlyClient
from mm.config import load_config

logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    # Load config
    config = load_config()

    # Setup logging
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validate credentials
    if not config.account_id or not config.api_key or not config.api_secret:
        logger.error("Missing ORDERLY_ACCOUNT_ID, ORDERLY_KEY, or ORDERLY_SECRET in .env")
        sys.exit(1)

    # Create client and bot
    async with OrderlyClient(
        config.base_url,
        config.account_id,
        config.api_key,
        config.api_secret
    ) as client:
        bot = MarketMaker(config, client)

        # Handle graceful shutdown
        def shutdown_handler(signum, frame):
            logger.info("Shutdown signal received, canceling all orders...")
            asyncio.create_task(client.cancel_all(config.symbol))
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        # Run bot
        await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
