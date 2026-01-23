import threading
import time
import concurrent.futures
import socket
import random
from typing import List, Dict, Optional, Any
from pytdx.hq import TdxHq_API
from pytdx.config.hosts import hq_hosts
from core.config import TDX_HOSTS

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
            self.lock = threading.Lock() # Guards self.api usage
            
            # Initial hardcoded hosts (high quality) from config
            self.hosts = list(TDX_HOSTS)
            
            # Merge with pytdx default hosts
            existing_ips = {h['ip'] for h in self.hosts}
            for name, ip, port in hq_hosts:
                if ip not in existing_ips:
                    self.hosts.append({'ip': ip, 'port': port})
                    existing_ips.add(ip)
            
            self.current_host_idx = 0
            self.connected = False
            self.health_lock = threading.Lock()
            self.health = {"ok": None, "ts": 0.0, "detail": None, "degraded": False}
            
            # Non-blocking connection management
            self._connecting = False
            self._connecting_lock = threading.Lock()
            self._last_connect_attempt = 0.0
            
            self._initialized = True
            
            # Start background host selection (non-blocking)
            # DISABLED BY USER REQUEST
            # threading.Thread(target=self.select_best_host, daemon=True).start()

    def _quick_select_best_host(self):
        """Quickly ping a few hosts to find a good one immediately."""
        pass

    def _ping_host(self, host: Dict, timeout: float = 2.0) -> float:
        """Ping a host via TCP connect to measure latency."""
        return float('inf')

    def select_best_host(self):
        """Test hosts and sort by latency."""
        pass

    def connect(self) -> bool:
        """
        Ensure connection to TDX server.
        Non-blocking check. If connecting, returns False immediately.
        """
        return False


    def _set_health(self, ok: bool, detail: Optional[str] = None) -> None:
        with self.health_lock:
            self.health["ok"] = ok
            self.health["ts"] = time.time()
            self.health["detail"] = detail
            if ok:
                self.health["degraded"] = False
            else:
                self.health["degraded"] = True

    def get_health(self) -> Dict[str, Any]:
        with self.health_lock:
            return dict(self.health)

    def is_degraded(self) -> bool:
        with self.health_lock:
            return bool(self.health.get("degraded"))

    def check_health(self) -> bool:
        # Non-blocking health check
        return self.connect()

    def get_market_code(self, code: str) -> int:
        if code.startswith(('6', '5', '7')):
            return 1
        if code.startswith('000') and len(code) == 6:
            pass
        return 0

    def get_index_quotes(self) -> List[Dict[str, Any]]:
        target_indices = [
            (1, '000001'), # SH Composite
            (0, '399001'), # SZ Component
            (0, '399006'), # ChiNext
            (1, '000688'), # STAR 50
        ]
        
        if not self.connect():
            raise Exception("Failed to connect to TDX")
            
        with self.lock:
            try:
                quotes = self.api.get_security_quotes(target_indices)
                if not quotes:
                    return []
                
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
                    last_close = q.get('last_close', 0)
                    price = q.get('price', 0)
                    change = 0
                    pct = 0
                    if last_close > 0:
                        change = price - last_close
                        pct = (change / last_close) * 100
                    
                    processed.append({
                        "name": q['name'],
                        "value": price,
                        "change": round(pct, 2),
                        "volume": str(q.get('amount', 0))
                    })
                
                order = ['上证指数', '深证成指', '创业板指', '科创50']
                processed.sort(key=lambda x: order.index(x['name']) if x['name'] in order else 99)
                return processed
            except Exception as e:
                self.connected = False
                self._set_health(False, str(e))
                raise e

    def get_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        if not codes:
            return []
            
        all_processed = []
        chunk_size = 80
        
        for i in range(0, len(codes), chunk_size):
            chunk = codes[i:i + chunk_size]
            params = []
            for code in chunk:
                market = self.get_market_code(code)
                params.append((market, code))
            
            # Retry mechanism
            max_retries = 2 # Reduced from 3
            success = False
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if not self.connect():
                        raise Exception("Connection unavailable")
                    
                    with self.lock:
                        quotes = self.api.get_security_quotes(params)
                        if quotes:
                            all_processed.extend(self._process_quotes(quotes))
                        success = True
                    
                    if success:
                        break

                except Exception as e:
                    last_error = e
                    # Mark disconnected
                    with self.lock:
                        self.connected = False
                    self._set_health(False, str(e))
                    
                    # If this was the last attempt, don't sleep, just fail
                    if attempt < max_retries - 1:
                         # Maybe try next host logic handled in connect()
                         pass
                    
            if not success:
                raise last_error or Exception("Failed to fetch quotes")
                    
        return all_processed

    def _process_quotes(self, quotes: List[Dict]) -> List[Dict]:
        processed = []
        for q in quotes:
            bids = []
            asks = []
            for i in range(1, 6):
                bids.append({'p': q.get(f'bid{i}', 0), 'v': q.get(f'bid_vol{i}', 0)})
                asks.append({'p': q.get(f'ask{i}', 0), 'v': q.get(f'ask_vol{i}', 0)})
            
            last_close = q.get('last_close', 0)
            price = q.get('price', 0)
            change = 0
            pct = 0
            if last_close > 0:
                change = price - last_close
                pct = (change / last_close) * 100
            
            q['bids'] = bids
            q['asks'] = asks
            q['change'] = round(change, 2)
            q['change_pct'] = round(pct, 2)
            q['name'] = str(q.get('code', '')) 
            processed.append(q)
        return processed

    def _process_kline(self, data: List[Dict]) -> List[Dict]:
        processed = []
        for d in data:
            ts_str = ""
            if 'year' in d and 'month' in d and 'day' in d:
                ts_str = f"{d['year']}-{d['month']:02d}-{d['day']:02d}"
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
                self._set_health(False, str(e))
                raise e

    def get_security_list(self, market: int, start: int = 0) -> List[Dict]:
        if not self.connect():
            raise Exception("Failed to connect")
        with self.lock:
            try:
                return self.api.get_security_list(market, start)
            except Exception as e:
                self.connected = False
                self._set_health(False, str(e))
                raise e

tdx_client = TdxClient()
