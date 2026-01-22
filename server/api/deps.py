from typing import Generator
from core.database import get_backtest_store
from core.data_manager import DataManager

def get_db() -> Generator:
    yield get_backtest_store()

# Singleton instance
_data_manager = DataManager()

def get_data_manager() -> DataManager:
    return _data_manager
