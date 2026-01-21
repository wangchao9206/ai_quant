import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, List, Badge, Tag, Progress, Avatar, Tooltip } from 'antd';
import { 
    SendOutlined, RobotOutlined, ThunderboltOutlined, 
    SafetyCertificateOutlined, LineChartOutlined, 
    PlayCircleOutlined, PauseCircleOutlined,
    WarningOutlined, CheckCircleOutlined,
    BugOutlined, AimOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const ConceptDashboard = () => {
    const [messages, setMessages] = useState([
        { type: 'ai', content: '下午好，指挥官。市场波动率指数(VIX)上升至 22.5，建议启动防御性策略检查。' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(45);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        let interval;
        if (isPlaying) {
            interval = setInterval(() => {
                setProgress(prev => (prev >= 100 ? 0 : prev + 0.5));
            }, 100);
        }
        return () => clearInterval(interval);
    }, [isPlaying]);

    const handleSend = () => {
        if (!inputValue.trim()) return;
        setMessages(prev => [...prev, { type: 'user', content: inputValue }]);
        const userQuery = inputValue;
        setInputValue('');
        
        // Simulate AI thinking delay
        setTimeout(() => {
            let response = '收到。正在分析...';
            if (userQuery.includes('风险')) {
                response = '已扫描当前组合。发现潜在的流动性风险（评分 4.2/10）。建议降低小市值个股仓位，增加 ETF 对冲。';
            } else if (userQuery.includes('优化')) {
                response = '基于遗传算法，我为您生成了 3 个优化变体。变体 B 的夏普比率提升了 15%，但最大回撤略有增加。是否查看详情？';
            } else {
                response = '指令已确认。正在执行全市场扫描，预计耗时 1.2秒... 发现 3 个符合“均线多头排列”的标的。';
            }
            setMessages(prev => [...prev, { type: 'ai', content: response }]);
        }, 1500);
    };

    // Chart Options
    const radarOption = {
        backgroundColor: 'transparent',
        title: { text: 'Risk Sentinel (风控哨兵)', textStyle: { color: 'rgba(255,255,255,0.7)', fontSize: 12, fontWeight: 'normal' }, top: 0, left: 0 },
        radar: {
            indicator: [
                { name: '流动性', max: 100 },
                { name: '波动率', max: 100 },
                { name: '最大回撤', max: 100 },
                { name: '杠杆率', max: 100 },
                { name: '集中度', max: 100 },
                { name: 'Alpha', max: 100 }
            ],
            splitArea: { show: false },
            axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
            splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
            radius: '65%',
            center: ['50%', '55%']
        },
        series: [{
            type: 'radar',
            data: [
                {
                    value: [80, 40, 20, 60, 30, 75],
                    name: 'Current Portfolio',
                    areaStyle: { color: 'rgba(41, 121, 255, 0.2)' },
                    lineStyle: { color: '#2979FF', width: 2 },
                    symbol: 'none'
                },
                {
                    value: [90, 30, 10, 50, 20, 85],
                    name: 'Optimized',
                    areaStyle: { color: 'rgba(0, 230, 118, 0.1)' },
                    lineStyle: { color: '#00E676', width: 1, type: 'dashed' },
                    symbol: 'none'
                }
            ]
        }]
    };

    return (
        <div className="grid-cockpit" style={{ height: 'calc(100vh - 80px)' }}>
            
            {/* =================================================================================
               LEFT PANEL: AI COPILOT
               ================================================================================= */}
            <div className="glass-panel" style={{ gridRow: '1 / -1', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* Header */}
                <div style={{ padding: 'var(--space-md)', borderBottom: 'var(--glass-border)', background: 'rgba(0,0,0,0.2)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                        <div className="animate-pulse-glow" style={{ borderRadius: '50%' }}>
                            <Avatar size="large" icon={<RobotOutlined />} style={{ backgroundColor: 'var(--color-primary)', border: '2px solid rgba(255,255,255,0.1)' }} />
                        </div>
                        <div>
                            <div className="text-neon-blue" style={{ fontWeight: 'bold', fontSize: '16px' }}>AI Copilot</div>
                            <div style={{ fontSize: 12, color: 'var(--color-success)' }}>
                                <Badge status="processing" color="var(--color-success)" /> System Online
                            </div>
                        </div>
                    </div>
                </div>

                {/* Chat Area */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                    {messages.map((msg, idx) => (
                        <div key={idx} style={{ 
                            alignSelf: msg.type === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '90%'
                        }}>
                            <div style={{ 
                                padding: '12px 16px', 
                                borderRadius: msg.type === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                                background: msg.type === 'user' ? 'var(--color-primary)' : 'rgba(255,255,255,0.05)',
                                color: '#fff',
                                border: msg.type === 'ai' ? '1px solid rgba(255,255,255,0.1)' : 'none',
                                fontSize: '14px',
                                lineHeight: '1.5'
                            }}>
                                {msg.content}
                            </div>
                            {msg.type === 'ai' && (
                                <div style={{ fontSize: 10, color: 'var(--color-text-disabled)', marginTop: 4, marginLeft: 4 }}>
                                    AI Strategy Doctor v2.1
                                </div>
                            )}
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div style={{ padding: 'var(--space-md)', borderTop: 'var(--glass-border)', background: 'rgba(0,0,0,0.2)' }}>
                    <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                        <Input 
                            placeholder="输入指令 (e.g., '优化止损参数')" 
                            value={inputValue}
                            onChange={e => setInputValue(e.target.value)}
                            onPressEnter={handleSend}
                            style={{ 
                                background: 'rgba(0,0,0,0.3)', 
                                border: '1px solid rgba(255,255,255,0.2)', 
                                color: '#fff',
                                borderRadius: 'var(--radius-full)'
                            }}
                        />
                        <Button 
                            type="primary" 
                            shape="circle" 
                            icon={<SendOutlined />} 
                            onClick={handleSend}
                            style={{ background: 'var(--color-primary)', borderColor: 'var(--color-primary)' }}
                        />
                    </div>
                </div>
            </div>

            {/* =================================================================================
               CENTER PANEL: MAIN HUD
               ================================================================================= */}
            <div style={{ gridColumn: '2 / 3', gridRow: '1 / -1', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                
                {/* Top Status Bar */}
                <div className="glass-panel" style={{ padding: '12px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '32px' }}>
                        <div>
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>上证指数</span>
                            <div className="text-neon-green" style={{ fontSize: 16, fontWeight: 'bold' }}>3,245.12 <span style={{ fontSize: 12 }}>+1.2%</span></div>
                        </div>
                        <div>
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>VIX 恐慌指数</span>
                            <div style={{ color: 'var(--color-warning)', fontSize: 16, fontWeight: 'bold' }}>22.50 <span style={{ fontSize: 12 }}>+5.1%</span></div>
                        </div>
                        <div>
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>主力净流入</span>
                            <div className="text-neon-blue" style={{ fontSize: 16, fontWeight: 'bold' }}>+12.5亿</div>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                        <Tag color="rgba(41, 121, 255, 0.2)" style={{ color: '#2979FF', border: '1px solid #2979FF' }}>AI 算力: 98%</Tag>
                        <Tag color="rgba(0, 230, 118, 0.2)" style={{ color: '#00E676', border: '1px solid #00E676' }}>低延迟: 8ms</Tag>
                    </div>
                </div>

                {/* Immersive Chart Area */}
                <div className="glass-panel" style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ position: 'absolute', top: 20, left: 24, zIndex: 10 }}>
                        <h2 style={{ margin: 0, fontWeight: 300, fontSize: 24 }}>SH.600000 <span style={{ fontWeight: 700 }}>浦发银行</span></h2>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                            <Badge status="processing" color="var(--color-success)" />
                            <span style={{ color: 'var(--color-success)' }}>MA Trend Strategy Running...</span>
                        </div>
                    </div>

                    {/* Chart Placeholder */}
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle at center, rgba(41, 121, 255, 0.05) 0%, rgba(0,0,0,0) 70%)' }}>
                        <div className="animate-float" style={{ textAlign: 'center', opacity: 0.5 }}>
                            <LineChartOutlined style={{ fontSize: 80, color: 'var(--color-text-disabled)' }} />
                            <p style={{ marginTop: 16, fontFamily: 'var(--font-mono)' }}>[ IMMERSIVE REPLAY MODE ]</p>
                        </div>
                    </div>

                    {/* Playback Controls HUD */}
                    <div style={{ 
                        background: 'rgba(0,0,0,0.6)', 
                        backdropFilter: 'blur(10px)',
                        padding: '16px 24px', 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '24px',
                        borderTop: 'var(--glass-border)'
                    }}>
                         <Button 
                            type="text" 
                            shape="circle" 
                            icon={isPlaying ? <PauseCircleOutlined style={{ fontSize: 24, color: 'var(--color-primary)' }} /> : <PlayCircleOutlined style={{ fontSize: 24, color: 'var(--color-primary)' }} />} 
                            onClick={() => setIsPlaying(!isPlaying)}
                        />
                         <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                                <span>2023-01-01</span>
                                <span>PLAYBACK SPEED: 10x</span>
                                <span>2023-12-31</span>
                            </div>
                            <Progress 
                                percent={progress} 
                                showInfo={false} 
                                strokeColor={{ '0%': 'var(--color-primary)', '100%': 'var(--color-accent)' }} 
                                trailColor="rgba(255,255,255,0.1)"
                                size="small"
                            />
                         </div>
                         <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>
                             2023-05-12 <span style={{ color: 'var(--color-text-secondary)' }}>14:30:00</span>
                         </div>
                    </div>
                </div>

                {/* Strategy Gene Map */}
                <div className="glass-panel" style={{ height: '180px', padding: 'var(--space-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                        <span style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--color-text-secondary)' }}>Strategy DNA Map</span>
                        <AimOutlined style={{ color: 'var(--color-text-secondary)' }} />
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--space-md)', height: 'calc(100% - 30px)' }}>
                        {['Entry Signal', 'Exit Signal', 'Position Mgmt', 'Risk Control'].map((title, i) => (
                            <div key={i} style={{ 
                                flex: 1, 
                                border: '1px dashed rgba(255,255,255,0.2)', 
                                borderRadius: 'var(--radius-md)', 
                                padding: '12px',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                background: 'rgba(255,255,255,0.02)',
                                transition: 'all 0.3s'
                            }} className="hover-glow">
                                <span style={{ color: i===0?'#2979FF':i===1?'#00E676':i===2?'#FFAB00':'#FF1744', fontSize: 12, marginBottom: 8 }}>{title}</span>
                                <div style={{ fontSize: 13, fontWeight: 'bold', textAlign: 'center' }}>
                                    {i===0 ? 'MA5 > MA20' : i===1 ? 'RSI > 80' : i===2 ? 'Kelly Criterion' : 'MaxDD < 10%'}
                                </div>
                                <div style={{ fontSize: 10, color: 'var(--color-text-disabled)', marginTop: 4 }}>Gene #{1000+i}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* =================================================================================
               RIGHT PANEL: RISK & STATS
               ================================================================================= */}
            <div className="glass-panel" style={{ gridRow: '1 / -1', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', padding: 'var(--space-md)' }}>
                {/* Radar Chart */}
                <div style={{ height: '300px', margin: '-16px -16px 0 -16px' }}>
                    <ReactECharts option={radarOption} style={{ height: '100%', width: '100%' }} />
                </div>

                {/* Diagnostics */}
                <div style={{ flex: 1, overflowY: 'auto' }}>
                    <h4 style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 0 16px 0' }}>
                        <SafetyCertificateOutlined style={{ color: 'var(--color-success)' }} /> 
                        <span className="text-gradient-success">Diagnostic Report</span>
                    </h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                                <span>Overfitting Risk</span>
                                <span style={{ color: 'var(--color-success)' }}>Low (12%)</span>
                            </div>
                            <Progress percent={12} strokeColor="var(--color-success)" trailColor="rgba(255,255,255,0.1)" showInfo={false} size="small" />
                        </div>

                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                                <span>Parameter Sensitivity</span>
                                <span style={{ color: 'var(--color-danger)' }}>High (85%)</span>
                            </div>
                            <Progress percent={85} strokeColor="var(--color-danger)" trailColor="rgba(255,255,255,0.1)" showInfo={false} size="small" />
                            <div style={{ fontSize: 11, color: 'var(--color-warning)', marginTop: 6, display: 'flex', gap: 6 }}>
                                <WarningOutlined />
                                <span>Sensitivity Alert: Small parameter changes cause large profit swings.</span>
                            </div>
                        </div>

                        <div style={{ 
                            background: 'rgba(41, 121, 255, 0.1)', 
                            border: '1px solid rgba(41, 121, 255, 0.2)',
                            borderRadius: 'var(--radius-md)', 
                            padding: '12px',
                            marginTop: '8px'
                        }}>
                            <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                                <BugOutlined style={{ color: 'var(--color-primary)' }} />
                                <span style={{ color: 'var(--color-primary)', fontSize: 12, fontWeight: 'bold' }}>AI Insight</span>
                            </div>
                            <p style={{ margin: 0, fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                                Strategy performs poorly in choppy markets (2022-Q3). Suggest adding <strong>ATR Filter</strong> to reduce false signals.
                            </p>
                            <Button size="small" type="link" style={{ padding: '4px 0', height: 'auto', fontSize: 11 }}>Apply Fix &rarr;</Button>
                        </div>
                    </div>
                </div>

                {/* Live Performance */}
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                        <div>
                            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Total Return</div>
                            <div className="text-neon-green" style={{ fontSize: 24, fontWeight: 'bold', lineHeight: 1 }}>+128.4%</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Max Drawdown</div>
                            <div style={{ color: 'var(--color-danger)', fontSize: 16, fontWeight: 'bold' }}>-12.1%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConceptDashboard;
