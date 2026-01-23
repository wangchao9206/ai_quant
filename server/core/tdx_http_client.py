import requests
import logging
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class TdxHttpClient:
    """
    Client for the local Go-based tdx-api service.
    See: https://github.com/oficcejo/tdx-api
    Default URL: http://localhost:8080
    """
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 2.0  # Fast fail for local service
        
        # Availability management
        self._last_error_ts = 0.0
        self._retry_interval = 5.0  # Retry every 5 seconds (fast recovery for local dev)
        self._is_down = False

    def is_available(self) -> bool:
        """Check if we should try to use this service."""
        if not self._is_down:
            return True
        
        # If it was down, check if we passed the retry interval
        now = time.monotonic()
        if now - self._last_error_ts > self._retry_interval:
            # Time to retry
            logger.info(f"Retrying TDX HTTP API ({self.base_url})...")
            return True
        
        # Log periodically if needed, but for now just return False
        return False

    def _mark_down(self, reason: str):
        """Mark service as down temporarily."""
        now = time.monotonic()
        if not self._is_down:
            logger.warning(f"TDX HTTP API ({self.base_url}) marked down: {reason}. Will retry in {self._retry_interval}s.")
        self._is_down = True
        self._last_error_ts = now

    def _mark_up(self):
        """Mark service as up."""
        if self._is_down:
            logger.info(f"TDX HTTP API ({self.base_url}) recovered.")
        self._is_down = False
        self._last_error_ts = 0.0

    def _process_kline(self, data: Any) -> List[Dict[str, Any]]:
        """Map tdx-api kline response to internal format."""
        try:
            items = []
            if isinstance(data, dict):
                # Handle tdx-api response format: {"data": {"List": [...]}} or {"data": [...]}
                if "data" in data:
                    d = data["data"]
                    if isinstance(d, list):
                        items = d
                    elif isinstance(d, dict) and "List" in d and isinstance(d["List"], list):
                        items = d["List"]
                elif "list" in data and isinstance(data["list"], list):
                    items = data["list"]
            elif isinstance(data, list):
                items = data
                
            if not items:
                return []
                
            mapped = []
            for item in items:
                # Handle different casing from Go API
                ts = item.get("Date") or item.get("date") or item.get("time") or item.get("datetime")
                if not ts:
                    continue
                    
                o = item.get("Open") if "Open" in item else item.get("open")
                c = item.get("Close") if "Close" in item else item.get("close")
                h = item.get("High") if "High" in item else item.get("high")
                l = item.get("Low") if "Low" in item else item.get("low")
                v = item.get("Vol") if "Vol" in item else item.get("vol")
                amt = item.get("Amount") if "Amount" in item else item.get("amount")
                
                if o is None or c is None:
                    continue
                    
                mapped.append({
                    "datetime": str(ts),
                    "open": float(o),
                    "close": float(c),
                    "high": float(h),
                    "low": float(l),
                    "vol": float(v or 0),
                    "amount": float(amt or 0)
                })
            return mapped
        except Exception as e:
            logger.error(f"Error processing TDX kline: {e}")
            return []

    def get_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time quote.
        GET /api/quote?code=xxxxxx
        """
        if not self.is_available():
            logger.debug(f"TDX HTTP Client unavailable, skipping get_quote for {code}")
            return None

        url = f"{self.base_url}/api/quote"
        params = {"code": code}
        start_time = time.monotonic()
        
        try:
            logger.info(f"TDX HTTP Request: GET {url} params={params}")
            resp = requests.get(url, params=params, timeout=self.timeout)
            duration = time.monotonic() - start_time
            
            if resp.status_code == 200:
                self._mark_up()
                data = resp.json()
                # Log data snippet for debugging
                data_str = str(data)
                if len(data_str) > 200:
                    data_str = data_str[:200] + "..."
                logger.info(f"TDX HTTP Response ({duration:.3f}s): Success for {code}. Data: {data_str}")
                return data
            else:
                logger.warning(f"TDX HTTP Error ({duration:.3f}s): {resp.status_code} {resp.text}")
            
        except requests.exceptions.ConnectionError:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Connection Refused ({duration:.3f}s): {url}")
            self._mark_down("Connection refused")
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Exception ({duration:.3f}s): {e}")
        
        return None

    def get_index_bars(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch index bars (kline) to get latest index data.
        GET /api/index?code=xxxxxx
        """
        if not self.is_available():
            logger.debug(f"TDX HTTP Client unavailable, skipping get_index_bars for {code}")
            return None

        url = f"{self.base_url}/api/index"
        params = {"code": code}
        start_time = time.monotonic()
        
        try:
            logger.info(f"TDX HTTP Request: GET {url} params={params}")
            resp = requests.get(url, params=params, timeout=self.timeout)
            duration = time.monotonic() - start_time
            
            if resp.status_code == 200:
                self._mark_up()
                data = resp.json()
                # Log data snippet
                data_str = str(data)
                if len(data_str) > 200:
                    data_str = data_str[:200] + "..."
                logger.info(f"TDX HTTP Response ({duration:.3f}s): Success for {code}. Data: {data_str}")
                return data
            else:
                logger.warning(f"TDX HTTP Error ({duration:.3f}s): {resp.status_code} {resp.text}")
            
        except requests.exceptions.ConnectionError:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Connection Refused ({duration:.3f}s): {url}")
            self._mark_down("Connection refused")
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Exception ({duration:.3f}s): {e}")
        
        return None

    def parse_index_snapshot(self, data: Dict, code: str) -> Optional[Dict[str, Any]]:
        """
        Parse tdx-api index response (kline list) into single snapshot dict.
        """
        try:
            items = []
            if isinstance(data, dict):
                # Handle tdx-api response format: {"data": {"List": [...]}} or {"data": [...]}
                if "data" in data:
                    d = data["data"]
                    if isinstance(d, list):
                        items = d
                    elif isinstance(d, dict) and "List" in d and isinstance(d["List"], list):
                        items = d["List"]
            elif isinstance(data, list):
                items = data
            
            if not items:
                return None
            
            # Get latest bar
            item = items[-1]
            
            # Price scaling (usually /1000 for tdx-api)
            close_p = float(item.get("Close", 0)) / 1000.0
            open_p = float(item.get("Open", 0)) / 1000.0
            high = float(item.get("High", 0)) / 1000.0
            low = float(item.get("Low", 0)) / 1000.0
            
            # Previous close (Need to infer from previous bar if available)
            pre_close = open_p # Fallback
            if len(items) > 1:
                prev_item = items[-2]
                pre_close = float(prev_item.get("Close", 0)) / 1000.0
            
            change = close_p - pre_close
            pct_change = (change / pre_close * 100) if pre_close != 0 else 0.0
            
            return {
                "symbol": code, # Keep original request code (e.g. SH000001) or strip?
                "name": code,   # Name not available in kline data
                "price": close_p,
                "change": change,
                "pct_change": pct_change,
                "volume": str(item.get("Volume", 0)),
                "amount": str(item.get("Amount", 0)),
                "high": high,
                "low": low,
                "open": open_p,
                "pre_close": pre_close,
                "timestamp": item.get("Time", "")
            }
        except Exception as e:
            logger.error(f"Error parsing index snapshot: {e}")
            return None

    def parse_quote(self, data: Dict, code: str, exchange: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Parse tdx-api quote response into standardized dict.
        """
        try:
            # Handle potential wrapper
            items = []
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    items = data["data"]
                elif "list" in data and isinstance(data["list"], list):
                    items = data["list"]
                elif "Exchange" in data:
                    items = [data]
                elif "data" in data and isinstance(data["data"], dict):
                    items = [data["data"]]
            elif isinstance(data, list):
                items = data
            
            if not items:
                return None
                
            # Select best match if multiple
            target_item = items[0]
            if len(items) > 1 and exchange:
                # 0=SZ, 1=SH
                target_ex = 1 if exchange == "SH" else 0
                for item in items:
                    if item.get("Exchange") == target_ex:
                        target_item = item
                        break
            
            item = target_item
            
            # Check for K dict (standard tdx-api format)
            k_data = item.get("K", {})
            
            # Helper to get value from K or top level
            def get_val(keys, default=0):
                for k in keys:
                    if k in k_data:
                        return k_data[k]
                    if k in item:
                        return item[k]
                return default

            # Price scaling logic
            raw_price = float(get_val(["Last", "Price", "price", "current", "Close"], 0))
            
            if raw_price == 0:
                return None
                
            # Heuristic scaling: tdx-api returns integer (e.g. 11070 -> 11.07)
            price = raw_price / 1000.0

            last_close = float(get_val(["LastClose", "last_close", "pre_close"], raw_price)) / 1000.0
            open_p = float(get_val(["Open", "open"], 0)) / 1000.0
            high = float(get_val(["High", "high"], 0)) / 1000.0
            low = float(get_val(["Low", "low"], 0)) / 1000.0
            
            vol = str(get_val(["TotalHand", "Vol", "vol", "volume"], 0))
            amt = str(get_val(["Amount", "amount"], 0))
            
            # Change calculation
            change_pct = 0.0
            change_amt = 0.0
            if last_close > 0:
                change_amt = price - last_close
                change_pct = (change_amt / last_close) * 100
            
            name = item.get("Name") or item.get("name") or code
            
            return {
                "name": str(name),
                "code": code,
                "price": round(price, 2),
                "change": round(change_pct, 2),
                "changeAmt": round(change_amt, 2),
                "open": round(open_p, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "vol": vol,
                "amt": amt,
                "pe": 0.0,
                "pb": 0.0
            }
        except Exception as e:
            logger.error(f"Error parsing TDX quote: {e}")
            return None

    def get_kline(self, code: str, ktype: str = "day") -> List[Dict[str, Any]]:
        """
        Fetch K-line data.
        GET /api/kline?code=xxxxxx&type=day
        Returns list of dicts in internal format.
        """
        if not self.is_available():
            logger.debug(f"TDX HTTP Client unavailable, skipping get_kline for {code}")
            return []

        clean_code = code
        if len(code) > 6:
            clean_code = code[-6:] # Take last 6 digits

        url = f"{self.base_url}/api/kline"
        params = {"code": clean_code, "type": ktype}
        start_time = time.monotonic()

        try:
            logger.info(f"TDX HTTP Request: GET {url} params={params}")
            resp = requests.get(url, params=params, timeout=self.timeout)
            duration = time.monotonic() - start_time

            if resp.status_code == 200:
                self._mark_up()
                raw_data = resp.json()
                logger.info(f"TDX HTTP Response ({duration:.3f}s): Success for {code} ktype={ktype}")
                return self._process_kline(raw_data)
            else:
                logger.warning(f"TDX HTTP Error ({duration:.3f}s): {resp.status_code} {resp.text}")

        except requests.exceptions.ConnectionError:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Connection Refused ({duration:.3f}s): {url}")
            self._mark_down("Connection refused")
            return []
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Exception ({duration:.3f}s): {e}")
            return []
        return []

    def get_minute(self, code: str) -> Dict[str, Any]:
        """
        Fetch intraday minute data.
        GET /api/minute?code=xxxxxx
        """
        if not self.is_available():
            logger.debug(f"TDX HTTP Client unavailable, skipping get_minute for {code}")
            return {"times": [], "values": []}

        clean_code = code
        if len(code) > 6:
            clean_code = code[-6:]
            
        url = f"{self.base_url}/api/minute"
        params = {"code": clean_code}
        start_time = time.monotonic()

        try:
            logger.info(f"TDX HTTP Request: GET {url} params={params}")
            resp = requests.get(url, params=params, timeout=self.timeout)
            duration = time.monotonic() - start_time
            
            if resp.status_code == 200:
                self._mark_up()
                data = resp.json()
                logger.info(f"TDX HTTP Response ({duration:.3f}s): Success for {code}")
                return self._process_minute(data)
            else:
                logger.warning(f"TDX HTTP Error ({duration:.3f}s): {resp.status_code} {resp.text}")
            
        except requests.exceptions.ConnectionError:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Connection Refused ({duration:.3f}s): {url}")
            self._mark_down("Connection refused")
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.error(f"TDX HTTP Exception ({duration:.3f}s): {e}")
            
        return {"times": [], "values": []}

    def _process_minute(self, data: Any) -> Dict[str, Any]:
        times = []
        values = []
        
        items = []
        if isinstance(data, dict):
            # Handle tdx-api response format: {"data": {"List": [...]}} or {"data": [...]}
            if "data" in data:
                d = data["data"]
                if isinstance(d, list):
                    items = d
                elif isinstance(d, dict) and "List" in d and isinstance(d["List"], list):
                    items = d["List"]
            elif "list" in data and isinstance(data["list"], list):
                items = data["list"]
        elif isinstance(data, list):
            items = data
            
        for item in items:
            # Try different casing
            t = item.get("Time") or item.get("time")
            p = item.get("Price") or item.get("price")
            
            if t and p:
                try:
                    # Clean time format 0930 -> 09:30 if needed
                    t_str = str(t)
                    if len(t_str) == 4 and t_str.isdigit():
                         t_str = f"{t_str[:2]}:{t_str[2:]}"
                    
                    times.append(t_str)
                    p_float = float(p)
                    # Use same price for OHLC
                    values.append([p_float, p_float, p_float, p_float])
                except:
                    pass
                
        return {"times": times, "values": values}

# Global instance
tdx_http_client = TdxHttpClient()
