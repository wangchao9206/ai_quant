import unittest
import tempfile
import pandas as pd
from core.data_manager import DataManager
from core.data_processor import DataProcessor


class FakeDataManager(DataManager):
    def __init__(self, test_df: pd.DataFrame, **kwargs):
        super().__init__(**kwargs)
        self.test_df = test_df

    def _fetch_data(self, symbol: str, period: str, asset_type: str, start_date):
        return self.test_df


class TestDataSync(unittest.TestCase):
    def test_clean_data_rules(self):
        idx = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"])
        df = pd.DataFrame(
            {
                "Open": [10, 10, None],
                "High": [9, 8, 12],
                "Low": [11, 9, 10],
                "Close": [10, 10, 11],
                "Volume": [-1, 100, 200],
            },
            index=idx,
        )
        cleaned = DataProcessor.clean_data(df)
        self.assertFalse(cleaned.index.duplicated().any())
        self.assertTrue((cleaned["Volume"] >= 0).all())
        self.assertTrue((cleaned["High"] >= cleaned["Low"]).all())

    def test_incremental_sync_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/market.db"
            df_initial = pd.DataFrame(
                {
                    "Open": [1, 2, 3],
                    "High": [2, 3, 4],
                    "Low": [1, 2, 3],
                    "Close": [1.5, 2.5, 3.5],
                    "Volume": [10, 20, 30],
                },
                index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            )
            df_new = pd.DataFrame(
                {
                    "Open": [2, 3, 4],
                    "High": [3, 4, 5],
                    "Low": [2, 3, 4],
                    "Close": [2.5, 3.5, 4.5],
                    "Volume": [20, 30, 40],
                },
                index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            )
            manager = FakeDataManager(df_initial, db_path=db_path)
            manager._write_market_data(df_initial, "stock", "000001", "daily")
            manager._set_last_ts("stock", "000001", "daily", pd.to_datetime("2024-01-02"))
            manager.test_df = df_new
            manager.sync_symbol_data("000001", "daily", "stock", full=False)

            with manager._connect() as conn:
                count = conn.execute(
                    "SELECT COUNT(1) FROM market_bars WHERE asset_type=? AND symbol=? AND period=?",
                    ("stock", "000001", "daily"),
                ).fetchone()[0]
            self.assertEqual(count, 4)

    def test_load_data_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/market.db"
            df = pd.DataFrame(
                {
                    "Open": [1, 2, 3],
                    "High": [2, 3, 4],
                    "Low": [1, 2, 3],
                    "Close": [1.5, 2.5, 3.5],
                    "Volume": [10, 20, 30],
                },
                index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            )
            manager = DataManager(db_path=db_path)
            manager._write_market_data(df, "stock", "000001", "daily")
            loaded = manager.load_data("000001", "daily", start_date="2024-01-02", end_date="2024-01-02", asset_type="stock")
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded), 1)

    def test_fetch_and_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/market.db"
            df = pd.DataFrame(
                {
                    "Open": [1, 2, 3],
                    "High": [2, 3, 4],
                    "Low": [1, 2, 3],
                    "Close": [1.5, 2.5, 3.5],
                    "Volume": [10, 20, 30],
                },
                index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            )
            manager = FakeDataManager(df, db_path=db_path)
            loaded = manager.fetch_and_update("SZ000001", "daily")
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded), 3)


if __name__ == "__main__":
    unittest.main()
