from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import Optional, List
import datetime
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from api.deps import get_db
from schemas.backtest import BacktestRequest
from core.database import BacktestRecord
from core.engine import BacktestEngine
from core.optimizer import StrategyOptimizer
from core.analysis import generate_strategy_summary

router = APIRouter()

@router.post("")
async def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    print(f"收到回测请求: {request.symbol}, {request.period}, {request.strategy_params}, 自动优化: {request.auto_optimize}, 时间段: {request.start_date} - {request.end_date}, 本金: {request.initial_cash}")
    
    strategy_class = None
    if request.strategy_code:
        try:
            print("Compiling custom strategy code...")
            local_scope = {}
            import backtrader as bt
            # Execute in a restricted scope but with bt available
            exec(request.strategy_code, {'bt': bt}, local_scope)
            if 'GeneratedStrategy' in local_scope:
                strategy_class = local_scope['GeneratedStrategy']
                print("Custom strategy 'GeneratedStrategy' loaded successfully.")
            else:
                raise ValueError("Generated code must define 'GeneratedStrategy' class")
        except Exception as e:
            print(f"Error compiling strategy: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid strategy code: {str(e)}")

    engine = BacktestEngine()
    
    # 1. 运行初始回测
    result = engine.run(
        symbol=request.symbol, 
        period=request.period, 
        strategy_params=request.strategy_params,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
        strategy_class=strategy_class
    )
    
    if "error" in result:
        print(f"Backtest execution returned error: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])
        
    # 计算初始收益率
    initial_cash = result['metrics']['initial_cash']
    final_value = result['metrics']['final_value']
    net_profit = result['metrics']['net_profit']
    return_rate = (net_profit / initial_cash) * 100
    
    # 保存初始结果
    record = BacktestRecord(
        symbol=request.symbol,
        period=request.period,
        strategy_params=request.strategy_params,
        initial_cash=initial_cash,
        final_value=final_value,
        net_profit=net_profit,
        return_rate=return_rate,
        sharpe_ratio=result['metrics']['sharpe_ratio'],
        max_drawdown=result['metrics']['max_drawdown'],
        total_trades=result['metrics']['total_trades'],
        win_rate=result['metrics']['win_rate'],
        is_optimized=0,
        equity_curve=result.get('equity_curve', []),
        logs=result.get('logs', [])
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    
    # 2. 检查是否需要自动优化
    optimized_result = None
    optimized_params = None
    optimization_msg = ""
    
    if request.auto_optimize and return_rate < 20.0:
        optimizer = StrategyOptimizer()
        best_params, best_res = optimizer.optimize(
            symbol=request.symbol, 
            period=request.period, 
            initial_params=request.strategy_params,
            target_return=20.0,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=initial_cash
        )
        
        if best_res:
             # 计算优化后的收益率
            opt_final_value = best_res['metrics']['final_value']
            opt_net_profit = best_res['metrics']['net_profit']
            opt_return_rate = (opt_net_profit / initial_cash) * 100
            
            if opt_return_rate > return_rate:
                print(f"优化成功! 新收益率: {opt_return_rate:.2f}%")
                optimized_result = best_res
                optimized_params = best_params
                optimization_msg = f"原始收益率 {return_rate:.2f}% 未达标 (<20%)。已自动优化参数，新收益率 {opt_return_rate:.2f}%。"
                
                # 保存优化后的结果
                opt_record = BacktestRecord(
                    symbol=request.symbol,
                    period=request.period,
                    strategy_params=best_params,
                    initial_cash=initial_cash,
                    final_value=opt_final_value,
                    net_profit=opt_net_profit,
                    return_rate=opt_return_rate,
                    sharpe_ratio=best_res['metrics']['sharpe_ratio'],
                    max_drawdown=best_res['metrics']['max_drawdown'],
                    total_trades=best_res['metrics']['total_trades'],
                    win_rate=best_res['metrics']['win_rate'],
                    is_optimized=1,
                    equity_curve=best_res.get('equity_curve', []),
                    logs=best_res.get('logs', [])
                )
                db.add(opt_record)
                db.commit()
            else:
                optimization_msg = "自动优化尝试未找到更好的参数组合。"
        else:
             optimization_msg = "自动优化失败，未产生有效结果。"
             
    # 构建最终响应
    response_data = result
    if optimized_result:
        response_data = optimized_result
        response_data['optimization_info'] = {
            'triggered': True,
            'message': optimization_msg,
            'original_return': return_rate,
            'optimized_return': (optimized_result['metrics']['net_profit'] / initial_cash) * 100,
            'optimized_params': optimized_params
        }
    else:
        response_data['optimization_info'] = {
            'triggered': False,
            'message': "收益率已达标或未开启自动优化" if return_rate >= 20 else "自动优化未找到更好结果"
        }

    return response_data

@router.get("/history")
async def get_backtest_history(
    skip: int = 0, 
    limit: int = 20, 
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    db: Session = Depends(get_db)
):
    query = db.query(BacktestRecord)
    
    if symbol:
        query = query.filter(BacktestRecord.symbol == symbol)
    if start_date:
        query = query.filter(BacktestRecord.timestamp >= datetime.datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(BacktestRecord.timestamp <= datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1))
    if min_return is not None:
        query = query.filter(BacktestRecord.return_rate >= min_return)
        
    total = query.count()
    
    sort_attr = BacktestRecord.timestamp
    if sort_by == "return_rate":
        sort_attr = BacktestRecord.return_rate
    elif sort_by == "sharpe_ratio":
        sort_attr = BacktestRecord.sharpe_ratio
    elif sort_by == "max_drawdown":
        sort_attr = BacktestRecord.max_drawdown
        
    if order == "asc":
        query = query.order_by(asc(sort_attr))
    else:
        query = query.order_by(desc(sort_attr))
        
    records = query.offset(skip).limit(limit).all()
    
    # 不返回大数据量的 logs 和 equity_curve 以提高列表加载速度
    result_list = []
    for r in records:
        result_list.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "symbol": r.symbol,
            "period": r.period,
            "initial_cash": r.initial_cash,
            "final_value": r.final_value,
            "net_profit": r.net_profit,
            "return_rate": r.return_rate,
            "sharpe_ratio": r.sharpe_ratio,
            "max_drawdown": r.max_drawdown,
            "total_trades": r.total_trades,
            "win_rate": r.win_rate,
            "is_optimized": r.is_optimized,
            "strategy_params": r.strategy_params
        })
        
    return {"total": total, "items": result_list}

