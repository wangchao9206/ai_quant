# Page Wireframes & Layout Specs
**Version**: 1.0  
**Date**: 2026-01-21  
**Grid System**: 12-Column Grid (Ant Design Standard)

## 1. 股票深度分析终端 (Stock Deep Dive Terminal)

**布局结构**: 三栏式布局 (Left: 20%, Center: 60%, Right: 20%)

### Left Column: 市场概览 (Market Watch)
*   **Top**: 迷你指数卡片 (上证/深证/创业板) - 实时跳动。
*   **Middle**: 自选股列表 (Symbol List) - 紧凑行高，仅展示 Name, Price, Chg%。
*   **Bottom**: 快速板块轮动 (Sector Rotation) - 热力条。

### Center Column: 核心分析区 (Core Analysis)
*   **Header**: 个股抬头 (Name + Code + Big Price) + 核心标签 (Tag: "白酒龙头", "高ROE").
*   **Main Chart**: 
    *   Tab 1: **TradingView K-Line** (支持画图、多指标)。
    *   Tab 2: **分时图** (叠加量比、大单)。
    *   Tab 3: **深度图** (Level-2 Order Book).
*   **Sub-Module 1 (Fundamental)**: 财务三张表可视化 (Revenue/Profit Bar Chart)。
*   **Sub-Module 2 (News)**: 舆情时间轴 (News Timeline)。

### Right Column: 交易与AI (Trade & AI)
*   **Top**: 盘口五档 (Level-1 Quote) - 传统的买五卖五列表。
*   **Middle**: **AI 信号吹哨 (Signal Alert)**.
    *   UI: 类似 Twitter 信息流，实时推送 "MA5上穿MA20", "主力净流入超1亿"。
*   **Bottom**: 交易面板 (Trade Panel) - 快速下单入口 (Buy/Sell/Quantity)。

---

## 2. 基金智能筛选器 (Fund Smart Screener)

**布局结构**: 上下结构 (Top: Filter, Bottom: Results)

### Top Area: 筛选控制台 (Filter Console)
*   **Search Bar**: 居中大搜索框，支持自然语言 ("Search for low volatility tech funds").
*   **Quick Tags**: 热门标签行 (Button Group: "晨星五星", "双十经理", "金牛奖").
*   **Advanced Filters**: 
    *   Row 1: 基金类型 (股票/混合/债券/指数).
    *   Row 2: 业绩区间 (近1月/3月/1年/3年).
    *   Row 3: 风险指标 (最大回撤 < 10%, Sharpe > 2).
    *   *Interaction*: 选中标签高亮蓝底白字。

### Bottom Area: 结果透视表 (Results Table)
*   **Header**: "共筛选出 123 只基金".
*   **Table Columns**:
    1.  **基金信息**: 代码 + 名称 + 经理头像 (Avatar).
    2.  **净值**: 数值 + 日期.
    3.  **业绩 (Sparkline)**: 嵌入迷你折线图展示近一年走势。
    4.  **风险**: 动态最大回撤条 (Progress Bar).
    5.  **操作**: "加入对比" (Checkbox) + "定投" (Button).

---

## 3. 资产配置驾驶舱 (Wealth Cockpit)

**布局结构**: 仪表盘卡片式 (Dashboard Cards)

### Row 1: 核心资产总览 (Assets Summary)
*   **Card A (Total Asset)**: 总资产数字 (超大字号) + 昨日盈亏。
*   **Card B (Allocation Pie)**: 环形图 (Equity / Bond / Cash / Other)。
    *   *Visual*: 环形中间显示最大占比的资产类别。
*   **Card C (Risk Gauge)**: 仪表盘显示当前组合风险评分 (0-100)。

### Row 2: 穿透分析 (Look-through Analysis)
*   **Card D (Correlation Matrix)**: 
    *   热力图矩阵 (Heatmap)，展示持仓资产间的相关性。
    *   *Rule*: 相关性 > 0.8 显示红色警告。
*   **Card E (Geography Map)**: 世界地图，展示资产的国别分布 (CN/US/HK/EU)。

### Row 3: 智能投顾建议 (Robo-Advisor)
*   **Layout**: 左右分栏。
*   **Left**: "当前组合问题" (e.g., "科技板块暴露度过高").
*   **Right**: "优化建议" (e.g., "建议卖出 10% 纳指ETF，买入 黄金ETF").
*   **Action**: "一键调仓" 按钮 (Primary Color).
