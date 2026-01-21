# AI Quant Pro - UI Design System (V2.0)
**适用范围**: 股票/基金/资产配置全平台  
**设计风格**: 专业金融 (Professional Financial)、高密度 (High Density)、沉浸式 (Immersive)  
**更新日期**: 2026-01-21

## 1. 色彩系统 (Color Palette)

基于中国金融市场习惯，严格遵循**“红涨绿跌”**原则，整体采用深色模式以适应长时间盯盘需求。

### 1.1 语义色 (Semantic Colors)
| Token | Hex Value | 语义描述 | 适用场景 |
| :--- | :--- | :--- | :--- |
| `color-up` | `#F5222D` | **涨 / 买入 / 风险** | 价格上涨、买入按钮、高风险警示 |
| `color-down` | `#52C41A` | **跌 / 卖出 / 安全** | 价格下跌、卖出按钮、低风险/安全状态 |
| `color-flat` | `#FAAD14` | **平 / 观望 / 警告** | 价格持平、持有建议、一般警告 |
| `color-primary` | `#1890FF` | **品牌主色 / 交互** | 链接、选中状态、常规按钮、光标 |
| `color-bg-base` | `#000000` | **全局背景** | 应用底层背景 |
| `color-bg-card` | `#141414` | **卡片背景** | 模块容器、浮层背景 |
| `color-text-primary` | `#FFFFFF` (95%) | **主要文本** | 标题、核心数据 |
| `color-text-secondary` | `#FFFFFF` (65%) | **次要文本** | 标签、辅助说明 |
| `color-border` | `#303030` | **分割线** | 模块分割、边框 |

### 1.2 图表配色 (Chart Colors)
用于区分不同资产类别或数据系列。
*   Series 1: `#1890FF` (Blue)
*   Series 2: `#D500F9` (Purple)
*   Series 3: `#00E676` (Teal)
*   Series 4: `#FFAB00` (Amber)
*   Series 5: `#FF1744` (Red)

## 2. 排版规范 (Typography)

强调数据的可读性与数字的等宽对齐。

### 2.1 字体家族 (Font Family)
*   **数字/代码**: `'JetBrains Mono', 'Roboto Mono', Consolas, monospace` (确保数字上下对齐)
*   **常规文本**: `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif`

### 2.2 字号阶梯 (Type Scale)
| Level | Size | Weight | Line Height | 用途 |
| :--- | :--- | :--- | :--- | :--- |
| **H1** | 24px | Bold | 32px | 页面标题 / 核心资产价格 |
| **H2** | 20px | SemiBold | 28px | 模块标题 |
| **H3** | 16px | Medium | 24px | 卡片标题 / 强调数据 |
| **Body** | 14px | Regular | 22px | 正文 / 列表内容 (默认) |
| **Small** | 12px | Regular | 20px | 标签 / 辅助说明 / 脚注 |
| **Tiny** | 10px | Regular | 14px | 图表坐标轴 / 极小标签 |

## 3. 布局与间距 (Layout & Spacing)

采用 **8px 栅格系统**，强调高信息密度 (High Density)。

### 3.1 间距 Token
*   `xs`: 4px (紧凑关联元素)
*   `sm`: 8px (组件内部间距)
*   `md`: 16px (组件间距/容器内边距)
*   `lg`: 24px (模块间距)
*   `xl`: 32px (页面分区间距)

### 3.2 容器规范
*   **Glass Card**: 背景色 `#141414` + 边框 `#303030` + 圆角 `4px` (不仅是圆角，更是为了最大化利用屏幕空间，不用大圆角)。
*   **Dashboard Grid**: 采用 Bento Grid (便当盒) 布局，模块间无缝拼接或保留极小缝隙 (`8px`)。

## 4. 组件规范 (Component Specs)

### 4.1 按钮 (Buttons)
*   **Primary**: 实心蓝底白字，用于“提交”、“确认”。
*   **Trade (Buy)**: 实心红底白字，用于“买入”。
*   **Trade (Sell)**: 实心绿底白字，用于“卖出”。
*   **Ghost**: 透明底带边框，用于“取消”、“详情”。

### 4.2 数据表格 (Data Table)
*   **行高**: Compact (32px) 或 Middle (40px)，严禁使用宽松行高。
*   **对齐**: 文本左对齐，**数字右对齐**。
*   **涨跌色**: 涨跌幅列必须应用 `color-up` / `color-down`。
*   **交互**: 鼠标悬停行高亮色 `#1F1F1F`。

### 4.3 标签 (Tags)
*   **Solid**: 用于重要状态 (e.g., "持仓", "已成交")。
*   **Outline**: 用于属性标记 (e.g., "白酒", "高波动")。

## 5. 图标系统 (Iconography)

使用线性图标 (Outlined) 保持界面清爽，选中态使用实心图标 (Filled)。
*   **导航类**: 首页, 市场, 交易, 资产, 研报
*   **操作类**: 筛选, 刷新, 设置, 导出, 分享
*   **趋势类**: 上升趋势, 下降趋势, 波动, 预警 (Bell)

---
**设计原则总结**:
1.  **数据优先 (Data First)**: 一切设计元素为数据展示服务，避免过度装饰。
2.  **清晰直观 (Clarity)**: 涨跌一目了然，关键信息不折叠。
3.  **专业信赖 (Trust)**: 严谨的对齐，稳定的配色，流畅的响应。
