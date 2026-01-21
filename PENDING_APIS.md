# 待对接后端接口文档

以下接口为前端页面（AI Quant Pro 2026）当前所需的后端接口清单。目前前端已完成对接代码改造，请后端开发参考以下规范尽快实现。

## 1. 市场复盘 (Market Replay)

**涉及页面**: `web/src/components/tools/MarketReplay.jsx`

### 1.1 获取复盘K线数据
*   **接口路径**: `GET /api/market/replay/kline`
*   **描述**: 获取用于市场复盘训练的历史K线数据及关键帧标记。
*   **请求参数**: 无 (未来可扩展 `symbol`, `date` 等)
*   **返回结构**:
    ```json
    {
      "data": [
        {
          "time": "09:30",
          "values": [3000.0, 3010.0, 2990.0, 3020.0], // [Open, Close, Low, High]
          "vol": 10000
        }
      ],
      "key_frames": [
        {
          "index": 15,
          "type": "min_price", // "min_price" | "max_price"
          "label": "日内低点",
          "value": 2990.0
        }
      ]
    }
    ```

## 2. 宏观日历 (Macro Calendar)

**涉及页面**: `web/src/components/tools/MacroCalendar.jsx`

### 2.1 获取宏观经济事件
*   **接口路径**: `GET /api/market/macro/calendar`
*   **描述**: 获取指定日期和国家的宏观经济数据发布日程。
*   **请求参数**:
    *   `date` (string): 日期，格式 `YYYY-MM-DD`
    *   `countries` (string): 国家代码列表，逗号分隔，如 `US,CN,EU`
*   **返回结构**:
    ```json
    [
      {
        "id": 1,
        "time": "20:30",
        "country": "US",
        "currency": "USD",
        "event": "非农就业人口",
        "importance": "high", // "high" | "medium" | "low"
        "actual": "21.6",
        "forecast": "17.0",
        "previous": "17.3",
        "impact": "利空金银"
      }
    ]
    ```

## 3. 舆情分析 (Sentiment Radar)

**涉及页面**: `web/src/components/tools/SentimentRadar.jsx`

### 3.1 获取情绪概览
*   **接口路径**: `GET /api/analysis/sentiment/overview`
*   **描述**: 获取当前市场情绪评分及趋势。
*   **返回结构**:
    ```json
    {
      "score": 78, // 0-100
      "status": "贪婪", // "极度恐慌" | "恐惧" | "中性" | "贪婪" | "极度贪婪"
      "trend": [65, 68, 72, 70, 75, 78, 82, 78] // 最近8小时趋势
    }
    ```

### 3.2 获取热门话题
*   **接口路径**: `GET /api/analysis/sentiment/topics`
*   **描述**: 获取当前市场热门讨论话题/概念词云数据。
*   **返回结构**:
    ```json
    [
      {
        "text": "人工智能",
        "weight": 10, // 权重，决定字体大小
        "sentiment": "bullish" // "bullish" | "bearish" | "neutral"
      }
    ]
    ```

### 3.3 获取智能新闻流
*   **接口路径**: `GET /api/analysis/sentiment/news`
*   **描述**: 获取经过AI分析的实时新闻流。
*   **返回结构**:
    ```json
    [
      {
        "id": 1,
        "title": "某科技巨头发布新芯片",
        "source": "路透社",
        "time": "10分钟前",
        "impact": 85, // 影响力评分 0-100
        "sentiment": "bullish",
        "analysis": "利好算力板块"
      }
    ]
    ```

## 4. 风控中心 (Risk Center)

**涉及页面**: `web/src/components/tools/RiskCenter.jsx`

### 4.1 获取风控指标
*   **接口路径**: `GET /api/analysis/risk/metrics`
*   **描述**: 获取组合层面的核心风控指标。
*   **返回结构**:
    ```json
    {
      "var95": 12500,
      "var99": 18000,
      "beta": 1.12,
      "sharpe": 1.85,
      "maxDrawdown": -12.5
    }
    ```

### 4.2 获取资产相关性矩阵
*   **接口路径**: `GET /api/analysis/risk/correlation`
*   **描述**: 获取资产间的相关性数据，用于热力图展示。
*   **返回结构**:
    ```json
    {
      "assets": ["股票", "债券", "黄金", "原油", "现金"],
      "matrix": [
        [0, 0, 1.0], // [xIndex, yIndex, correlationValue]
        [0, 1, -0.2]
      ]
    }
    ```

### 4.3 获取压力测试结果
*   **接口路径**: `GET /api/analysis/risk/stress-test`
*   **描述**: 获取不同极端情景下的组合压力测试表现。
*   **返回结构**:
    ```json
    [
      {
        "scenario": "2008 金融危机重演",
        "impact": "-25.4%",
        "probability": "Low"
      }
    ]
    ```

## 5. 股票深度分析 (Stock Dashboard)

**涉及页面**: `web/src/components/StockDashboard.jsx`

