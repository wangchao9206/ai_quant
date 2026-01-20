import requests
import pandas as pd
import io

BASE_URL = "http://localhost:8000"

def test_export():
    print("Testing Export Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/backtest/export")
        if response.status_code == 200:
            print("Export OK. Content-Type:", response.headers.get('content-type'))
            # Try to parse as Excel
            try:
                df = pd.read_excel(io.BytesIO(response.content))
                print(f"Excel read OK. Rows: {len(df)}")
            except Exception as e:
                print(f"Excel parse failed: {e}")
        else:
            print(f"Export Failed: {response.status_code}")
            print("Error:", response.text)
    except Exception as e:
        print(f"Export Request Failed: {e}")

def test_export_pdf():
    print("\nTesting PDF Export Endpoint...")
    res = requests.get(f"{BASE_URL}/api/backtest/export/pdf")
    if res.status_code == 200:
        print(f"PDF Export OK. Content-Type: {res.headers.get('Content-Type')}")
        content = res.content
        if len(content) > 100: # Basic check
             print(f"PDF Size: {len(content)} bytes")
    else:
        print(f"PDF Export Failed: {res.status_code} {res.text}")

def test_sorting():
    print("\nTesting History Sorting...")
    try:
        # Sort by return_rate desc
        res = requests.get(f"{BASE_URL}/api/backtest/history", params={"sort_by": "return_rate", "order": "desc", "limit": 5})
        data = res.json()
        items = data['items']
        print(f"Fetched {len(items)} items sorted by return_rate desc")
        if len(items) >= 2:
            print(f"Top 1: {items[0]['return_rate']}")
            print(f"Top 2: {items[1]['return_rate']}")
            if items[0]['return_rate'] >= items[1]['return_rate']:
                print("Sorting OK")
            else:
                print("Sorting Failed")
    except Exception as e:
        print(f"Sorting Request Failed: {e}")

if __name__ == "__main__":
    test_export()
    test_export_pdf()
    test_sorting()
