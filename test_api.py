import requests
import json

payload = {
    "symbol": "LH0",
    "period": "5",
    "strategy_params": {
        "fast_period": 10,
        "slow_period": 30,
        "contract_multiplier": 16,
        "risk_per_trade": 0.02,
        "atr_multiplier": 2.0
    },
    "initial_cash": 1000000,
    # "start_date": "2024-01-01",
    # "end_date": "2024-02-01"
}

print("Sending request...")
try:
    response = requests.post("http://localhost:8000/api/backtest", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        # print(f"Metrics: {json.dumps(data.get('metrics', {}), indent=2)}")
        print(f"Has Chart Data: {'chart_data' in data}")
        if 'chart_data' in data and data['chart_data']:
             print(f"Chart Data Keys: {data['chart_data'].keys()}")
             print(f"Num Bars: {len(data['chart_data'].get('dates', []))}")
        
        # Check first trade for new fields
        if data.get('trades'):
            print(f"First Trade: {json.dumps(data['trades'][0], indent=2)}")
        else:
            print("No trades found.")
        
        # Print debug logs
        if 'logs' in data and data['logs']:
            print("Debug Logs:")
            for log in data['logs']:
                if "DEBUG" in log:
                    print(log)
    else:
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