### 5.1 获取市场指数行情
*   **接口路径**: `GET /api/market/indices`
*   **描述**: 获取主要市场指数（上证、深证、创业板等）的实时行情。
*   **返回结构**:
    ```json
    [
      {
        "name": "上证指数",
        "value": 3200.50,
        "change": 1.25,
        "volume": "4500亿"
      }
    ]
    ```

### 5.2 获取个股深度行情
*   **接口路径**: `GET /api/stock/quote`
*   **请求参数**: `symbol` (e.g., "600519")
*   **描述**: 获取个股的详细报价及基本面数据。
*   **返回结构**:
    ```json
    {
      "name": "贵州茅台",
      "code": "600519",
      "price": 1850.00,
      "change": 2.50,
      "changeAmt": 45.00,
      "open": 1810.00,
      "high": 1860.00,
      "low": 1805.00,
      "vol": "5.2万",
      "amt": "98亿",
      "pe": 35.2,
      "pb": 8.5
    }
    ```

### 5.3 获取盘口数据 (Level-2)
*   **接口路径**: `GET /api/stock/orderbook`
*   **请求参数**: `symbol` (e.g., "600519")
*   **描述**: 获取五档买卖盘口数据。
*   **返回结构**:
    ```json
    {
      "asks": [{"p": 1850.50, "v": 12}, ...], // 卖盘 [价格, 量]
      "bids": [{"p": 1850.00, "v": 345}, ...] // 买盘
    }
    ```

### 5.4 获取板块热度
*   **接口路径**: `GET /api/market/sectors`
*   **描述**: 获取当前热门板块及其涨跌幅。
*   **返回结构**:
    ```json
    [
      { "name": "白酒", "change": 2.5 },
      { "name": "新能源", "change": -1.2 }
    ]
    ```

### 5.5 获取日内分时/K线
*   **接口路径**: `GET /api/stock/intraday`
*   **请求参数**: `symbol` (e.g., "600519")
*   **描述**: 获取当日的分时走势或分钟K线数据。
*   **返回结构**:
    ```json
    {
        "times": ["09:30", "09:31", ...],
        "values": [
            [1810, 1820, 1805, 1825], // [Open, Close, Low, High]
            ...
        ]
    }
    ```

## 6. 基金筛选 (Fund Dashboard)

**涉及页面**: `web/src/components/FundDashboard.jsx`
*(新增)*

### 6.1 获取基金列表
*   **接口路径**: `GET /api/fund/list`
*   **描述**: 获取推荐的基金列表及关键指标。
*   **返回结构**:
    ```json
    [
      {
        "key": "1",
        "code": "000001",
        "name": "华夏成长混合",
        "manager": "王经理",
        "type": "Hybrid",
        "nav": "2.4512",
        "return1y": 15.2,
        "sharpe": 2.1,
        "maxdd": -12
      }
    ]
    ```

## 7. 衍生品 (Derivatives Dashboard)

**涉及页面**: `web/src/components/DerivativesDashboard.jsx`
*(新增)*

### 7.1 获取期货主力合约
*   **接口路径**: `GET /api/derivatives/futures`
*   **描述**: 获取主要期货合约的实时行情。
*   **返回结构**:
    ```json
    [
      {
        "symbol": "IF2312",
        "name": "沪深300主力",
        "price": 3520.4,
        "change": 1.2,
        "volume": "12.5W",
        "openInt": "4.2W",
        "basis": 12.5
      }
    ]
    ```

### 7.2 获取期权T型报价
*   **接口路径**: `GET /api/derivatives/options`
*   **描述**: 获取期权链数据。
*   **返回结构**:
    ```json
    [
      {
        "callPrice": 150, "callVol": 2000, "strike": 3500, "putVol": 1500, "putPrice": 45
      }
    ]
    ```

## 8. 大宗商品 (Commodities Dashboard)

**涉及页面**: `web/src/components/CommoditiesDashboard.jsx`
*(新增)*

### 8.1 获取商品行情列表
*   **接口路径**: `GET /api/commodities/list`
*   **描述**: 获取贵金属和大宗商品的实时报价。
*   **返回结构**:
    ```json
    [
      {
        "name": "Gold (伦敦金)",
        "price": 2045.50,
        "change": 0.85,
        "unit": "USD/oz"
      }
    ]
    ```

### 8.2 获取商品走势图
*   **接口路径**: `GET /api/commodities/chart`
*   **描述**: 获取商品的走势图数据。
*   **返回结构**:
    ```json
    {
      "times": ["09:00", ...],
      "values": [2040, 2042, ...]
    }
    ```

### 8.3 获取宏观驱动因子
*   **接口路径**: `GET /api/commodities/macro`
*   **描述**: 获取影响大宗商品的宏观指标。
*   **返回结构**:
    ```json
    [
      {
        "name": "美元指数 (DXY)",
        "value": "103.5",
        "change": "-0.2%",
        "percent": 70,
        "status": "low" // color logic
      }
    ]
    ```
