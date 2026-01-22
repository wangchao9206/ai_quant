from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class BacktestRequest(BaseModel):
    symbol: str
    period: str
    strategy_params: Dict[str, Any]
    auto_optimize: bool = True
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: float = 1000000.0
    strategy_code: Optional[str] = None
    asset_type: Optional[str] = None
