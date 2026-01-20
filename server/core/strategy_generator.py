
import re
import datetime

class StrategyGenerator:
    """
    Translates natural language strategy descriptions into Backtrader Python code.
    Currently uses a rule-based approach (Regex) for common patterns, 
    designed to be extended with LLM capabilities.
    """
    
    TEMPLATE = """
import backtrader as bt

class GeneratedStrategy(bt.Strategy):
    params = (
        ('printlog', True),
        ('stop_loss', 0.0),   # Percentage stop loss (e.g., 0.05 for 5%)
        ('take_profit', 0.0), # Percentage take profit
    )

    def log(self, txt, dt=None, doprint=False):
        if not hasattr(self, 'logs_list'):
             self.logs_list = []
        
        dt = dt or self.datas[0].datetime.date(0)
        log_msg = f'{dt.isoformat()}, {txt}'
        self.logs_list.append(log_msg)
        
        if self.params.printlog or doprint:
            print(log_msg)

    def stop(self):
        # Collect logs if they exist
        if hasattr(self, 'logs_list'):
            self.logs = self.logs_list
        else:
            self.logs = []

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Indicators
{indicators}

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {{order.executed.price:.2f}}, Cost: {{order.executed.value:.2f}}, Comm {{order.executed.comm:.2f}}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'SELL EXECUTED, Price: {{order.executed.price:.2f}}, Cost: {{order.executed.value:.2f}}, Comm {{order.executed.comm:.2f}}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {{trade.pnl:.2f}}, NET {{trade.pnlcomm:.2f}}')

    def next(self):
        if self.order:
            return

        # Stop Loss / Take Profit Logic
        if self.position:
            if self.params.stop_loss > 0:
                if self.dataclose[0] < self.buyprice * (1.0 - self.params.stop_loss):
                    self.log('STOP LOSS TRIGGERED')
                    self.order = self.sell()
                    return
            
            if self.params.take_profit > 0:
                if self.dataclose[0] > self.buyprice * (1.0 + self.params.take_profit):
                    self.log('TAKE PROFIT TRIGGERED')
                    self.order = self.sell()
                    return

        # Entry Conditions
        if not self.position:
{entry_logic}

        # Exit Conditions
        else:
{exit_logic}
"""

    def parse(self, text):
        """
        Main entry point to parse text and return code and config.
        """
        # 1. Normalize text
        original_text = text
        text = text.lower().replace(" ", "")
        
        # 2. Extract indicators
        indicators = []
        ind_defs = []
        config = {}
        
        # MA Pattern: "20日均线", "MA20", "SMA20", "20均线", "20日线"
        ma_matches = re.findall(r'(?:ma|sma|均线)(\d+)|(\d+)(?:日?)(?:ma|sma|均线|线)', text)
        ma_periods = []
        for m in ma_matches:
            p = m[0] if m[0] else m[1]
            if p and p not in ma_periods:
                ma_periods.append(int(p))
        
        if ma_periods:
            ma_periods.sort()
            # Try to map to fast/slow for standard form
            if len(ma_periods) >= 2:
                config['fast_period'] = ma_periods[0]
                config['slow_period'] = ma_periods[1]
            elif len(ma_periods) == 1:
                config['fast_period'] = ma_periods[0]

            for period in ma_periods:
                var_name = f"self.sma{period}"
                if var_name not in indicators:
                    indicators.append(var_name)
                    ind_defs.append(f"        self.sma{period} = bt.indicators.SimpleMovingAverage(self.datas[0], period={period})")

        # RSI Pattern: "rsi", "rsi14", "rsi>80"
        rsi_match = re.search(r'rsi(\d*)', text)
        if rsi_match:
            period = rsi_match.group(1) if rsi_match.group(1) else "14"
            indicators.append("self.rsi")
            ind_defs.append(f"        self.rsi = bt.indicators.RSI_Safe(self.datas[0], period={period})")
            config['rsi_period'] = int(period)

        # MACD Pattern
        if "macd" in text:
            indicators.append("self.macd")
            ind_defs.append(f"        self.macd = bt.indicators.MACD(self.datas[0])")
            config['use_macd'] = True

        # Stop Loss / Take Profit
        sl_match = re.search(r'止损(\d+(?:\.\d+)?)%?', text)
        if sl_match:
            sl_val = float(sl_match.group(1))
            if sl_val > 1: sl_val = sl_val / 100.0 # Convert 5 to 0.05
            ind_defs.append(f"        self.params.stop_loss = {sl_val}")
            config['stop_loss'] = sl_val

        tp_match = re.search(r'止盈(\d+(?:\.\d+)?)%?', text)
        if tp_match:
            tp_val = float(tp_match.group(1))
            if tp_val > 1: tp_val = tp_val / 100.0
            ind_defs.append(f"        self.params.take_profit = {tp_val}")
            config['take_profit'] = tp_val

        # 3. Parse Logic Segments (Simple approach)
        # Split by comma or common separators to isolate conditions
        segments = re.split(r'[,，。;；\n]', original_text)
        
        entry_logic = []
        exit_logic = []
        
        for segment in segments:
            segment_lower = segment.lower().replace(" ", "")
            if not segment_lower: continue
            
            # --- MA Logic ---
            seg_ma_matches = re.findall(r'(?:ma|sma|均线)(\d+)|(\d+)(?:日?)(?:ma|sma|均线|线)', segment_lower)
            seg_periods = [m[0] if m[0] else m[1] for m in seg_ma_matches if (m[0] or m[1])]
            
            # MA Crossover
            if len(seg_periods) >= 2:
                p1, p2 = seg_periods[0], seg_periods[1]
                # Assuming p1 < p2 usually, but regex order matters
                # "MA5 cross MA20"
                if ("突破" in segment_lower or "上穿" in segment_lower or "金叉" in segment_lower) and ("买" in segment_lower or "多" in segment_lower):
                     entry_logic.append(f"            if self.sma{p1}[0] > self.sma{p2}[0] and self.sma{p1}[-1] <= self.sma{p2}[-1]:")
                     entry_logic.append(f"                self.log('MA CROSS BUY')")
                     entry_logic.append(f"                self.order = self.buy()")
                elif ("跌破" in segment_lower or "下穿" in segment_lower or "死叉" in segment_lower) and ("卖" in segment_lower or "空" in segment_lower):
                     exit_logic.append(f"            if self.sma{p1}[0] < self.sma{p2}[0] and self.sma{p1}[-1] >= self.sma{p2}[-1]:")
                     exit_logic.append(f"                self.log('MA CROSS SELL')")
                     exit_logic.append(f"                self.order = self.sell()")
            
            # Single MA (Price vs MA)
            elif len(seg_periods) == 1:
                p = seg_periods[0]
                if ("突破" in segment_lower or "上穿" in segment_lower or "站上" in segment_lower) and ("买" in segment_lower):
                     entry_logic.append(f"            if self.dataclose[0] > self.sma{p}[0] and self.dataclose[-1] <= self.sma{p}[-1]:")
                     entry_logic.append(f"                self.log('PRICE BREAK MA BUY')")
                     entry_logic.append(f"                self.order = self.buy()")
                elif ("跌破" in segment_lower or "下穿" in segment_lower) and ("卖" in segment_lower):
                     exit_logic.append(f"            if self.dataclose[0] < self.sma{p}[0] and self.dataclose[-1] >= self.sma{p}[-1]:")
                     exit_logic.append(f"                self.log('PRICE DROP MA SELL')")
                     exit_logic.append(f"                self.order = self.sell()")

            # --- RSI Logic ---
            if "rsi" in segment_lower:
                # "RSI < 30 buy"
                val_match = re.search(r'(?:<|小于|低于)(\d+)', segment_lower)
                if val_match and ("买" in segment_lower):
                    val = val_match.group(1)
                    entry_logic.append(f"            if self.rsi[0] < {val}:")
                    entry_logic.append(f"                self.log('RSI OVERSOLD BUY')")
                    entry_logic.append(f"                self.order = self.buy()")
                
                # "RSI > 70 sell"
                val_match_high = re.search(r'(?:>|大于|高于)(\d+)', segment_lower)
                if val_match_high and ("卖" in segment_lower):
                    val = val_match_high.group(1)
                    exit_logic.append(f"            if self.rsi[0] > {val}:")
                    exit_logic.append(f"                self.log('RSI OVERBOUGHT SELL')")
                    exit_logic.append(f"                self.order = self.sell()")

            # --- MACD Logic ---
            if "macd" in segment_lower:
                if ("金叉" in segment_lower or ("上穿" in segment_lower and "signal" in segment_lower)) and ("买" in segment_lower):
                    entry_logic.append(f"            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:")
                    entry_logic.append(f"                self.log('MACD GOLDEN CROSS BUY')")
                    entry_logic.append(f"                self.order = self.buy()")
                elif ("死叉" in segment_lower or ("下穿" in segment_lower and "signal" in segment_lower)) and ("卖" in segment_lower):
                    exit_logic.append(f"            if self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]:")
                    exit_logic.append(f"                self.log('MACD DEATH CROSS SELL')")
                    exit_logic.append(f"                self.order = self.sell()")

        # Fallback if logic empty (for demo safety)
        if not entry_logic:
            entry_logic.append("            pass # No entry condition found")
        if not exit_logic:
            exit_logic.append("            pass # No exit condition found")

        code = self.TEMPLATE.format(
            indicators="\n".join(ind_defs),
            entry_logic="\n".join(entry_logic),
            exit_logic="\n".join(exit_logic)
        )
        
        return {"code": code, "config": config}

strategy_generator = StrategyGenerator()