@router.get("/history/{record_id}")
async def get_backtest_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(BacktestRecord).filter(BacktestRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    # Return full details including logs (trades) and equity_curve
    return {
        "id": record.id,
        "timestamp": record.timestamp,
        "symbol": record.symbol,
        "period": record.period,
        "initial_cash": record.initial_cash,
        "final_value": record.final_value,
        "net_profit": record.net_profit,
        "return_rate": record.return_rate,
        "sharpe_ratio": record.sharpe_ratio,
        "max_drawdown": record.max_drawdown,
        "total_trades": record.total_trades,
        "win_rate": record.win_rate,
        "is_optimized": record.is_optimized,
        "strategy_params": record.strategy_params,
        "logs": record.logs, # Contains trade list
        "equity_curve": record.equity_curve
    }

@router.get("/stats")
async def get_backtest_stats(db: Session = Depends(get_db)):
    total_count = db.query(BacktestRecord).count()
    if total_count == 0:
        return {
            "total_count": 0,
            "avg_return": 0,
            "avg_sharpe": 0,
            "avg_drawdown": 0,
            "positive_count": 0,
            "win_rate_avg": 0
        }
        
    avg_return = db.query(func.avg(BacktestRecord.return_rate)).scalar() or 0
    avg_sharpe = db.query(func.avg(BacktestRecord.sharpe_ratio)).scalar() or 0
    avg_drawdown = db.query(func.avg(BacktestRecord.max_drawdown)).scalar() or 0
    positive_count = db.query(BacktestRecord).filter(BacktestRecord.net_profit > 0).count()
    win_rate_avg = db.query(func.avg(BacktestRecord.win_rate)).scalar() or 0
    
    # 简单的收益分布 (例如：<-10%, -10~0%, 0~10%, 10~30%, >30%)
    return_dist = {
        "<-10%": db.query(BacktestRecord).filter(BacktestRecord.return_rate < -10).count(),
        "-10%~0%": db.query(BacktestRecord).filter(BacktestRecord.return_rate >= -10, BacktestRecord.return_rate < 0).count(),
        "0%~10%": db.query(BacktestRecord).filter(BacktestRecord.return_rate >= 0, BacktestRecord.return_rate < 10).count(),
        "10%~30%": db.query(BacktestRecord).filter(BacktestRecord.return_rate >= 10, BacktestRecord.return_rate < 30).count(),
        ">30%": db.query(BacktestRecord).filter(BacktestRecord.return_rate >= 30).count(),
    }
    
    return {
        "total_count": total_count,
        "avg_return": avg_return,
        "avg_sharpe": avg_sharpe,
        "avg_drawdown": avg_drawdown,
        "positive_count": positive_count,
        "win_rate_avg": win_rate_avg,
        "return_distribution": return_dist
    }

@router.get("/export")
async def export_backtest_history(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(BacktestRecord)
    if symbol:
        query = query.filter(BacktestRecord.symbol == symbol)
    if start_date:
        query = query.filter(BacktestRecord.timestamp >= datetime.datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(BacktestRecord.timestamp <= datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1))
    if min_return is not None:
        query = query.filter(BacktestRecord.return_rate >= min_return)
    
    records = query.order_by(desc(BacktestRecord.timestamp)).all()
    
    data = []
    for r in records:
        data.append({
            "ID": r.id,
            "Timestamp": r.timestamp,
            "Symbol": r.symbol,
            "Period": r.period,
            "Initial Cash": r.initial_cash,
            "Final Value": r.final_value,
            "Net Profit": r.net_profit,
            "Return Rate (%)": r.return_rate,
            "Sharpe Ratio": r.sharpe_ratio,
            "Max Drawdown (%)": r.max_drawdown,
            "Total Trades": r.total_trades,
            "Win Rate (%)": r.win_rate,
            "Is Optimized": r.is_optimized
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Backtest Records')
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="backtest_records.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/export/pdf")
async def export_backtest_history_pdf(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(BacktestRecord)
    if symbol:
        query = query.filter(BacktestRecord.symbol == symbol)
    if start_date:
        query = query.filter(BacktestRecord.timestamp >= datetime.datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(BacktestRecord.timestamp <= datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1))
    if min_return is not None:
        query = query.filter(BacktestRecord.return_rate >= min_return)
    
    records = query.order_by(desc(BacktestRecord.timestamp)).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Backtest History Report", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Data for Table
    # Limit columns to fit on page
    data = [['ID', 'Date', 'Symbol', 'Return(%)', 'Sharpe', 'Drawdown(%)', 'Trades', 'WinRate(%)']]
    for r in records:
        data.append([
            str(r.id),
            r.timestamp.strftime('%Y-%m-%d'),
            r.symbol,
            f"{r.return_rate:.2f}" if r.return_rate is not None else "0.00",
            f"{r.sharpe_ratio:.2f}" if r.sharpe_ratio is not None else "0.00",
            f"{r.max_drawdown:.2f}" if r.max_drawdown is not None else "0.00",
            str(r.total_trades),
            f"{r.win_rate:.2f}" if r.win_rate is not None else "0.00"
        ])
    
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    
    try:
        doc.build(elements)
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
        
    buffer.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="backtest_report.pdf"'
    }
    return StreamingResponse(buffer, headers=headers, media_type='application/pdf')

@router.delete("/{record_id}")
async def delete_backtest(record_id: int, db: Session = Depends(get_db)):
    record = db.query(BacktestRecord).filter(BacktestRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(record)
    db.commit()
    return {"status": "success"}

@router.get("/summary/{record_id}")
async def get_summary_report(record_id: int, db: Session = Depends(get_db)):
    record = db.query(BacktestRecord).filter(BacktestRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    summary = generate_strategy_summary(record)
    return {"summary": summary}
