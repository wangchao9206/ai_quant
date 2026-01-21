from typing import Generator
from core.database import SessionLocal
from core.data_manager import DataManager

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# Singleton instance
_data_manager = DataManager()

def get_data_manager() -> DataManager:
    return _data_manager
