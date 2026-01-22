import random
import copy
import multiprocessing
import platform
from concurrent.futures import ProcessPoolExecutor, as_completed
from .engine import BacktestEngine

def _run_backtest_wrapper(args):
    """
    Wrapper function for parallel execution.
    Must be top-level for pickling.
    """
    symbol, period, params, start_date, end_date, initial_cash, asset_type = args
    engine = BacktestEngine()
    result = engine.run(
        symbol=symbol,
        period=period,
        strategy_params=params,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        asset_type=asset_type
    )
    
    if "error" in result:
        return params, None, -float('inf')
        
    final_value = result['metrics']['final_value']
    net_profit = final_value - initial_cash
    return_rate = (net_profit / initial_cash) * 100
    
    # We only return metrics to save serialization overhead, 
    # unless we really need the full result (logs/equity curve)
    # Here we return the full result but we could optimize
    return params, result, return_rate

class StrategyOptimizer:
    def __init__(self):
        # We don't instantiate engine here for parallel runs
        pass
        
    def optimize(self, symbol, period, initial_params, target_return=20.0, max_trials=20, start_date=None, end_date=None, initial_cash=1000000.0, parallel=True, asset_type=None):
        """
        Parallelized Strategy Optimization
        """
        best_result = None
        best_return = -float('inf')
        best_params = initial_params.copy()
        
        # Define parameter search space
        param_ranges = {
            'fast_period': list(range(5, 30, 2)),
            'slow_period': list(range(20, 100, 5)),
            'atr_period': [10, 14, 20, 30],
            'atr_multiplier': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            'risk_per_trade': [0.01, 0.02, 0.03, 0.05]
        }
        
        print(f"Starting optimization... Target: >{target_return}%, Trials: {max_trials}, Parallel: {parallel}")
        
        # Generate all trial parameters first
        trials = []
        for i in range(max_trials):
            trial_params = initial_params.copy()
            num_mutations = random.randint(1, 3)
            keys_to_mutate = random.sample(list(param_ranges.keys()), num_mutations)
            
            for key in keys_to_mutate:
                if key in param_ranges:
                    trial_params[key] = random.choice(param_ranges[key])
            
            # Constraint: fast < slow
            if 'fast_period' in trial_params and 'slow_period' in trial_params:
                if trial_params['fast_period'] >= trial_params['slow_period']:
                    trial_params['slow_period'] = trial_params['fast_period'] + 5
            
            trials.append((symbol, period, trial_params, start_date, end_date, initial_cash, asset_type))
            
        if parallel:
            # Use ProcessPoolExecutor for parallel execution
            # Note: On Windows, max_workers usually defaults to cpu_count()
            # We limit it to avoid system freeze if needed, but default is usually fine
            with ProcessPoolExecutor() as executor:
                futures = [executor.submit(_run_backtest_wrapper, args) for args in trials]
                
                for i, future in enumerate(as_completed(futures)):
                    try:
                        params, result, return_rate = future.result()
                        print(f"Trial #{i+1} finished. Return: {return_rate:.2f}%")
                        
                        if return_rate > best_return:
                            best_return = return_rate
                            best_result = result
                            best_params = params
                            
                        if best_return > target_return:
                            print(f"Target return reached! Note: In parallel mode, other tasks may still complete.")
                            # In parallel, breaking doesn't stop others immediately unless we cancel futures
                            # For simplicity, we let them finish or just break the collection loop
                            # To truly stop, we'd need executor.shutdown(wait=False, cancel_futures=True) in Py3.9+
                            break
                    except Exception as e:
                        print(f"Trial failed: {e}")
        else:
            # Sequential fallback
            engine = BacktestEngine()
            for i, args in enumerate(trials):
                # Unpack args
                _, _, params, _, _, _ = args
                print(f"Trial #{i+1}: {params}")
                result = engine.run(symbol, period, params, start_date, end_date, initial_cash, asset_type=asset_type)
                
                if "error" in result: continue
                
                final_value = result['metrics']['final_value']
                net_profit = final_value - initial_cash
                return_rate = (net_profit / initial_cash) * 100
                
                print(f"  -> Return: {return_rate:.2f}%")
                
                if return_rate > best_return:
                    best_return = return_rate
                    best_result = result
                    best_params = params
                    
                if best_return > target_return:
                    print("Target reached.")
                    break
                    
        return best_params, best_result
