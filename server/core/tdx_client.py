import threading
import time
import os
import configparser
from typing import List, Dict, Optional, Any
from pytdx.hq import TdxHq_API

class TdxClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TdxClient, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        with self._lock:
            if self._initialized:
                return
            # Enable raise_exception to see real errors
            self.api = TdxHq_API(heartbeat=True, raise_exception=True)
            self.lock = threading.Lock()
            # High quality public TDX servers (fallback)
            self.hosts = [
                {'ip': '119.147.212.81', 'port': 7709},
                {'ip': '119.147.212.120', 'port': 7709},
                {'ip': '221.231.141.60', 'port': 7709},
                {'ip': '124.74.236.94', 'port': 7709},
                {'ip': '101.227.73.20', 'port': 7709},
                {'ip': '114.80.73.243', 'port': 7709},
                {'ip': '121.14.110.200', 'port': 7709},
                {'ip': '218.108.47.69', 'port': 7709},
                {'ip': '180.153.39.51', 'port': 7709},
            ]
            self._load_local_config()
            self.current_host_idx = 0
            self.connected = False
            self._initialized = True

    def _load_local_config(self):
        """Load servers from local TDX installation if available."""
        config_path = r"D:\software\tdx\connect.cfg"
        if not os.path.exists(config_path):
            return

        try:
            print(f"Loading TDX config from {config_path}...")
            # connect.cfg is often GBK encoded
            config = configparser.ConfigParser()
            config.read(config_path, encoding='gbk')
            
            if 'HQHOST' in config:
                hosts = []
                section = config['HQHOST']
                host_num = int(section.get('HostNum', 0))
                primary_idx = int(section.get('PrimaryHost', -1))
                
                # Extract primary host first
                if primary_idx >= 0:
                    ip = section.get(f'IPAddress{primary_idx:02d}')
                    port = section.get(f'Port{primary_idx:02d}')
                    if ip and port:
                        hosts.append({'ip': ip, 'port': int(port)})
                        print(f"Found Primary Host: {ip}:{port}")

                # Extract others
                for i in range(1, host_num + 1):
                    # Skip primary if already added
                    if i == primary_idx:
                        continue
                        
                    key_suffix = f"{i:02d}" # 01, 02, ...
                    ip = section.get(f'IPAddress{key_suffix}')
                    port = section.get(f'Port{key_suffix}')
                    
                    if ip and port:
                        try:
                            hosts.append({'ip': ip, 'port': int(port)})
                        except:
                            pass
                
                if hosts:
                    print(f"Loaded {len(hosts)} servers from local config.")
                    self.hosts = hosts # Replace default hosts
        except Exception as e:
            print(f"Failed to load local TDX config: {e}")

    def connect(self) -> bool:
        """Ensure connection to TDX server."""
        with self.lock:
            if self.connected:
                # We could add a ping here if needed, but pytdx has heartbeat
                return True
            
            # Try to connect cycling through hosts
            start_idx = self.current_host_idx
            # Try more servers
            for _ in range(len(self.hosts)):
                host = self.hosts[self.current_host_idx]
                try:
                    print(f"Connecting to TDX {host['ip']}...")
                    if self.api.connect(host['ip'], host['port'], time_out=5):
                        self.connected = True
                        print(f"Connected to TDX {host['ip']}!")
                        return True
                except Exception as e:
                    print(f"Connection failed to {host['ip']}: {e}")
                    pass
                
                self.current_host_idx = (self.current_host_idx + 1) % len(self.hosts)
            
            return False

    def get_market_code(self, code: str) -> int:
        """
        0 - SZ, 1 - SH
        Note: This is a heuristic. 
        SH: 600xxx, 688xxx (KC), 000xxx (Index) -> But 000xxx is also SZ Stock?
        SZ: 00xxxx, 30xxxx (ChiNext)
        
        Strictly speaking:
        SH Stocks: 60xxxx, 68xxxx
        SH Indices: 000xxx (e.g. 000001)
        SZ Stocks: 00xxxx, 30xxxx
        SZ Indices: 399xxx
        """
        if code.startswith(('6', '5', '7')):
            return 1
        # Special handling for SH Index 000001 vs SZ Stock 000001 (PingAn)
        # This function is usually used for stocks. 
        # For indices, use explicit (market, code) tuples.
        if code.startswith('000') and len(code) == 6:
            # Ambiguous. Default to SZ stock usually unless it's known index.
            pass
        return 0

    def get_index_quotes(self) -> List[Dict[str, Any]]:
        """Get quotes for major indices: SH, SZ, ChiNext, KC50"""
        # SH Index (1, 000001), SZ Component (0, 399001), ChiNext (0, 399006), KC50 (1, 000688)
        # Note: KC50 index code is 000688 in SH? Or is it ETF? 
        # KC50 Index is 000688. SH Market.
        target_indices = [
            (1, '000001'), # SH Composite
            (0, '399001'), # SZ Component
            (0, '399006'), # ChiNext
            (1, '000688'), # STAR 50
        ]
        
        if not self.connect():
            # Return empty or raise? Raise to let caller handle
            raise Exception("Failed to connect to TDX")
            
        with self.lock:
            try:
                quotes = self.api.get_security_quotes(target_indices)
                if not quotes:
                    return []
                
                # Map names manually because get_security_quotes doesn't return index names properly sometimes
                # or we want standard names
                names = {
                    '000001': '上证指数',
                    '399001': '深证成指',
                    '399006': '创业板指',
                    '000688': '科创50'
                }
                
                processed = []
                for q in quotes:
                    code = q.get('code')
                    q['name'] = names.get(code, code)
                    # Calculate change
                    last_close = q.get('last_close', 0)
                    price = q.get('price', 0)
                    change = 0
                    pct = 0
                    if last_close > 0:
                        change = price - last_close
                        pct = (change / last_close) * 100
                    
                    # Format for frontend
                    processed.append({
                        "name": q['name'],
                        "value": price,
                        "change": round(pct, 2),
                        "volume": str(q.get('amount', 0)) # Index volume usually Amount
                    })
                
                # Sort to ensure order
                order = ['上证指数', '深证成指', '创业板指', '科创50']
                processed.sort(key=lambda x: order.index(x['name']) if x['name'] in order else 99)
                return processed
            except Exception as e:
                self.connected = False
                raise e

    def get_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        if not codes:
            return []
            
        # pytdx allows max 80 stocks per query usually
        # We split into chunks of 80 just in case
        all_processed = []
        chunk_size = 80
        
        for i in range(0, len(codes), chunk_size):
            chunk = codes[i:i + chunk_size]
            params = []
            for code in chunk:
                market = self.get_market_code(code)
                params.append((market, code))
            
            # Retry mechanism for each chunk
            max_retries = 3
            success = False
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # Ensure connected (connect() handles its own locking)
                    if not self.connect():
                        # Force rotate if connect returns False (though connect tries all hosts)
                        self.current_host_idx = (self.current_host_idx + 1) % len(self.hosts)
                        raise Exception("Connection failed")
                    
                    with self.lock:
                        quotes = self.api.get_security_quotes(params)
                        if quotes:
                            all_processed.extend(self._process_quotes(quotes))
                        success = True
                    
                    if success:
                        break

                except Exception as e:
                    last_error = e
                    print(f"TDX get_quotes error (attempt {attempt+1}/{max_retries}): {e}")
                    
                    # Mark disconnected so next connect() call reconnects
                    with self.lock:
                        self.connected = False
                    
                    # Rotate to next host for next attempt
                    self.current_host_idx = (self.current_host_idx + 1) % len(self.hosts)
                    
            if not success:
                # If all retries failed for this chunk, re-raise
                raise last_error or Exception("Failed to fetch quotes")
                    
        return all_processed

    def _process_quotes(self, quotes: List[Dict]) -> List[Dict]:
        processed = []
        for q in quotes:
            # Transform flattened bid/ask to arrays
            bids = []
            asks = []
            for i in range(1, 6):
                # pytdx returns 0 for empty levels sometimes
                bids.append({'p': q.get(f'bid{i}', 0), 'v': q.get(f'bid_vol{i}', 0)})
                asks.append({'p': q.get(f'ask{i}', 0), 'v': q.get(f'ask_vol{i}', 0)})
            
            # Add derived fields
            last_close = q.get('last_close', 0)
            price = q.get('price', 0)
            change = 0
            pct = 0
            if last_close > 0:
                change = price - last_close
                pct = (change / last_close) * 100
            
            # Map standard keys for frontend
            q['bids'] = bids
            q['asks'] = asks
            q['change'] = round(change, 2)
            q['change_pct'] = round(pct, 2)
            # Use code as name fallback since get_security_quotes doesn't return name
            q['name'] = str(q.get('code', '')) 
            
            processed.append(q)
        return processed

    def _process_kline(self, data: List[Dict]) -> List[Dict]:
        processed = []
        for d in data:
            # Format datetime
            ts_str = ""
            if 'year' in d and 'month' in d and 'day' in d:
                ts_str = f"{d['year']}-{d['month']:02d}-{d['day']:02d}"
                # Minute bars usually have hour/minute. 
                # Note: day bars from pytdx might NOT have hour/minute keys, or have them as 0.
                # We check if they exist and are significant if needed, 
                # but usually minute bars (category 0-8) have valid hour/minute.
                if 'hour' in d and 'minute' in d:
                     ts_str += f" {d['hour']:02d}:{d['minute']:02d}"
            
            new_d = {
                'datetime': ts_str,
                'open': d.get('open'),
                'close': d.get('close'),
                'high': d.get('high'),
                'low': d.get('low'),
                'vol': d.get('vol'),
                'amount': d.get('amount')
            }
            processed.append(new_d)
        return processed

    def get_kline(self, code: str, category: str = 'day', start: int = 0, count: int = 800) -> List[Dict]:
        if not self.connect():
            raise Exception("Failed to connect")
        
        market = self.get_market_code(code)
        
        # Map category string to TDX int
        # 9=Day, 5=5min, 4=1min, 0=5min(older), 8=1min(older)
        # Using standard mapping
        cat_map = {
            'day': 9, 'd': 9,
            'week': 5, 'w': 5,
            'month': 6, 'm': 6,
            'year': 11, 'y': 11,
            '5min': 0, '5m': 0,
            '1min': 8, '1m': 8,
            '15min': 1, '15m': 1,
            '30min': 2, '30m': 2,
            '60min': 3, '1hour': 3, 'h': 3
        }
        category_id = cat_map.get(str(category).lower(), 9)
        
        with self.lock:
            try:
                data = self.api.get_security_bars(category_id, market, code, start, count)
                if not data:
                    return []
                return self._process_kline(data)
            except Exception as e:
                self.connected = False
                raise e

    def get_security_list(self, market: int, start: int = 0) -> List[Dict]:
        if not self.connect():
            raise Exception("Failed to connect")
        with self.lock:
            try:
                # pytdx get_security_list returns list of tuples/dicts?
                # It usually returns list of dicts: code, volunit, decimal_point, name, pre_close
                return self.api.get_security_list(market, start)
            except Exception as e:
                self.connected = False
                raise e

tdx_client = TdxClient()
