import backtrader as bt
import datetime

class TrendFollowingStrategy(bt.Strategy):
    """
    趋势跟踪策略：
    1. 信号：双均线交叉 (Fast SMA vs Slow SMA)
    2. 风控：ATR 移动止损
    3. 仓位管理：基于账户权益百分比的风险敞口计算
    """
    params = (
        ('fast_period', 10),      # 快速均线周期
        ('slow_period', 30),      # 慢速均线周期
        ('atr_period', 14),       # ATR周期
        ('atr_multiplier', 2.0),  # ATR止损倍数
        ('risk_per_trade', 0.02), # 每笔交易风险 (2% of equity)
        ('contract_multiplier', 1), # 合约乘数 (期货使用)
        ('use_expma', False),     # 是否使用指数移动平均 (EXPMA)
        ('print_log', True),      # 是否打印日志
    )

    def __init__(self):
        # 初始化指标
        # 1. 均线
        if self.params.use_expma:
             self.sma_fast = bt.indicators.EMA(self.data.close, period=self.params.fast_period)
             self.sma_slow = bt.indicators.EMA(self.data.close, period=self.params.slow_period)
        else:
             self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
             self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        
        # 交叉信号 (1: 金叉, -1: 死叉)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # 2. ATR 风控
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # 交易状态
        self.order = None      # 当前挂单
        self.stop_price = None # 当前止损价
        self.order_reasons = {} # 记录订单原因 {order_ref: reason}
        
        # 记录所有已平仓交易
        self.trade_history = []
        # 日志记录
        self.logs = []

    def log(self, txt, dt=None):
        """ 日志记录函数 """
        dt = dt or self.datas[0].datetime.datetime(0)
        log_text = f'{dt.isoformat()}, {txt}'
        if self.params.print_log:
             print(log_text)
        self.logs.append(log_text)

    def notify_order(self, order):
        """ 订单状态更新通知 """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，等待执行
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: 价格 {order.executed.price:.2f}, 数量 {order.executed.size}, 费用 {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'卖出执行: 价格 {order.executed.price:.2f}, 数量 {order.executed.size}, 费用 {order.executed.comm:.2f}')
            
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        # 重置订单状态
        self.order = None

    def notify_trade(self, trade):
        """ 交易结束通知 """
        if not trade.isclosed:
            return
        
        self.log(f'交易利润: 毛利 {trade.pnl:.2f}, 净利 {trade.pnlcomm:.2f}')
        
        # 记录交易详情
        # 计算大致的退出价格
        # PnL = (Exit - Entry) * Size * Multiplier
        # Exit = Entry + PnL / (Size * Multiplier)
        multiplier = self.params.contract_multiplier
        
        # 当交易关闭时，trade.size 为 0
        trade_size = trade.size
        if trade.isclosed:
            if len(trade.history) > 0:
                # history 记录了交易事件
                # event format: [status, dt, size, price, value, commission, pnl]
                try:
                    first_event = trade.history[0]
                    if hasattr(first_event, 'event'): 
                         event = first_event.event
                         if hasattr(event, 'size'):
                             trade_size = event.size
                         elif isinstance(event, dict):
                             trade_size = event.get('size', 0)
                    elif hasattr(first_event, 'size'):
                         trade_size = first_event.size
                    elif isinstance(first_event, (list, tuple)) and len(first_event) > 2:
                         trade_size = first_event[2]
                except Exception:
                    pass
                 
        if trade_size != 0:
            exit_price = trade.price + (trade.pnl / (trade_size * multiplier))
        else:
            exit_price = trade.price
        
        # 计算交易绩效
        entry_price = trade.price
        pnl = trade.pnl
        entry_value = abs(trade_size) * entry_price * multiplier
        return_rate = (pnl / entry_value) * 100 if entry_value != 0 else 0
        profit_points = exit_price - entry_price if trade_size > 0 else entry_price - exit_price

        # 获取交易原因
        entry_reason = "未知"
        exit_reason = "未知"
        
        if len(trade.history) > 0:
            # 尝试查找开仓订单
            # trade.history 包含订单对象或引用
            # 我们遍历 history 查找对应的 reason
            # 假设第一个是开仓，最后一个是平仓
            try:
                # 获取开仓原因
                open_order_ref = None
                close_order_ref = None
                
                # 简单处理：第一个event是开仓
                if len(trade.history) > 0:
                    first_ev = trade.history[0]
                    # Backtrader event structure is complex, often just the order object is not directly exposed as ref here easily
                    # But if we use self.order_reasons which maps order ref (int)
                    # We need to find the order ref from trade history
                    
                    # trade.history is list of list [status, dt, size, price, value, commission, pnl] usually? 
                    # No, trade.history is updated in notify_order usually.
                    # Wait, trade.history in Backtrader is a list of events.
                    # Let's rely on our own log or mapping.
                    
                    # Better approach: 
                    # We stored reasons by order.ref in self.order_reasons.
                    # But we need to know WHICH order belongs to THIS trade.
                    # Trade object has .ref (unique trade ID) but orders have their own refs.
                    # trade.history doesn't easily give order refs.
                    
                    # Alternate strategy: 
                    # When we submit order, we store reason in self.order_reasons[order.ref]
                    # In notify_order(order), if order.status == Completed, we can see if it closed a trade?
                    # No, notify_trade comes after.
                    
                    # Let's try to match by timestamp or just store last reasons?
                    # Since this is a simple strategy with one active position at a time:
                    # The "entry reason" is the reason of the LAST BUY order if we are Long, or SELL if Short.
                    # But we might have multiple trades.
                    
                    # Let's stick to simple logic:
                    # We track "latest_entry_reason" and "latest_exit_reason" in the class instance
                    # taking advantage of the sequential execution.
                    pass
            except:
                pass

        # Since we process bars sequentially and single position:
        # We can just fetch the reason stored for the orders that created this trade.
        # But `notify_trade` is called at the end.
        # Let's look at `self.trade_reasons_map` which we will populate in `notify_order`.
        
        # New approach:
        # In notify_order: if order.status == Completed:
        #   if order triggers trade open (pos=0->1), record entry reason for current position.
        #   if order triggers trade close, record exit reason.
        
        # Actually, let's just grab the text from our tracking variables.
        # We will set `self.current_trade_entry_reason` when opening.
        # And `self.current_trade_exit_reason` when closing.
        
        entry_reason = getattr(self, 'current_trade_entry_reason', '趋势信号触发')
        exit_reason = getattr(self, 'current_trade_exit_reason', '信号反转或止损')

        trade_record = {
            "entry_time": bt.num2date(trade.dtopen).strftime('%Y-%m-%d %H:%M'),
            "exit_time": bt.num2date(trade.dtclose).strftime('%Y-%m-%d %H:%M'),
            "symbol": self.datas[0]._name if hasattr(self.datas[0], '_name') else 'Unknown',
            "direction": "多" if trade_size > 0 else "空",
            "size": abs(trade_size),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "profit_points": profit_points,
            "return_rate": return_rate,
            "pnl": trade.pnl,
            "net_pnl": trade.pnlcomm,
            "commission": trade.commission,
            "bars": trade.barlen,
            "entry_reason": entry_reason,
            "exit_reason": exit_reason
        }
        self.trade_history.append(trade_record)

    def next(self):
        """ 主策略逻辑 """
        # 如果有订单正在处理，不进行新操作
        if self.order:
            return

        # 调试日志：打印当前状态 (每1个Bar打印一次，排查无交易问题)
        # 仅在数据长度较短或前几个Bar打印，避免日志过大
        if len(self) < 50 or len(self) % 100 == 0:
             self.log(f'Bar:{len(self)} Date:{self.datas[0].datetime.date(0)} Close:{self.datas[0].close[0]:.2f} SMA_F:{self.sma_fast[0]:.2f} SMA_S:{self.sma_slow[0]:.2f} Cross:{self.crossover[0]}')

        # 获取当前账户价值
        value = self.broker.get_value()
        
        # 调试信号 (每100天打一次，或者有信号时打)
        # if len(self) % 100 == 0:
        #    self.log(f'Close: {self.datas[0].close[0]:.2f}, SMA10: {self.sma_fast[0]:.2f}, SMA30: {self.sma_slow[0]:.2f}, Cross: {self.crossover[0]}')

        # 1. 没有持仓
        if not self.position:
            # 金叉买入
            if self.crossover > 0:
                # 计算止损距离
                atr_value = self.atr[0]
                stop_dist = atr_value * self.params.atr_multiplier
                self.stop_price = self.datas[0].close[0] - stop_dist
                
                # 计算仓位大小 (基于风险)
                # Risk Amount = Size * (Entry - Stop) * Multiplier
                # Size = Risk Amount / ((Entry - Stop) * Multiplier)
                risk_amount = value * self.params.risk_per_trade
                risk_per_unit = stop_dist * self.params.contract_multiplier
                
                size = 0
                if risk_per_unit > 0:
                    size = int(risk_amount / risk_per_unit)
                    self.log(f'仓位计算: 权益{value:.0f}, 风险金{risk_amount:.0f}, ATR{atr_value:.2f}, 止损距{stop_dist:.2f}, 单手风险{risk_per_unit:.2f}, 计算数量{size}')
                else:
                    self.log(f'仓位计算错误: 单手风险为0 (ATR={atr_value:.2f})')

                # 最小手数保障：如果计算为0但有资金，至少买1手
                # 同时检查资金是否足够
                available_cash = self.broker.get_cash()
                price = self.datas[0].close[0]
                # 考虑合约乘数
                max_affordable = int(available_cash / (price * self.params.contract_multiplier))
                
                if size == 0:
                    if max_affordable >= 1:
                        size = 1
                        self.log(f'调整仓位: 计算数量为0，但资金充足，尝试最小下单 1 手')
                    else:
                         self.log(f'无法开仓: 资金不足以购买 1 手 (需要 {price * self.params.contract_multiplier:.2f}, 可用 {available_cash:.2f})')
                
                # 双重检查：确保不超过最大可买数量
                if size > max_affordable:
                    size = max_affordable
                    self.log(f'资金限制: 调整仓位至最大可买数量 {size}')
                
                if size > 0:
                    self.log(f'买入信号 (金叉): 收盘价 {self.datas[0].close[0]:.2f}, ATR {atr_value:.2f}, 目标仓位 {size}')
                    self.current_trade_entry_reason = f"金叉开仓 (SMA{self.params.fast_period} > SMA{self.params.slow_period}), 风险控制: ATR={atr_value:.2f}, 仓位风险={self.params.risk_per_trade*100}%"
                    self.current_trade_exit_reason = "" # Reset exit reason
                    self.order = self.buy(size=size)
            
            # 死叉卖空
            elif self.crossover < 0:
                # 计算止损距离
                atr_value = self.atr[0]
                stop_dist = atr_value * self.params.atr_multiplier
                self.stop_price = self.datas[0].close[0] + stop_dist # 空单止损在上方
                
                # 计算仓位
                value = self.broker.get_value()
                risk_amount = value * self.params.risk_per_trade
                risk_per_unit = stop_dist * self.params.contract_multiplier
                
                size = 0
                if risk_per_unit > 0:
                    size = int(risk_amount / risk_per_unit)
                    self.log(f'做空仓位计算: 权益{value:.0f}, 风险金{risk_amount:.0f}, ATR{atr_value:.2f}, 止损距{stop_dist:.2f}, 单手风险{risk_per_unit:.2f}, 计算数量{size}')
                else:
                    self.log(f'做空仓位计算错误: 单手风险为0')

                # 做空时通常需要保证金，这里简单检查一下是否有足够权益
                # 假设保证金要求为 100% (简单处理) 或由 broker 处理
                # 这里主要处理 risk-based size 为 0 的情况
                
                if size == 0:
                    size = 1
                    self.log(f'调整做空仓位: 计算数量为0，尝试最小下单 1 手')
                
                if size > 0:
                    self.log(f'卖出开空信号 (死叉): 收盘价 {self.datas[0].close[0]:.2f}, ATR {atr_value:.2f}, 目标仓位 {size}')
                    self.current_trade_entry_reason = f"死叉开空 (SMA{self.params.fast_period} < SMA{self.params.slow_period}), 风险控制: ATR={atr_value:.2f}"
                    self.current_trade_exit_reason = "" # Reset
                    self.order = self.sell(size=size)

        # 2. 持有仓位
        else:
            # 持有多单
            if self.position.size > 0:
                # 死叉平仓
                if self.crossover < 0:
                    self.log(f'卖出平多 (死叉): 收盘价 {self.datas[0].close[0]:.2f}')
                    self.current_trade_exit_reason = f"死叉平仓 (SMA{self.params.fast_period} < SMA{self.params.slow_period})"
                    self.order = self.close() # 仅平仓
                    # 可选：反手开空 (这里简单起见，先平仓，下一个bar再看是否有机会，或者直接反手)
                    # self.order = self.sell(size=self.position.size + new_short_size) 
                
                # 移动止损
                else:
                    atr_value = self.atr[0]
                    new_stop_price = self.datas[0].close[0] - (atr_value * self.params.atr_multiplier)
                    if self.stop_price and new_stop_price > self.stop_price:
                        self.stop_price = new_stop_price
                    
                    if self.datas[0].close[0] < self.stop_price:
                        self.log(f'多单止损触发: 当前价 {self.datas[0].close[0]:.2f} < 止损价 {self.stop_price:.2f}')
                        self.current_trade_exit_reason = f"移动止损触发 (价格 {self.datas[0].close[0]:.2f} < 止损价 {self.stop_price:.2f})"
                        self.order = self.close()

            # 持有空单
            elif self.position.size < 0:
                # 金叉平仓
                if self.crossover > 0:
                    self.log(f'买入平空 (金叉): 收盘价 {self.datas[0].close[0]:.2f}')
                    self.current_trade_exit_reason = f"金叉平仓 (SMA{self.params.fast_period} > SMA{self.params.slow_period})"
                    self.order = self.close()
                
                # 移动止损 (空单止损向下移动? 不，空单止损是价格上涨时触发，止损线应该随着价格下跌而向下移动)
                else:
                    atr_value = self.atr[0]
                    # 空单：止损价在当前价上方。如果价格下跌，止损价应该跟着下跌（降低）。
                    # 初始 stop_price = Entry + ATR * M
                    # New stop potential = Current + ATR * M
                    # 我们希望 stop_price 越来越小 (Locked in profit)
                    new_stop_price = self.datas[0].close[0] + (atr_value * self.params.atr_multiplier)
                    
                    if self.stop_price and new_stop_price < self.stop_price:
                        self.stop_price = new_stop_price
                    
                    if self.datas[0].close[0] > self.stop_price:
                         self.log(f'空单止损触发: 当前价 {self.datas[0].close[0]:.2f} > 止损价 {self.stop_price:.2f}')
                         self.current_trade_exit_reason = f"移动止损触发 (价格 {self.datas[0].close[0]:.2f} > 止损价 {self.stop_price:.2f})"
                         self.order = self.close()

