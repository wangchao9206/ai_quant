from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import pandas as pd
import json
import os
import traceback
import importlib
from pydantic import BaseModel

from api.deps import get_db
from core.database import BacktestRecord
import core.strategy_generator

router = APIRouter()

class StrategyCodeRequest(BaseModel):
    code: str

class StrategyGenerationRequest(BaseModel):
    text: str

@router.get("/recommended")
async def get_recommended_strategies(db: Session = Depends(get_db)):
    """
    获取推荐策略：
    1. 从历史回测中筛选表现最好的 (Top 3 by Return Rate)
    2. 如果历史记录不足，补充预设的经典策略
    """
    recommendations = []
    
    # 1. 查询历史最佳
    top_records = db.query(BacktestRecord).filter(
        BacktestRecord.return_rate > 10, # 至少正收益
        BacktestRecord.total_trades > 5  # 至少有一定交易量
    ).order_by(desc(BacktestRecord.return_rate)).limit(3).all()
    
    for record in top_records:
        recommendations.append({
            "id": f"hist_{record.id}",
            "name": f"历史优选: {record.symbol} {record.period}策略",
            "description": f"基于历史回测数据筛选的高收益策略，收益率 {record.return_rate:.2f}%",
            "tags": ["高收益", "历史验证"],
            "metrics": {
                "return_rate": record.return_rate,
                "win_rate": record.win_rate,
                "max_drawdown": record.max_drawdown,
                "sharpe_ratio": record.sharpe_ratio
            },
            "config": {
                "symbol": record.symbol,
                "period": record.period,
                "strategy_params": record.strategy_params
            },
            "source": "history",
            "usage_guide": "此策略基于历史数据挖掘，建议在相似的市场环境（波动率、趋势性）下使用。请先进行模拟交易验证。",
            "risk_warning": "历史回测表现不代表未来收益。注意过拟合风险，当市场风格切换时策略可能会失效。"
        })
        
    # 2. 预设经典策略 (如果推荐不足 5 个)
    presets = [
        {
            "id": "preset_trend_conservative",
            "name": "稳健趋势跟踪",
            "description": "使用较长周期的均线组合 (20/60)，配合较宽的 ATR 止损 (3.0)，适合捕捉大趋势，交易频率较低。",
            "tags": ["稳健", "长线", "低频"],
            "metrics": {
                "return_rate": 25.5, # 模拟数据
                "win_rate": 45.0,
                "max_drawdown": 12.0,
                "sharpe_ratio": 1.5
            },
            "config": {
                "symbol": "SH0", # 默认
                "period": "daily",
                "strategy_params": {
                    "fast_period": 20,
                    "slow_period": 60,
                    "atr_period": 14,
                    "atr_multiplier": 3.0,
                    "risk_per_trade": 0.01
                }
            },
            "source": "preset",
            "usage_guide": "该策略适合在日线级别的大趋势行情中使用。建议在市场明确出现单边上涨或下跌趋势时开启。适合资金量较大、追求稳健收益的投资者。",
            "risk_warning": "由于是趋势跟踪策略，在长期震荡市中可能会出现连续小幅磨损。请耐心持有，避免频繁干预。"
        },
        {
            "id": "preset_trend_aggressive",
            "name": "激进波段策略",
            "description": "使用灵敏的均线组合 (5/20) 和较紧的止损 (1.5)，旨在捕捉短期快速波动，交易活跃，适合波动率高的品种。",
            "tags": ["激进", "短线", "高频"],
            "metrics": {
                "return_rate": 40.2, # 模拟数据
                "win_rate": 38.0,
                "max_drawdown": 25.0,
                "sharpe_ratio": 1.2
            },
            "config": {
                "symbol": "SH0",
                "period": "30", # 30分钟
                "strategy_params": {
                    "fast_period": 5,
                    "slow_period": 20,
                    "atr_period": 14,
                    "atr_multiplier": 1.5,
                    "risk_per_trade": 0.03
                }
            },
            "source": "preset",
            "usage_guide": "适合波动率较高的品种（如股指期货、黑色系）。建议在开盘后波动剧烈时段运行。适合风险偏好较高、追求高收益的投资者。",
            "risk_warning": "策略交易频率高，滑点和手续费对收益影响较大。回撤风险较高，请严格遵守止损，不建议隔夜重仓。"
        },
        {
            "id": "preset_intraday",
            "name": "日内超短线",
            "description": "基于 5 分钟 K 线的极速策略，利用 3/10 均线交叉，严格止损，不留隔夜仓。",
            "tags": ["超短线", "日内", "高风险"],
            "metrics": {
                "return_rate": 15.0, # 模拟数据
                "win_rate": 55.0,
                "max_drawdown": 5.0,
                "sharpe_ratio": 1.8
            },
            "config": {
                "symbol": "SH0",
                "period": "5",
                "strategy_params": {
                    "fast_period": 3,
                    "slow_period": 10,
                    "atr_period": 14,
                    "atr_multiplier": 1.0,
                    "risk_per_trade": 0.01
                }
            },
            "source": "preset",
            "usage_guide": "严格的日内交易策略。建议仅在主力合约活跃时段交易。每日收盘前 15 分钟请强制平仓。",
            "risk_warning": "对网络延迟和滑点极度敏感。请确保交易环境稳定。若连续亏损超过 3 次，建议当日停止交易。"
        }
    ]
    
    # 合并，去重 (简单按ID)
    existing_ids = set(r['id'] for r in recommendations)
    for p in presets:
        if p['id'] not in existing_ids:
            recommendations.append(p)
            
    return recommendations

