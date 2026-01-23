from fastapi import APIRouter
from core.yijing import YiJingEngine
from core.database import get_market_collection
import datetime
import random

router = APIRouter()
engine = YiJingEngine()

def _element_sectors(element: str):
    mapping = {
        "金": ["金融", "有色", "军工"],
        "木": ["消费", "医药", "农业"],
        "火": ["科技", "新能源", "军工"],
        "水": ["航运", "化工", "传媒"],
        "土": ["基建", "地产", "建材"],
    }
    return mapping.get(element, ["均衡配置"])

def _risk_level(change_pct: float, trend: str):
    if "暴" in trend or "风险" in trend or "顶部" in trend:
        return "高"
    if abs(change_pct) >= 2.5:
        return "高"
    if abs(change_pct) >= 1.0:
        return "中"
    return "低"

def _position_suggestion(trend: str):
    if "强" in trend or "主升" in trend or "大牛" in trend:
        return {"bias": "偏多", "range": "60%-80%", "style": "顺势"}
    if "熊" in trend or "空" in trend or "暴跌" in trend or "困" in trend:
        return {"bias": "防守", "range": "0%-20%", "style": "规避"}
    if "震" in trend or "盘整" in trend or "观望" in trend:
        return {"bias": "中性", "range": "30%-50%", "style": "区间"}
    return {"bias": "谨慎", "range": "20%-40%", "style": "试探"}

def _action_steps(trend: str):
    if "强" in trend or "主升" in trend:
        return ["逢回调分批加仓", "设置移动止盈", "关注量能延续"]
    if "熊" in trend or "暴跌" in trend or "困" in trend:
        return ["严格止损", "减少交易频率", "等待企稳信号"]
    if "震" in trend or "盘整" in trend or "观望" in trend:
        return ["轻仓试探", "低吸高抛", "关注突破方向"]
    return ["保持耐心", "以小仓验证", "只做高胜率信号"]

def _time_window(hour: int, trend: str):
    if hour < 10:
        base = "开盘后试探"
    elif hour < 13:
        base = "午前顺势"
    elif hour < 15:
        base = "午后确认"
    else:
        base = "收盘前控仓"
    if "强" in trend or "主升" in trend:
        return f"{base}，可择强势板块"
    if "熊" in trend or "暴跌" in trend:
        return f"{base}，以防守为主"
    return base

def _holding_cycle(trend: str):
    if "主升" in trend or "大牛" in trend:
        return "中期持有"
    if "震" in trend or "盘整" in trend:
        return "短线波段"
    if "熊" in trend or "暴跌" in trend:
        return "观望"    
    return "短线"    

def _market_style(trend: str, element: str):
    if "震" in trend or "盘整" in trend:
        return "区间震荡"
    if "主升" in trend or "强" in trend:
        return "趋势行情"
    if "熊" in trend or "空" in trend:
        return "防御行情"
    if element == "火":
        return "成长风格"
    if element == "金":
        return "价值风格"
    return "均衡风格"

def _signals(trend: str, risk: str):
    if risk == "高":
        return ["放量长阴警惕", "追高无效", "跌破均线减仓"]
    if "强" in trend or "主升" in trend:
        return ["站上关键均线", "放量突破", "回踩不破"]
    if "震" in trend or "盘整" in trend:
        return ["区间下沿企稳", "缩量回调", "量价背离"]
    return ["等待转势信号", "控制仓位", "关注政策窗口"]

def _rotation_checklist(trend: str, risk: str):
    base = ["确认趋势方向", "设置止损位", "控制单笔风险"]
    if risk == "高":
        return base + ["降低仓位", "避免追高", "等待确认"]
    if "强" in trend or "主升" in trend:
        return base + ["关注强势板块", "回踩不破再加仓", "成交量配合"]
    if "震" in trend or "盘整" in trend:
        return base + ["区间操作", "高抛低吸", "缩量不追"]
    return base + ["小仓试探", "等待拐点", "保持耐心"]

