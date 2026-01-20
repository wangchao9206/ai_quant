import requests
import time

BASE_URL = "http://localhost:8001"

def test_workflow():
    print("1. Testing Health/Symbols...")
    try:
        r = requests.get(f"{BASE_URL}/api/symbols")
        assert r.status_code == 200
        print("   Symbols OK")
    except Exception as e:
        print(f"   Failed to connect: {e}")
        return

    print("2. Running a Backtest...")
    payload = {
        "symbol": "RB0",
        "period": "daily",
        "strategy_params": {
            "fast_period": 5,
            "slow_period": 10,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "risk_per_trade": 0.02,
            "contract_multiplier": 30
        },
        "auto_optimize": False,
        "start_date": "2023-01-01",
        "end_date": "2023-06-01"
    }
    r = requests.post(f"{BASE_URL}/api/backtest", json=payload)
    if r.status_code != 200:
        print(f"   Backtest Failed: {r.text}")
        return
    result = r.json()
    metrics = result['metrics']
    ret = (metrics['net_profit'] / metrics['initial_cash']) * 100
    print("   Backtest OK. Return:", ret)

    print("3. Checking History...")
    r = requests.get(f"{BASE_URL}/api/backtest/history")
    history = r.json()
    print(f"   Total records: {history['total']}")
    assert history['total'] > 0
    latest = history['items'][0]
    print(f"   Latest ID: {latest['id']}, Return: {latest['return_rate']}")

    print("4. Checking Detail...")
    r = requests.get(f"{BASE_URL}/api/backtest/{latest['id']}")
    detail = r.json()
    print("   Detail fetch OK.")
    print("   Has Equity Curve?", len(detail.get('equity_curve', [])) > 0)
    print("   Has Logs?", len(detail.get('logs', [])) > 0)

    print("5. Checking Stats...")
    r = requests.get(f"{BASE_URL}/api/backtest/stats")
    stats = r.json()
    print("   Stats:", stats)

if __name__ == "__main__":
    # Wait for server to potentially start
    time.sleep(2)
    test_workflow()
