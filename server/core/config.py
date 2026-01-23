from typing import List, Dict, Optional

# === MongoDB Configuration ===
MONGO_HOST = "localhost"
MONGO_PORT = "27017"
MONGO_USERNAME = "admin"
MONGO_PASSWORD = "password123"
MONGO_AUTH_SOURCE = "admin"
MONGO_DB = "quant"
MONGO_COLLECTION = "backtest_records"
MONGO_MARKET_COLLECTION = "market_bars"
MONGO_MIGRATE_FROM_SQLITE = True
MONGO_USE_FALLBACK = False
MONGO_TIMEOUT_MS = 2000

DATA_SYNC_CRON_HOUR = 15
DATA_SYNC_CRON_MINUTE = 10
DATA_SYNC_ASSET_TYPES = ["stock", "fund", "futures"]
DATA_SYNC_STOCK_SYMBOLS = []
DATA_SYNC_FUND_SYMBOLS = []
DATA_SYNC_FUTURES_SYMBOLS = []
DATA_SYNC_STOCK_LIMIT = 0
DATA_SYNC_FUND_LIMIT = 0
DATA_SYNC_FUTURES_LIMIT = 0

# === Proxy Configuration ===
# Explicitly disable proxies to prevent connection issues
DISABLE_PROXIES = True

# === TDX Server Configuration ===
# Initial high-quality hosts
TDX_HOSTS: List[Dict[str, object]] = [
    {'ip': '119.147.212.81', 'port': 7709},
    {'ip': '119.147.212.120', 'port': 7709},
    {'ip': '221.231.141.60', 'port': 7709},
    {'ip': '124.74.236.94', 'port': 7709},
    {'ip': '101.227.73.20', 'port': 7709},
    {'ip': '114.80.73.243', 'port': 7709},
    {'ip': '121.14.110.200', 'port': 7709},
    {'ip': '218.108.47.69', 'port': 7709},
    {'ip': '180.153.39.51', 'port': 7709},
]
