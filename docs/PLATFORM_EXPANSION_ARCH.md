# AI Quant Platform Expansion Architecture
**Version**: 1.0  
**Date**: 2026-01-21  
**Objective**: Transform from a specialized Quant Tool to a Comprehensive Wealth Management Platform for the Chinese Market.

## 1. Functional Architecture (功能架构)

The platform will be reorganized into three core pillars:

### 1.1 Smart Equity (智能股票) - For Active Traders
*   **Real-time Analytics**: Tick-level data processing, Dynamic K-line (TradingView integration), Technical Indicator scanning.
*   **Deep Research**: Financial statement visualization (DuPont Analysis), Peer comparison, Valuation modeling (DCF/PE/PB).
*   **Quant Lab**: Existing backtesting engine + Smart Strategy Generation (NLP).
*   **Risk Sentinel**: Real-time signal alerts, Margin monitoring.

### 1.2 Smart Fund (智慧基金) - For Passive/Allocators
*   **Fund Screener**: Multi-factor filtering (Sharpe, MaxDrawdown, Alpha, Manager Tenure).
*   **Manager 360**: Manager track record analysis, Style drift detection, Attribution analysis (Brinson).
*   **Smart SIP**: Systematic Investment Plan calculator with backtesting capability.
*   **Fund Diagnostic**: "Health Check" for existing fund portfolios.

### 1.3 Smart Allocation (智投配置) - For HNW Individuals
*   **Robo-Advisor**: Risk profiling (KYC) -> Portfolio generation (Markowitz/Black-Litterman).
*   **Cross-Asset View**: Correlation matrix across Stocks, Bonds, Gold, Commodities.
*   **REITs/Derivatives**: Specialized modules for alternative assets.

## 2. Technical Architecture (技术架构)

### 2.1 Frontend (React + Ant Design Pro)
*   **Micro-Frontend approach**: 
    *   `ModuleStock`: Existing backtest + new Analysis components.
    *   `ModuleFund`: New components for Fund Screening & Analysis.
    *   `ModuleAsset`: Portfolio management visualization.
*   **Data Visualization**: Heavy use of ECharts for financial charts and D3.js for relationship graphs.

### 2.2 Backend (FastAPI + Python)
*   **Service Layering**:
    *   `Core Engine`: Backtesting & Quant logic.
    *   `Data Service`: Adapters for AkShare/Tushare/JQData.
    *   `Analysis Service`: Calculation engines for Fund Alpha/Beta, Attribution.
*   **Data Storage**:
    *   `TimeSeries DB` (e.g., InfluxDB/KDB+) for Tick/Quote data.
    *   `Relational DB` (PostgreSQL) for User Data, Fund Meta, Fundamental Data.

## 3. Compliance & Security (合规与安全)
*   **Data Security**: AES-256 encryption for user sensitive data.
*   **Compliance**: 
    *   Disclaimer management.
    *   KYC/AML workflows.
    *   Data residency (China mainland servers).
*   **Role-Based Access Control (RBAC)**: Differentiation between Retail, Pro, and Admin users.

## 4. Roadmap (实施路线)

*   **Phase 1 (Current)**: Foundation - Navigation Restructure, Fund Dashboard MVP.
*   **Phase 2**: Data Integration - Connect real-time quotes, Fund database.
*   **Phase 3**: Intelligence - Robo-advisor algorithms, Deep learning for stock selection.