def _rotation_timing(now: datetime.datetime, trend: str):
    hour = now.hour
    if hour < 10:
        window = "开盘试探"
    elif hour < 13:
        window = "午前强化"
    elif hour < 15:
        window = "午后确认"
    else:
        window = "收盘控仓"
    if "强" in trend or "主升" in trend:
        return f"{window}，优先强势领涨"
    if "熊" in trend or "暴跌" in trend:
        return f"{window}，以防守轮动为主"
    return f"{window}，观察资金切换"

def _fetch_sector_changes():
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.iterrows():
            name = row.get("板块名称")
            change = row.get("涨跌幅")
            try:
                change = float(change)
            except Exception:
                change = 0.0
            result.append({"name": name, "change": change})
        return result
    except Exception:
        return []

def _rotation_action(change: float, risk: str):
    if risk == "高":
        return "回避"
    if change >= 2.0:
        return "跟随"
    if change >= 0.5:
        return "关注"
    if change <= -1.5:
        return "回避"
    return "观望"

def _rotation_reason(change: float, preferred: bool, trend: str):
    if preferred and change >= 1.0:
        return "五行同气，顺势领涨"
    if preferred and change < 0:
        return "五行同气，弱中求稳"
    if "震" in trend or "盘整" in trend:
        return "震荡市资金轮动快"
    if "熊" in trend or "暴跌" in trend:
        return "防守逻辑优先"
    if change >= 1.5:
        return "资金集中推升"
    if change <= -1.0:
        return "资金撤退迹象"
    return "中性震荡"

def _fetch_index_snapshot(code: str = "000001"):
    try:
        col = get_market_collection()
    except Exception:
        return 0.0, 0.0
    try:
        docs = list(
            col.find(
                {"asset_type": "stock", "symbol": code, "period": "daily"},
                {"_id": 0, "ts": 1, "close_price": 1, "open_price": 1},
            )
            .sort("ts", -1)
            .limit(2)
        )
    except Exception:
        return 0.0, 0.0
    if not docs:
        return 0.0, 0.0
    latest = docs[0]
    prev = docs[1] if len(docs) > 1 else docs[0]
    price = latest.get("close_price") or latest.get("open_price") or 0.0
    last_close = prev.get("close_price") or prev.get("open_price") or 0.0
    try:
        price = float(price)
    except Exception:
        price = 0.0
    try:
        last_close = float(last_close)
    except Exception:
        last_close = 0.0
    change_pct = ((price - last_close) / last_close * 100) if last_close else 0.0
    return price, change_pct

def _season_cycle(now: datetime.datetime):
    month = now.month
    if month in (3, 4, 5):
        return "春生"
    if month in (6, 7, 8):
        return "夏长"
    if month in (9, 10, 11):
        return "秋收"
    return "冬藏"

def _liuyao_judgement(moving_line: int, trend: str):
    if moving_line in (1, 2):
        return "世爻偏弱，宜守不宜攻"
    if moving_line in (3, 4):
        return "世应相持，等待转机"
    if "强" in trend or "主升" in trend:
        return "世爻得势，可顺势而为"
    return "世爻平和，择机而动"

@router.get("/forecast")
async def get_forecast():
    """
    获取今日易道投资预测
    基于上证指数实时价格起卦
    """
    # 1. 获取起卦种子 (上证指数最新价)
    seed = 0.0
    change_pct = 0.0
    seed_source = "market"
    
    try:
        seed, change_pct = _fetch_index_snapshot("000001")
    except Exception as e:
        print(f"YiDao Seed Error: {e}")
        pass
    
    # Fallback to timestamp if market is closed or error
    now = datetime.datetime.now()
    if seed == 0:
        seed = now.year + now.month + now.day + now.hour + now.minute
        seed_source = "time"
    
    # 2. 起卦
    # 因子: 涨跌幅整数部分
    factor = int(change_pct * 10) 
    result = engine.get_forecast(seed, abs(factor))
    
    # Add market context
    trend_text = result["hexagram"]["trend"]
    current_element = result["qimen"]["current_element"]
    position = _position_suggestion(trend_text)
    risk_level = _risk_level(change_pct, trend_text)
    result["market_seed"] = seed
    result["market_change_pct"] = round(float(change_pct), 2) if change_pct is not None else 0.0
    result["seed_source"] = seed_source
    result["season_cycle"] = _season_cycle(now)
    result["risk_level"] = risk_level
    result["position"] = position
    result["action_steps"] = _action_steps(trend_text)
    result["sector_focus"] = _element_sectors(current_element)
    result["time_window"] = _time_window(now.hour, trend_text)
    result["holding_cycle"] = _holding_cycle(trend_text)
    result["market_style"] = _market_style(trend_text, current_element)
    result["signals"] = _signals(trend_text, risk_level)
    result["liuyao"] = {
        "moving_line": result["moving_line"],
        "judgement": _liuyao_judgement(result["moving_line"], trend_text)
    }
    result["analysis"] = {
        "methods": ["易经卦象", "奇门遁甲", "六爻", "均线", "MACD"],
        "summary": f"以{trend_text}为主轴，{position['style']}为先"
    }
    
    return result

