import React, { useState, useEffect, useRef } from 'react';
import { Row, Col, Button, Select, Slider, Statistic, Card, Space, message, InputNumber, Tag, Spin } from 'antd';
import { 
    PlayCircleOutlined, 
    PauseCircleOutlined, 
    StepForwardOutlined, 
    ReloadOutlined,
    ClockCircleOutlined,
    TrophyOutlined,
    FallOutlined,
    RiseOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import axios from 'axios';
import { API_BASE_URL } from '../../config';

const MarketReplay = () => {
    // --- State ---
    const [loading, setLoading] = useState(false);
    const [fullData, setFullData] = useState([]);
    const [keyFrames, setKeyFrames] = useState([]);
    const [isPlaying, setIsPlaying] = useState(false);
    const [speed, setSpeed] = useState(1); // 1x, 5x, 10x, 50x
    const [currentIndex, setCurrentIndex] = useState(0);
    const [account, setAccount] = useState({ cash: 1000000, position: 0, pnl: 0, avgPrice: 0 });
    const [tradeType, setTradeType] = useState('buy');
    const [tradeQty, setTradeQty] = useState(100);

    const timerRef = useRef(null);
    const chartRef = useRef(null);

    // --- Data Fetching ---
    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/market/replay/kline`);
            setFullData(response.data.data);
            
            // Map backend keyframes to frontend format
            const mappedKeyFrames = response.data.key_frames.map(kf => {
                let color = '#1890ff';
                let icon = <RiseOutlined />;
                
                if (kf.type === 'min_price') {
                    color = '#52c41a';
                    icon = <FallOutlined />;
                } else if (kf.type === 'max_price') {
                    color = '#ff4d4f';
                    icon = <TrophyOutlined />;
                }
                
                return {
                    ...kf,
                    color,
                    icon
                };
            });
            setKeyFrames(mappedKeyFrames);
            setCurrentIndex(0);
        } catch (error) {
            console.error("Failed to fetch market replay data:", error);
            message.error("获取复盘数据失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const [displayData, setDisplayData] = useState([]);

    // --- Effect for Playback ---
    useEffect(() => {
        if (isPlaying) {
            timerRef.current = setInterval(() => {
                setCurrentIndex(prev => {
                    if (prev >= fullData.length - 1) {
                        setIsPlaying(false);
                        return prev;
                    }
                    return prev + 1;
                });
            }, 1000 / speed);
        } else {
            clearInterval(timerRef.current);
        }

        if (loading && fullData.length === 0) {
        return (
            <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <Spin size="large" tip="正在生成市场回放数据..." />
            </div>
        );
    }

    return () => clearInterval(timerRef.current);
    }, [isPlaying, speed, fullData]);

    useEffect(() => {
        setDisplayData(fullData.slice(0, currentIndex + 1));
    }, [currentIndex, fullData]);

    // --- Effect for KeyFrames Calculation ---
    // (Handled in fetchData)

    // --- Actions ---
    const handleJumpTo = (index) => {
        setCurrentIndex(index);
        setIsPlaying(false);
        message.info(`Jumped to index ${index}`);
    };

    const handleTrade = () => {
        const currentPrice = displayData[displayData.length - 1].values[1]; // close price
        const cost = currentPrice * tradeQty;

        if (tradeType === 'buy') {
            if (account.cash >= cost) {
                const newPos = account.position + tradeQty;
                const newAvg = ((account.position * account.avgPrice) + cost) / newPos;
                setAccount(prev => ({
                    ...prev,
                    cash: prev.cash - cost,
                    position: newPos,
                    avgPrice: newAvg
                }));
                message.success(`买入 ${tradeQty} 股 @ ${currentPrice.toFixed(2)}`);
            } else {
                message.error('资金不足');
            }
        } else {
            if (account.position >= tradeQty) {
                const revenue = currentPrice * tradeQty;
                const profit = (currentPrice - account.avgPrice) * tradeQty;
                setAccount(prev => ({
                    ...prev,
                    cash: prev.cash + revenue,
                    position: prev.position - tradeQty,
                    pnl: prev.pnl + profit,
                    avgPrice: prev.position - tradeQty === 0 ? 0 : prev.avgPrice
                }));
                message.success(`卖出 ${tradeQty} 股 @ ${currentPrice.toFixed(2)}`);
            } else {
                message.error('持仓不足');
            }
        }
    };

    const handleReset = () => {
        setIsPlaying(false);
        setCurrentIndex(0);
        setAccount({ cash: 1000000, position: 0, pnl: 0, avgPrice: 0 });
        fetchData(); // Refresh data
    };

    // --- Chart Option ---
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        grid: { left: 50, right: 50, top: 30, bottom: 30 },
        xAxis: {
            type: 'category',
            data: displayData.map(d => d.time),
            axisLine: { lineStyle: { color: '#666' } }
        },
        yAxis: {
            scale: true,
            splitLine: { lineStyle: { color: '#333' } },
            axisLine: { show: false }
        },
        series: [{
            type: 'candlestick',
            data: displayData.map(d => d.values),
            itemStyle: {
                color: '#ff4d4f',
                color0: 'var(--color-secondary)',
                borderColor: '#ff4d4f',
                borderColor0: 'var(--color-secondary)'
            }
        }]
    };

    const currentPrice = displayData.length > 0 ? displayData[displayData.length - 1].values[1] : 0;
    const marketValue = account.position * currentPrice;
    const totalAssets = account.cash + marketValue;
    const totalReturn = ((totalAssets - 1000000) / 1000000) * 100;

    return (
        <div style={{ height: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Header / Toolbar */}
            <div className="glass-card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                    <h2 style={{ margin: 0, color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <ClockCircleOutlined style={{ color: 'var(--color-primary)' }} />
                        复盘训练营 (Market Replay)
                    </h2>
                    <Space>
                        <Button 
                            type="primary" 
                            icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />} 
                            onClick={() => setIsPlaying(!isPlaying)}
                            size="large"
                        >
                            {isPlaying ? '暂停' : '开始回放'}
                        </Button>
                        <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
                        <Select value={speed} onChange={setSpeed} style={{ width: 100 }}>
                            <Select.Option value={1}>1x 速度</Select.Option>
                            <Select.Option value={5}>5x 速度</Select.Option>
                            <Select.Option value={10}>10x 速度</Select.Option>
                            <Select.Option value={50}>50x 速度</Select.Option>
                        </Select>
                        <span style={{ color: '#888', marginLeft: '12px' }}>
                            当前时间: {displayData.length > 0 ? displayData[displayData.length - 1].time : '--:--'}
                        </span>
                    </Space>
                </div>
                
                <div style={{ display: 'flex', gap: '32px' }}>
                    <Statistic 
                        title="总资产" 
                        value={totalAssets} 
                        precision={2} 
                        valueStyle={{ color: totalReturn >= 0 ? '#ff4d4f' : 'var(--color-secondary)' }} 
                    />
                    <Statistic 
                        title="收益率" 
                        value={totalReturn} 
                        precision={2} 
                        suffix="%" 
                        valueStyle={{ color: totalReturn >= 0 ? '#ff4d4f' : 'var(--color-secondary)' }} 
                        prefix={totalReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                    />
                </div>
            </div>

            <Row gutter={24} style={{ flex: 1 }}>
                {/* Chart Area */}
                <Col span={18} style={{ display: 'flex', flexDirection: 'column' }}>
                    <div className="glass-card" style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column' }}>
                        <ReactECharts 
                            ref={chartRef}
                            option={option} 
                            style={{ height: '100%', width: '100%' }} 
                            opts={{ renderer: 'svg' }}
                        />
                    </div>
                </Col>

                {/* Trading Panel */}
                <Col span={6}>
                    <div className="glass-card" style={{ height: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        <div style={{ borderBottom: '1px solid #333', paddingBottom: '12px' }}>
                            <h3 style={{ color: '#fff', margin: 0 }}>模拟交易台</h3>
                            <span style={{ color: '#888', fontSize: '12px' }}>Test your intuition</span>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <span style={{ color: '#888' }}>当前价格</span>
                            <span style={{ fontSize: '28px', fontWeight: 'bold', color: '#fff', fontFamily: 'JetBrains Mono' }}>
                                {currentPrice.toFixed(2)}
                            </span>
                        </div>

                        <div style={{ background: '#1f1f1f', padding: '16px', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                <span style={{ color: '#888' }}>可用资金</span>
                                <span style={{ color: '#fff' }}>{account.cash.toFixed(2)}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                <span style={{ color: '#888' }}>持仓数量</span>
                                <span style={{ color: '#fff' }}>{account.position}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: '#888' }}>持仓均价</span>
                                <span style={{ color: '#fff' }}>{account.avgPrice.toFixed(2)}</span>
                            </div>
                        </div>

                        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <Button 
                                    type={tradeType === 'buy' ? 'primary' : 'default'} 
                                    danger={tradeType === 'buy'}
                                    style={{ flex: 1 }}
                                    onClick={() => setTradeType('buy')}
                                >
                                    买入 (Buy)
                                </Button>
                                <Button 
                                    type={tradeType === 'sell' ? 'primary' : 'default'} 
                                    style={{ flex: 1, background: tradeType === 'sell' ? 'var(--color-secondary)' : '', borderColor: tradeType === 'sell' ? 'var(--color-secondary)' : '' }}
                                    onClick={() => setTradeType('sell')}
                                >
                                    卖出 (Sell)
                                </Button>
                            </div>
                            
                            <InputNumber 
                                style={{ width: '100%' }} 
                                value={tradeQty} 
                                onChange={setTradeQty} 
                                addonAfter="股"
                                step={100}
                            />

                            <Button 
                                type="primary" 
                                size="large" 
                                block
                                danger={tradeType === 'buy'}
                                style={{ 
                                    background: tradeType === 'sell' ? 'var(--color-secondary)' : undefined,
                                    borderColor: tradeType === 'sell' ? 'var(--color-secondary)' : undefined
                                }}
                                onClick={handleTrade}
                                disabled={!isPlaying && currentIndex === 0}
                            >
                                下单交易 (Execute)
                            </Button>
                        </div>
                        
                        {/* Key Moments Section */}
                        <div style={{ borderTop: '1px solid #333', paddingTop: '16px' }}>
                            <h4 style={{ color: '#fff', margin: '0 0 12px 0' }}>关键帧 (Key Moments)</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {keyFrames.map((kf, i) => (
                                    <div 
                                        key={i} 
                                        onClick={() => handleJumpTo(kf.index)}
                                        style={{ 
                                            background: '#1f1f1f', 
                                            padding: '8px 12px', 
                                            borderRadius: '4px', 
                                            cursor: 'pointer',
                                            display: 'flex', 
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            borderLeft: `3px solid ${kf.color}`
                                        }}
                                        className="keyframe-item"
                                    >
                                        <span style={{ color: '#ccc', fontSize: '12px' }}>{kf.icon} {kf.label}</span>
                                        <span style={{ color: '#fff', fontWeight: 'bold' }}>{kf.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export default MarketReplay;
