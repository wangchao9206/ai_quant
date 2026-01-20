import backtrader as bt
import pandas as pd
import datetime
import importlib
import traceback
from .data_loader import fetch_futures_data
from . import strategy

class BacktestEngine:
    def run(self, symbol, period, strategy_params, start_date=None, end_date=None, initial_cash=1000000.0, strategy_class=None):
        StrategyClass = None

        if strategy_class:
            StrategyClass = strategy_class
        else:
            # 强制重载策略模块，确保使用最新代码
            importlib.reload(strategy)
            # 获取策略类（假设类名固定为 TrendFollowingStrategy）
            if not hasattr(strategy, 'TrendFollowingStrategy'):
                 return {"error": "Strategy class 'TrendFollowingStrategy' not found in code."}
            StrategyClass = strategy.TrendFollowingStrategy

        # 1. 继承策略以捕获日志 (动态继承)
        # 实际上我们已经在 strategy.py 里加了日志捕获，这里可以直接用
        # 但为了兼容性，我们确保 StrategyClass 是最新的
        
        # Enable trade history to get details in notify_trade
        cerebro = bt.Cerebro(tradehistory=True)

        # 2. 获取数据
        print(f"Running backtest for {symbol}...")
        df = fetch_futures_data(symbol, period, start_date, end_date)
        
        if df is None or df.empty:
            return {"error": "No data found for the given symbol and date range"}

        # Check data length
        min_length = strategy_params.get('slow_period', 30) + 5
        if len(df) < min_length:
            return {"error": f"Data length ({len(df)}) is too short for the strategy (min {min_length})"}
            
        # Determine timeframe
        if period == 'daily':
            timeframe = bt.TimeFrame.Days
            compression = 1
        elif period in ['60', '30', '15', '5']:
            timeframe = bt.TimeFrame.Minutes
            compression = int(period)
        else:
            timeframe = bt.TimeFrame.Days
            compression = 1

        print("-" * 50)
        print(f"Data Loaded: {len(df)} bars")
        print(f"Timeframe: {timeframe}, Compression: {compression}")
        print("-" * 50)
        
        system_logs = [f"Data Loaded: {len(df)} bars"]
        try:
            head_info = f"Head: {df[['Close', 'Open', 'High', 'Low']].head(1).to_dict('records')}"
            tail_info = f"Tail: {df[['Close', 'Open', 'High', 'Low']].tail(1).to_dict('records')}"
            system_logs.append(head_info)
            system_logs.append(tail_info)
        except:
            pass

        data = bt.feeds.PandasData(dataname=df, timeframe=timeframe, compression=compression)
        cerebro.adddata(data, name=symbol) # Set name for strategy to use
        
        # 3. 添加策略
        # 确保 contract_multiplier 是 int
        if 'contract_multiplier' in strategy_params:
            strategy_params['contract_multiplier'] = int(strategy_params['contract_multiplier'])
            
        # Filter params for StrategyClass to avoid "unexpected keyword argument" errors
        # especially for GeneratedStrategy which may not have all standard params defined
        strategy_kwargs = {}
        if hasattr(StrategyClass, 'params'):
            valid_params = set()
            # Inspect valid parameters from the Strategy class (Backtrader params mechanism)
            # Use dir() to get all param names (including inherited ones)
            for name in dir(StrategyClass.params):
                if not name.startswith('_'):
                    valid_params.add(name)
            
            print(f"Valid strategy params: {valid_params}")
            for k, v in strategy_params.items():
                if k in valid_params:
                    strategy_kwargs[k] = v
        else:
            strategy_kwargs = strategy_params.copy()

        cerebro.addstrategy(StrategyClass, **strategy_kwargs)
        
        # 4. 资金设置
        cerebro.broker.setcash(initial_cash)
        
        # 手续费设置 (根据品种可以做个简单映射，这里暂时通用)
        # 假设是期货，按手收费或按比例
        # 为了演示，设置一个通用费率
        # 注意：margin参数是每手保证金，如果是股票应该设为None或0，如果是期货则为具体数值
        # 这里为了防止小资金无法开仓，暂时将 margin 设为 None (按全额现金交易) 或一个较小的值
        cerebro.broker.setcommission(commission=0.0001, mult=strategy_params.get('contract_multiplier', 1))
        
        # 5. 添加分析器
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, compression=1, riskfreerate=0.0)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # 6. 运行
        try:
            # runonce=False to avoid "IndexError" with short data/complex indicators
            results = cerebro.run(runonce=False)
        except Exception as e:
            traceback.print_exc()
            return {"error": f"Backtest execution failed: {str(e)}"}

        if not results:
            return {"error": "Backtest produced no results"}
            
        strat = results[0]
        
        # 7. 提取结果
        
        # 权益曲线
        timereturns = strat.analyzers.timereturn.get_analysis()
        equity_curve = []
        cumulative = 1.0
        current_equity = initial_cash
        
        # TimeReturn 返回的是收益率，我们需要计算净值
        # Backtrader 的 TimeReturn key 是 datetime 对象
        for date, ret in timereturns.items():
            if ret is None or pd.isna(ret): ret = 0.0
            cumulative *= (1.0 + ret)
            current_equity = initial_cash * cumulative
            equity_curve.append({
                "date": date.strftime("%Y-%m-%d"),
                "value": current_equity if not pd.isna(current_equity) else 0.0,
                "return": ret
            })
            
        # 绩效指标
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe = sharpe_analysis.get('sharperatio', 0)
        if sharpe is None or pd.isna(sharpe): sharpe = 0.0
        
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)
        if max_drawdown is None or pd.isna(max_drawdown): max_drawdown = 0.0
        
        trade_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        lost_trades = trade_analysis.get('lost', {}).get('total', 0)
        
        pnl_net = trade_analysis.get('pnl', {}).get('net', {}).get('total', 0)
        
        # 准备图表数据 (OHLC + 均线)
        chart_data = {}
        try:
            # 确保按时间排序
            df_chart = df.copy()
            if not isinstance(df_chart.index, pd.DatetimeIndex):
                if 'date' in df_chart.columns:
                    df_chart['date'] = pd.to_datetime(df_chart['date'])
                    df_chart.set_index('date', inplace=True)
            
            df_chart.sort_index(inplace=True)
            
            # 计算均线
            df_chart['MA5'] = df_chart['Close'].rolling(window=5).mean()
            df_chart['MA10'] = df_chart['Close'].rolling(window=10).mean()
            df_chart['MA20'] = df_chart['Close'].rolling(window=20).mean()
            df_chart['MA60'] = df_chart['Close'].rolling(window=60).mean()
            
            # Helper to clean NaNs for JSON
            def clean_nan(x):
                return None if pd.isna(x) else x

            chart_data = {
                "dates": [d.strftime('%Y-%m-%d %H:%M') for d in df_chart.index],
                "ohlc": [[clean_nan(x) for x in row] for row in df_chart[['Open', 'Close', 'Low', 'High']].values],
                "ma5": [clean_nan(x) for x in df_chart['MA5']],
                "ma10": [clean_nan(x) for x in df_chart['MA10']],
                "ma20": [clean_nan(x) for x in df_chart['MA20']],
                "ma60": [clean_nan(x) for x in df_chart['MA60']],
                "volume": [clean_nan(x) for x in df_chart['Volume']] if 'Volume' in df_chart.columns else []
            }
        except Exception as e:
            print(f"Error preparing chart data: {e}")
            traceback.print_exc()

        return {
            "status": "success",
            "equity_curve": equity_curve,
            "chart_data": chart_data,
            "metrics": {
                "initial_cash": initial_cash,
                "final_value": cerebro.broker.getvalue(),
                "net_profit": cerebro.broker.getvalue() - initial_cash,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_drawdown,
                "total_trades": total_trades,
                "win_rate": (won_trades / total_trades * 100) if total_trades > 0 else 0,
                "won_trades": won_trades,
                "lost_trades": lost_trades
            },
            "logs": getattr(strat, 'logs', []),
            "trades": getattr(strat, 'trade_history', [])
        }
