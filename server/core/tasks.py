import datetime
import logging
from api.deps import get_data_manager
from core.config import DATA_SYNC_ASSET_TYPES

logger = logging.getLogger(__name__)


def daily_data_update(full: bool = False):
    data_manager = get_data_manager()
    start_time = datetime.datetime.utcnow()
    logger.info("Daily data sync started")
    summaries = data_manager.sync_all(asset_types=DATA_SYNC_ASSET_TYPES, period="daily", full=full)
    duration = (datetime.datetime.utcnow() - start_time).total_seconds()
    logger.info("Daily data sync finished in %.2fs", duration)
    return summaries


def startup_sync_check():
    data_manager = get_data_manager()
    with data_manager._connect() as conn:
        row = conn.execute("SELECT COUNT(1) FROM market_bars").fetchone()
        total = int(row[0]) if row else 0
    if total == 0:
        logger.info("No historical data found, starting full sync")
        return daily_data_update(full=True)
    logger.info("Historical data found, starting incremental sync")
    return daily_data_update(full=False)
