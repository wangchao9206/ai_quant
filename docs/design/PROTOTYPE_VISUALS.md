# Visual Prototypes (High-Fidelity ASCII)
**Version**: 1.0  
**Date**: 2026-01-21  
**Designer**: AI Quant Design Team  
**Note**: Best viewed in a monospaced font editor.

## 1. 股票深度分析终端 (Stock Deep Dive Terminal)

**Design Intent**: 
The "Cockpit" layout maximizes information density. The user focuses on the center chart, while peripheral vision monitors market status and order flow.

```text
+-----------------------------------------------------------------------------------------------+
|  [LOGO] AI Quant Pro      [ Stock ] [ Fund ] [ Wealth ]      [ Search Symbol... ] [Q] [User]  |
+-----------------------+-------------------------------------------------------+---------------+
|  MARKET WATCH         |  SH.600519  Kweichow Moutai   [ Ind: Beverage ]       |  ORDER BOOK   |
|  SSE  3200.50 ^ 1.2%  |  # 1,850.00    CNY    +2.5% ( +45.00 )                |               |
|  SZE  1050.20 v 0.5%  |  Vol: 520K   Amt: 9.8B   Turnover: 1.2%               |  S5  1850.50  |
|                       +-------------------------------------------------------+  S4  1850.40  |
|  WATCHLIST            |  [ Time ] [ Day ] [ Week ] [ Month ]  [ Indicators v] |  S3  1850.30  |
|  1. 600036  +1.5%     |                                                       |  S2  1850.20  |
|  2. 000858  +2.1%     |           |              High: 1860.00                |  S1  1850.10  |
|  3. 601318  -0.5%     |     |     |  |                                        +---------------+
|  4. 300059  +5.2%     |     |  |  |  |                                        |  B1  1850.00  |
|  5. 002594  +0.0%     |     |  |  |  |                                        |  B2  1849.90  |
|  ...                  |     |  |  |  |                                        |  B3  1849.80  |
|                       |     |  |  |  |__                                      |  B4  1849.70  |
|  SECTOR HEATMAP       |     |__|__|     |                                     |  B5  1849.60  |
|  +-------+-------+    |                 |                                     +---------------+
|  | Banks | Tech  |    |  MA5: 1845  MA20: 1830                                |  TRADE PANEL  |
|  | +0.5% | -1.2% |    |  VOL: |||||||||||||                                   |  [ Buy ] [Sell] |
|  +-------+-------+    +-------------------------------------------------------+  Limit: 1850    |
|  | Auto  | Pharm |    |  FINANCIALS      |  NEWS FLOW            |  AI ALERT  |  Qty:   100     |
|  | +2.1% | +0.8% |    |  ROE: 28.5%      |  10:30  Sector up...  |  [!] Buy   |  Est: 185,000   |
|  +-------+-------+    |  PE:  35.2x      |  10:15  Large order...|  RSRS Sig  |  [ Submit ]     |
+-----------------------+------------------+-----------------------+------------+---------------+
```

## 2. 基金智能筛选器 (Fund Smart Screener)

**Design Intent**: 
Clean, top-down flow. The "Filter Console" uses tag-based interaction for quick narrowing, followed by a detailed "Results Table" with sparklines.