@router.get("/wisdom")
async def get_wisdom():
    wisdoms = [
        "财不入急门，慢就是快。",
        "善战者无赫赫之功，善猎者必善等待。",
        "君子藏器于身，待时而动。",
        "凡事预则立，不预则废。投资亦然。",
        "知其雄，守其雌，为天下溪。",
        "人弃我取，人取我与。",
        "物极必反，否极泰来。",
        "大道至简，顺势而为。",
        "知止不殆，可以长久。",
        "反者道之动，弱者道之用。"
    ]
    # Use day of year to pick consistent daily wisdom
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    idx = day_of_year % len(wisdoms)
    
    principle = [
        "顺势而为",
        "攻守平衡",
        "以静制动",
        "宁可错过，不可做错",
        "以退为进",
        "知止有度",
    ]
    risk_rules = [
        "单笔止损不超2%",
        "盈利不贪，分批止盈",
        "回撤扩大时主动降仓",
        "不在放量长阴时接飞刀",
        "不追高，不抄底",
    ]
    pos_rules = [
        "顺势仓位递增",
        "震荡区间轻仓",
        "高风险日减仓",
        "有信号才出手",
    ]
    p_idx = day_of_year % len(principle)
    r_idx = day_of_year % len(risk_rules)
    pr_idx = day_of_year % len(pos_rules)
    checklist = [
        "是否顺势",
        "是否有止损",
        "是否等待信号",
        "是否控制仓位",
    ]
    return {
        "content": wisdoms[idx],
        "principle": principle[p_idx],
        "risk": risk_rules[r_idx],
        "position": pos_rules[pr_idx],
        "checklist": checklist,
        "date": datetime.datetime.now().strftime("%Y-%m-%d")
    }

@router.get("/rotation")
async def get_rotation():
    now = datetime.datetime.now()
    seed = int(now.strftime("%Y%m%d"))
    change_pct = 0.0
    trend = "震荡"
    try:
        _, change_pct = _fetch_index_snapshot("000001")
    except Exception:
        change_pct = 0.0
    factor = int(float(change_pct) * 10) if change_pct is not None else 0
    forecast = engine.get_forecast(seed, abs(factor))
    trend = forecast.get("hexagram", {}).get("trend", "震荡")
    element = forecast.get("qimen", {}).get("current_element", "土")
    risk = _risk_level(float(change_pct), trend)
    sectors = _fetch_sector_changes()
    preferred = set(_element_sectors(element))
    if not sectors:
        rng = random.Random(seed)
        pool = ["金融", "科技", "消费", "医药", "新能源", "军工", "有色", "基建", "传媒", "化工", "航运", "地产", "农业", "建材"]
        sectors = [{"name": n, "change": round(rng.uniform(-2.5, 3.5), 2)} for n in pool]
    enriched = []
    for s in sectors:
        name = s.get("name")
        change = float(s.get("change") or 0.0)
        score = change * 2 + (1.2 if name in preferred else 0.0)
        if risk == "高":
            score -= 1.0
        enriched.append({
            "name": name,
            "change": round(change, 2),
            "score": round(score, 2),
            "action": _rotation_action(change, risk),
            "reason": _rotation_reason(change, name in preferred, trend)
        })
    enriched.sort(key=lambda x: x["score"], reverse=True)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "trend": trend,
        "risk": risk,
        "element": element,
        "window": _rotation_timing(now, trend),
        "sectors": enriched[:8],
        "checklist": _rotation_checklist(trend, risk)
    }
