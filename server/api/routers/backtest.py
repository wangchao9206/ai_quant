from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import datetime
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from api.deps import get_db
from schemas.backtest import BacktestRequest
from core.database import BacktestStore
from core.engine import BacktestEngine
from core.optimizer import StrategyOptimizer
from core.analysis import generate_strategy_summary
from core.data_loader import infer_asset_type

router = APIRouter()

@router.post("")
async def run_backtest(request: BacktestRequest, db: BacktestStore = Depends(get_db)):
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
    asset_type = request.asset_type or infer_asset_type(request.symbol)
    
    # 1. 运行初始回测
    result = engine.run(
        symbol=request.symbol, 
        period=request.period, 
        strategy_params=request.strategy_params,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
        strategy_class=strategy_class,
        asset_type=asset_type
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
    db.insert_record(
        {
            "symbol": request.symbol,
            "period": request.period,
            "strategy_params": request.strategy_params,
            "asset_type": asset_type,
            "initial_cash": initial_cash,
            "final_value": final_value,
            "net_profit": net_profit,
            "return_rate": return_rate,
            "sharpe_ratio": result["metrics"]["sharpe_ratio"],
            "max_drawdown": result["metrics"]["max_drawdown"],
            "total_trades": result["metrics"]["total_trades"],
            "win_rate": result["metrics"]["win_rate"],
            "is_optimized": 0,
            "equity_curve": result.get("equity_curve", []),
            "logs": result.get("logs", []),
        }
    )
    
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
            initial_cash=initial_cash,
            asset_type=asset_type
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
                db.insert_record(
                    {
                        "symbol": request.symbol,
                        "period": request.period,
                        "strategy_params": best_params,
                        "asset_type": asset_type,
                        "initial_cash": initial_cash,
                        "final_value": opt_final_value,
                        "net_profit": opt_net_profit,
                        "return_rate": opt_return_rate,
                        "sharpe_ratio": best_res["metrics"]["sharpe_ratio"],
                        "max_drawdown": best_res["metrics"]["max_drawdown"],
                        "total_trades": best_res["metrics"]["total_trades"],
                        "win_rate": best_res["metrics"]["win_rate"],
                        "is_optimized": 1,
                        "equity_curve": best_res.get("equity_curve", []),
                        "logs": best_res.get("logs", []),
                    }
                )
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
    db: BacktestStore = Depends(get_db)
):
    return db.list_history(
        skip=skip,
        limit=limit,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        min_return=min_return,
        sort_by=sort_by,
        order=order,
        include_big_fields=False,
    )

@router.get("/history/{record_id}")
async def get_backtest_detail(record_id: int, db: BacktestStore = Depends(get_db)):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@router.get("/stats")
async def get_backtest_stats(db: BacktestStore = Depends(get_db)):
    return db.stats()

@router.get("/export")
async def export_backtest_history(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    db: BacktestStore = Depends(get_db)
):
    records = db.export_records(symbol=symbol, start_date=start_date, end_date=end_date, min_return=min_return)
    
    data = []
    for r in records:
        data.append({
            "ID": r.get("id"),
            "Timestamp": r.get("timestamp"),
            "Symbol": r.get("symbol"),
            "Period": r.get("period"),
            "Initial Cash": r.get("initial_cash"),
            "Final Value": r.get("final_value"),
            "Net Profit": r.get("net_profit"),
            "Return Rate (%)": r.get("return_rate"),
            "Sharpe Ratio": r.get("sharpe_ratio"),
            "Max Drawdown (%)": r.get("max_drawdown"),
            "Total Trades": r.get("total_trades"),
            "Win Rate (%)": r.get("win_rate"),
            "Is Optimized": r.get("is_optimized")
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
    db: BacktestStore = Depends(get_db)
):
    records = db.export_records(symbol=symbol, start_date=start_date, end_date=end_date, min_return=min_return)
    
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
        ts = r.get("timestamp")
        if isinstance(ts, datetime.datetime):
            dt_str = ts.strftime('%Y-%m-%d')
        else:
            dt_str = str(ts)[:10] if ts else ""
        data.append([
            str(r.get("id")),
            dt_str,
            r.get("symbol"),
            f"{float(r.get('return_rate') or 0):.2f}",
            f"{float(r.get('sharpe_ratio') or 0):.2f}",
            f"{float(r.get('max_drawdown') or 0):.2f}",
            str(r.get("total_trades") or 0),
            f"{float(r.get('win_rate') or 0):.2f}"
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
async def delete_backtest(record_id: int, db: BacktestStore = Depends(get_db)):
    ok = db.delete_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success"}

@router.get("/summary/{record_id}")
async def get_summary_report(record_id: int, db: BacktestStore = Depends(get_db)):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
        
    summary = generate_strategy_summary(record)
    return {"summary": summary}