```text
+-----------------------------------------------------------------------------------------------+
|  [ Fund Screener ]        Smart Fund Discovery                                     [My Funds] |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|   [ Search by Code, Manager, or Strategy (e.g. "Low Drawdown Tech")                 ] [Go]    |
|                                                                                               |
|   HOT TAGS:   ( Morningstar 5* )  ( Mgr Tenur > 5Y )  ( High Sharpe )  ( TMT Sector )         |
|                                                                                               |
|   FILTERS:                                                                                    |
|   Type:       [ All ] [ Stock ] [ Bond ] [ Hybrid ] [ Index ]                                 |
|   Return:     [ Any ] [ >10% ] [ >20% ] [ >50% ]                                              |
|   Risk:       [ Any ] [ MaxDD < 10% ] [ MaxDD < 20% ]                                         |
|   Manager:    [ Any ] [ Gold Medal ] [ Veteran (>8Y) ]                                        |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
|   RESULTS: 12 Funds Found                                              [ Export ] [ Compare ] |
+-----------------------------------------------------------------------------------------------+
|   [ ] | Fund Info              | NAV    | 1-Year Trend       | Sharpe | MaxDD  | Action       |
|  -----+------------------------+--------+--------------------+--------+--------+------------  |
|   [x] | 000001 China Asset     | 2.4512 |      _/~^\_/^      |  2.1   | -12%   | [Buy] [Dtls] |
|       | Mgr: Wang (Gold)       |        |                    |        |        |              |
|  -----+------------------------+--------+--------------------+--------+--------+------------  |
|   [ ] | 110011 E-Fund Blue     | 3.1020 |    _/^~^\_         |  1.8   | -15%   | [Buy] [Dtls] |
|       | Mgr: Zhang (Star)      |        |                    |        |        |              |
|  -----+------------------------+--------+--------------------+--------+--------+------------  |
|   [ ] | 519732 BOCOM Growth    | 4.5010 |  _/~^\_/^~^        |  2.5   | -8%    | [Buy] [Dtls] |
|       | Mgr: Yang              |        |                    |        |        |              |
+-------+------------------------+--------+--------------------+--------+--------+--------------+
```

## 3. 资产配置驾驶舱 (Wealth Cockpit)

**Design Intent**: 
Dashboard visualization. Uses Cards to group related metrics. The visual hierarchy guides the eye from "Total Assets" -> "Allocation" -> "Risk" -> "Action".

```text
+-----------------------------------------------------------------------------------------------+
|  [ Wealth Cockpit ]       Global Asset Allocation View                     [ Rebalance ]      |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|  +-----------------------+   +-----------------------+   +-----------------------+            |
|  | TOTAL ASSETS (CNY)    |   | ASSET ALLOCATION      |   | PORTFOLIO RISK        |            |
|  |                       |   |         .--.          |   |      [ Moderate ]     |            |
|  |   ¥ 1,250,400.00      |   |       .'_/__'.        |   |    Score: 65 / 100    |            |
|  |                       |   |       | Stock|        |   |                       |            |
|  |   + ¥ 12,500 (+1.0%)  |   |       '--\--'         |   |    VaR (95%): ¥5000   |            |
|  |   Today's P&L         |   |     Bond  Cash        |   |    Beta: 0.85         |            |
|  +-----------------------+   +-----------------------+   +-----------------------+            |
|                                                                                               |
|  +-----------------------------------------------+   +---------------------------------------+|
|  | CORRELATION MATRIX (Risk Detection)           |   | AI ADVISOR (Actionable)               ||
|  |          Stk  Bnd  Gold  Oil                  |   |                                       ||
|  |  Stk     1.0  0.2  0.1   0.5                  |   |  [!] High concentration in Tech.      ||
|  |  Bnd     0.2  1.0  0.3   0.1                  |   |                                       ||
|  |  Gold    0.1  0.3  1.0   0.4                  |   |  Suggest:                             ||
|  |  Oil     0.5  0.1  0.4   1.0                  |   |  1. Sell 5% QQQ (Tech ETF)            ||
|  |                                               |   |  2. Buy 5% GLD (Gold)                 ||
|  |  * Low correlation = Better Diversification   |   |                                       ||
|  +-----------------------------------------------+   |       [ Preview Order ]               ||
|                                                      +---------------------------------------+|
+-----------------------------------------------------------------------------------------------+
```

## 4. UI Component Details (Atomic Specs)

### 4.1 The "Red/Green" Switch
To support global markets later, the color semantic is defined as a token.
```
[Token: color-up]   = #F5222D (Red in CN, Green in US)
[Token: color-down] = #52C41A (Green in CN, Red in US)
```

### 4.2 The "Glass Card" Container
Visual style for all dashboard modules.
```css
.glass-card {
   background: rgba(20, 20, 20, 0.8);
   backdrop-filter: blur(12px);
   border: 1px solid rgba(48, 48, 48, 0.5);
   border-radius: 4px; /* Small radius for pro feel */
}
```

### 4.3 Typography Scale (JetBrains Mono)
Used for all pricing data.
```text
H1 Price:  3200.50  (32px, Bold)
H2 Change: +1.25%   (20px, Medium)
Body Num:  150.00   (14px, Regular)
```
