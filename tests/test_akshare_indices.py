
import akshare as ak
import sys
import os
import time

def test_indices():
    print("=== Testing AkShare Indices Interface ===")
    start_time = time.time()
    
    # 1. Test Configuration
    symbol = "沪深重要指数" # Correct symbol
    print(f"Target Symbol: {symbol}")
    
    try:
        # 2. Execute
        print("Fetching data...", end="", flush=True)
        df = ak.stock_zh_index_spot_em(symbol=symbol)
        duration = time.time() - start_time
        print(f" Done ({duration:.2f}s)")
        
        # 3. Validation
        if df is None or df.empty:
            print("❌ FAIL: DataFrame is empty")
            return False
            
        print(f"✅ SUCCESS: Retrieved {len(df)} rows")
        
        # 4. Check Key Indices
        targets = {
            "000001": "上证指数",
            "399001": "深证成指", 
            "399006": "创业板指"
        }
        
        found_count = 0
        for _, row in df.iterrows():
            code = str(row['代码'])
            if code in targets:
                print(f"   - Found {targets[code]} ({code}): {row['最新价']}")
                found_count += 1
                
        if found_count < len(targets):
            print(f"⚠️ WARNING: Only found {found_count}/{len(targets)} key indices")
        else:
            print("✅ All key indices found")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Suggestion: Check if akshare version is updated or if EastMoney API changed.")
        return False

if __name__ == "__main__":
    success = test_indices()
    sys.exit(0 if success else 1)
