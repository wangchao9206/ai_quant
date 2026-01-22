
def generate_strategy_summary(record):
    """
    Generate a rule-based summary report for a backtest record.
    """
    summary = []
    
    def _get(name, default=None):
        if isinstance(record, dict):
            return record.get(name, default)
        return getattr(record, name, default)

    return_rate = _get("return_rate")
    sharpe_ratio = _get("sharpe_ratio")
    max_drawdown = _get("max_drawdown")
    win_rate = _get("win_rate")
    total_trades = _get("total_trades")

    return_rate = return_rate if return_rate is not None else 0.0
    sharpe_ratio = sharpe_ratio if sharpe_ratio is not None else 0.0
    max_drawdown = max_drawdown if max_drawdown is not None else 0.0
    win_rate = win_rate if win_rate is not None else 0.0
    total_trades = total_trades if total_trades is not None else 0
    won_trades = int(total_trades * (win_rate / 100))

    # 1. Performance Overview
    summary.append("### 1. 绩效概览")
    summary.append(f"- **总收益率**: {return_rate:.2f}%")
    summary.append(f"- **夏普比率**: {sharpe_ratio:.2f}")
    summary.append(f"- **最大回撤**: {max_drawdown:.2f}%")
    summary.append(f"- **胜率**: {win_rate:.2f}% ({won_trades}/{total_trades})")
    
    # 2. Strategy Analysis
    summary.append("\n### 2. 策略分析")
    
    # Return Analysis
    if return_rate > 20:
        summary.append("- **收益表现**: 优秀。策略取得了显著的正收益，表现优异。")
    elif return_rate > 0:
        summary.append("- **收益表现**: 良好。策略实现了盈利，但仍有提升空间。")
    else:
        summary.append("- **收益表现**: 不佳。策略未能盈利，建议重新审视交易逻辑。")
        
    # Risk Analysis
    if max_drawdown < 10:
        summary.append("- **风险控制**: 优秀。最大回撤控制在10%以内，风险较低。")
    elif max_drawdown < 20:
        summary.append("- **风险控制**: 一般。最大回撤在10%-20%之间，需注意风险管理。")
    else:
        summary.append("- **风险控制**: 较高。最大回撤超过20%，建议优化止损机制或降低仓位。")
        
    # Stability Analysis
    if sharpe_ratio > 1.5:
        summary.append("- **稳定性**: 极高。夏普比率超过1.5，收益风险比极佳。")
    elif sharpe_ratio > 1.0:
        summary.append("- **稳定性**: 良好。夏普比率超过1.0，收益相对稳定。")
    else:
        summary.append("- **稳定性**: 较低。夏普比率低于1.0，收益波动较大。")
        
    # 3. Improvement Suggestions
    summary.append("\n### 3. 改进建议")
    suggestions = []
    
    if win_rate < 40:
        suggestions.append("- **提高胜率**: 当前胜率较低，建议优化入场条件，过滤低质量交易信号。")
    
    if max_drawdown > 15:
        suggestions.append("- **加强风控**: 回撤较大，建议收紧止损幅度，或引入波动率过滤机制。")
        
    if total_trades < 10:
        suggestions.append("- **增加样本量**: 交易次数较少，统计结果可能存在偶然性，建议扩大回测时间范围或降低交易门槛。")
        
    if not suggestions:
        suggestions.append("- **持续监控**: 策略表现稳健，建议在更多品种或时间段上进行验证。")
        
    for s in suggestions:
        summary.append(s)
        
    return "\n".join(summary)
