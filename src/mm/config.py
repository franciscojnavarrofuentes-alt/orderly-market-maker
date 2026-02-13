"""Configuration loader"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Bot configuration"""
    # Orderly credentials
    base_url: str
    account_id: str
    api_key: str
    api_secret: str

    # Trading params
    symbol: str
    spread_bps: float  # Spread from mid price in basis points (e.g., 10 = 0.1%)
    order_size_usd: float

    # Bot params
    refresh_interval: float  # Seconds between quote updates
    dry_run: bool
    log_level: str


def load_config() -> Config:
    """Load configuration from environment variables"""
    load_dotenv()

    return Config(
        base_url=os.getenv("ORDERLY_BASE_URL", "https://api.orderly.org"),
        account_id=os.getenv("ORDERLY_ACCOUNT_ID", ""),
        api_key=os.getenv("ORDERLY_KEY", ""),
        api_secret=os.getenv("ORDERLY_SECRET", ""),

        symbol=os.getenv("SYMBOL", "PERP_ETH_USDC"),
        spread_bps=float(os.getenv("SPREAD_BPS", "10")),  # 0.1% each side
        order_size_usd=float(os.getenv("ORDER_SIZE_USD", "50")),

        refresh_interval=float(os.getenv("REFRESH_INTERVAL", "5")),
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
