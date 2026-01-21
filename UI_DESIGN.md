# AI Quant 智能量化投研平台 - UI 设计规范 (V1.0)

**设计核心理念**: "Bloomberg Professional meets ChatGPT"
**关键词**: 极简 (Minimalist)、专业 (Professional)、对话驱动 (Conversational)、暗色模式 (Dark Mode)

---

## 1. 视觉风格定义 (Visual Style)

### 1.1 主题色 (Color Palette)
采用金融终端经典的深色背景，减少长期盯盘的视觉疲劳，配合高亮信号色。

*   **背景色 (Deep Space)**:
    *   `#0B0E11` (Global Background) - 接近纯黑的深蓝灰
    *   `#151A21` (Card/Panel Background) - 稍微亮一点的面板背景
*   **主色调 (Brand Identity)**:
    *   `#00F0FF` (AI Neon) - 用于 AI 对话框、高亮按钮、光标 (Cyberpunk 风格)
    *   `#2D6BFF` (Action Blue) - 用于普通链接、选中状态
*   **信号色 (Signal)**:
    *   `#00D68F` (Profit/Up) - 亮绿色，代表上涨、盈利、安全
    *   `#FF4D4D` (Loss/Down) - 亮红色，代表下跌、亏损、风险
    *   `#FFC107` (Warning) - 黄色，代表警告、相关性过高
*   **文字色 (Typography)**:
    *   `#FFFFFF` (Primary Text)
    *   `#8B949E` (Secondary Text)

### 1.2 字体系统 (Typography)
*   **UI 字体**: Inter / San Francisco / PingFang SC (清晰、现代)
*   **数据/代码字体**: JetBrains Mono / Roboto Mono (等宽，适合数字对齐)

---

## 2. 布局架构 (Layout Structure)

界面采用 **"左侧导航 + 底部AI对话 + 主工作区"** 的布局。

### 2.1 侧边导航栏 (Sidebar) - 宽度 60px/200px (可折叠)
功能入口：
1.  **📊 仪表盘 (Dashboard)**: 全局资产概览、风险雷达。
2.  **🧠 策略工场 (Strategy Lab)**: 核心功能，对话生成策略。
3.  **⏳ 时光机 (Time Machine)**: 历史回测与归因分析。
4.  **📡 市场雷达 (Market Radar)**: 实时行情与情绪监控。
5.  **⚙️ 设置 (Settings)**: 账户、API Key、风控阈值。

### 2.2 全局 AI 指令栏 (Global AI Command Bar)
*   **位置**: 屏幕底部居中 (悬浮) 或 侧边栏底部。
*   **形态**: 类似 ChatGPT 的输入框，支持语音输入图标。
*   **功能**: 随时接收自然语言指令，如 "帮我测一下双均线策略"、"现在黄金怎么样"。

### 2.3 主工作区 (Main Workspace)
*   **卡片式设计**: 每个模块（如 K 线图、策略代码、回测结果）都是一个独立的 Card。
*   **Grid 布局**: 支持拖拽调整位置，类似 TradingView 或 Bloomberg Terminal。

---

## 3. 关键页面交互设计 (Key Screens)

### 3.1 首页：风控驾驶舱 (The Cockpit)
*   **顶部**: 滚动 ticker (大盘指数涨跌)。
*   **左侧**: **"组合健康度" (Portfolio Health)**
    *   一个环形图展示仓位占比。
    *   一个雷达图展示风险暴露 (Beta, Volatility, Drawdown)。
*   **右侧**: **"市场情绪风向标" (Sentiment Gauge)**
    *   像汽车仪表盘一样，指针指向 "贪婪" 或 "恐慌"。
*   **底部**: AI 每日简报 (Daily Briefing) - "早上好，今日市场波动率较低，建议维持震荡策略..."

### 3.2 策略工场：对话即开发 (Conversational Coding)
*   **左分屏 (Chat)**: 用户与 AI 的对话流。
    *   User: "我想写一个基于布林带的策略，突破上轨做多。"
    *   AI: "好的，已为您生成。建议设置 2% 的止损，是否需要？"
*   **右分屏 (Live Code/Visual)**:
    *   **代码模式**: 显示生成的 Python 代码 (高亮)。
    *   **图表模式**: 实时显示该策略在最近 1 个月 K 线上的买卖点标记 (Preview)。
*   **交互**: 用户在左侧修改指令，右侧代码实时刷新。

### 3.3 时光机：回测报告 (The Report)
*   **核心图表**: **动态权益曲线 (Interactive Equity Curve)**。
    *   鼠标悬停显示单笔交易详情。
    *   底部附带 "水下曲线" (Drawdown Chart)，直观展示回撤痛苦期。
*   **参数高原 (3D Heatmap)**:
    *   X轴: 参数A (如均线周期), Y轴: 参数B (如止损比例), Z轴: 收益率。
    *   **视觉隐喻**: 寻找 "平坦的高原" (稳健)，避开 "尖锐的山峰" (过拟合)。

---

## 4. 交互细节 (Micro-Interactions)
*   **Loading 状态**: 使用类似 AI 思考的波纹动画 (Thinking Wave)，而不是传统的旋转圈。
*   **数据跳动**: 数字变化时，红/绿闪烁 (Ticker effect)。
*   **成功反馈**: 生成策略成功时，界面边缘闪过一道微弱的蓝光 (Cyber effect)。

---

## 5. 移动端适配 (Mobile Adaptation)
*   **卡片流**: 手机端将 Grid 布局转为垂直流式布局。
*   **精简模式**: 隐藏复杂的代码编辑，只保留 "参数调整" 和 "一键回测"。
*   **信号推送**: 像微信消息一样的卡片推送，"触发买入信号：螺纹钢，价格 3600"。
