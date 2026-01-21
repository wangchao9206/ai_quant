import datetime
from api.deps import get_data_manager
from core.constants import get_multiplier

# Lazy import akshare to avoid startup delay
ak = None

def daily_data_update():
    global ak
    if ak is None:
        import akshare as ak
        
    print(f"[{datetime.datetime.now()}] Starting daily data update...")
    data_manager = get_data_manager()
    
    # Update cached symbols first to get latest list
    symbols = []
    try:
        print("Fetching latest symbol list from AkShare...")
        df = ak.futures_display_main_sina()
        
        # Update symbol cache file
        futures_list = []
        for _, row in df.iterrows():
            s = row['symbol']
            multiplier = get_multiplier(s)
            futures_list.append({
                "code": s,
                "name": f"{row['name']} ({s})",
                "multiplier": multiplier
            })
        
        data_manager.save_symbols_list(futures_list)
        symbols = [item['code'] for item in futures_list]
        print(f"Successfully updated symbol list with {len(symbols)} items.")
        
    except Exception as e:
        print(f"Failed to fetch symbol list during update: {e}")
        # Fallback to existing local cache or defaults
        local_symbols = data_manager.get_symbols_list()
        if local_symbols:
            symbols = [s['code'] for s in local_symbols]
        else:
            symbols = ['LH0', 'SH0', 'RB0', 'M0', 'IF0']
    
    print(f"Found {len(symbols)} symbols to update.")
    for symbol in symbols:
        # Update daily data for all symbols
        # Note: Updating minute data for ALL symbols might be too heavy. 
        # Ideally, we only update symbols that are 'active' or 'watched'.
        # For now, we update daily data which is fast.
        try:
            data_manager.fetch_and_update(symbol, 'daily')
        except Exception as e:
            print(f"Error updating data for {symbol}: {e}")
        
        # Uncomment to update minute data too (warning: slow)
        # data_manager.fetch_and_update(symbol, '5') 
        
    print(f"[{datetime.datetime.now()}] Daily data update completed.")