@router.get("/correlation")
async def get_strategy_correlation(
    ids: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    query = db.query(BacktestRecord)
    
    selected_records = []
    if ids:
        try:
            id_list = [int(i) for i in ids.split(",")]
            selected_records = query.filter(BacktestRecord.id.in_(id_list)).all()
        except:
            pass
    else:
        # Default to top return strategies
        selected_records = query.order_by(desc(BacktestRecord.return_rate)).limit(limit).all()
        
    if not selected_records:
        return {"labels": [], "matrix": []}
        
    # Build DataFrame of Equity Curves
    data = {}
    for r in selected_records:
        # equity_curve is a list of dicts: [{'date': '2023-01-01', 'value': 100000, 'return': 0.0}, ...]
        if not r.equity_curve:
            continue
            
        # Parse equity curve
        dates = []
        returns = []
        # Ensure equity_curve is a list (it might be stored as JSON)
        curve = r.equity_curve
        if isinstance(curve, str):
            try:
                curve = json.loads(curve)
            except:
                curve = []
                
        for point in curve:
            if isinstance(point, dict) and 'date' in point and 'return' in point:
                dates.append(point['date'])
                returns.append(point['return'])
            
        if dates:
            # 确保 dates 里的元素都是 datetime 对象
            try:
                dt_index = pd.to_datetime(dates)
                s = pd.Series(returns, index=dt_index)
                # Label: ID - Symbol
                label = f"#{r.id} {r.symbol}"
                data[label] = s
            except Exception as e:
                print(f"Error parsing dates for record {r.id}: {e}")
                continue

    if not data:
        return {"labels": [], "matrix": []}
        
    try:
        df = pd.DataFrame(data)
        # Fill NaN with 0 (assuming neutral/no return for missing days)
        df.fillna(0, inplace=True)
        
        if df.empty:
             return {"labels": [], "matrix": []}

        corr_matrix = df.corr()
        corr_matrix.fillna(0, inplace=True) # Fill NaN correlations if any
        
        # Format for frontend
        labels = corr_matrix.columns.tolist()
        # Round to 2 decimals, handle NaN/Inf just in case
        matrix = []
        for row in corr_matrix.values.tolist():
            new_row = []
            for x in row:
                try:
                    val = round(float(x), 2)
                    if val != val: # check for NaN
                        val = 0
                    new_row.append(val)
                except:
                    new_row.append(0)
            matrix.append(new_row)
        
        return {
            "labels": labels,
            "matrix": matrix
        }
    except Exception as e:
        print(f"Error calculating correlation: {e}")
        return {"labels": [], "matrix": []}

@router.get("/code")
async def get_strategy_code():
    try:
        # Path needs to be adjusted relative to this file
        # this file: server/api/routers/strategy.py
        # core/strategy.py: server/core/strategy.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        strategy_path = os.path.join(current_dir, "../../core/strategy.py")
        strategy_path = os.path.abspath(strategy_path)
        
        with open(strategy_path, "r", encoding="utf-8") as f:
            code = f.read()
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/code")
async def save_strategy_code(request: StrategyCodeRequest):
    try:
        # 简单校验语法
        compile(request.code, "<string>", "exec")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        strategy_path = os.path.join(current_dir, "../../core/strategy.py")
        strategy_path = os.path.abspath(strategy_path)
        
        with open(strategy_path, "w", encoding="utf-8") as f:
            f.write(request.code)
        return {"status": "success", "message": "Strategy code updated successfully"}
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_strategy(request: StrategyGenerationRequest):
    try:
        # Reload to ensure latest template is used
        importlib.reload(core.strategy_generator)
        from core.strategy_generator import strategy_generator as sg
        
        result = sg.parse(request.text)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
