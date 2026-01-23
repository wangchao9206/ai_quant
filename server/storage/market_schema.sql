CREATE TABLE IF NOT EXISTS market_bars (
    asset_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    ts TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL,
    open_interest REAL,
    amount REAL,
    update_time TEXT NOT NULL,
    PRIMARY KEY (asset_type, symbol, period, ts)
);

CREATE INDEX IF NOT EXISTS idx_market_bars_ts ON market_bars(ts);

CREATE TABLE IF NOT EXISTS sync_state (
    asset_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    last_ts TEXT,
    last_sync TEXT,
    PRIMARY KEY (asset_type, symbol, period)
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    mode TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL,
    rows_fetched INTEGER NOT NULL,
    rows_written INTEGER NOT NULL,
    error TEXT
);
