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
    try:
        from core.database import get_market_collection
        col = get_market_collection()
        total = int(col.count_documents({}))
    except Exception:
        total = 0
    if total == 0:
        logger.info("No historical data found, starting full sync")
        return daily_data_update(full=True)
    logger.info("Historical data found, starting incremental sync")
    return daily_data_update(full=False)
