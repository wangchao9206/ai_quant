import React, { useState, useEffect, useRef } from 'react';
import { Row, Col, Card, Statistic, List, Avatar, Button, Progress, message, Input } from 'antd';
import { 
    GoldOutlined, 
    BankOutlined, 
    GlobalOutlined, 
    AlertOutlined 
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import '../styles/design-tokens.css';

const COMMODITY_KEYWORDS = {
    'Gold (伦敦金)': ['黄金', '沪金', 'au', 'xau'],
    'Silver (白银)': ['白银', '沪银', 'ag', 'xag'],
    'Copper (沪铜)': ['沪铜', '铜', 'cu'],
    'Aluminum (沪铝)': ['沪铝', '铝', 'al'],
    'Zinc (沪锌)': ['沪锌', '锌', 'zn'],
    'Crude Oil (原油)': ['原油', 'sc'],
    'Rebar (螺纹钢)': ['螺纹', '螺纹钢', 'rb'],
    'Iron Ore (铁矿石)': ['铁矿', '铁矿石', 'i'],
    'Soymeal (豆粕)': ['豆粕', 'm'],
    'Palm Oil (棕榈油)': ['棕榈', '棕榈油', 'p'],
    'Corn (玉米)': ['玉米', 'c'],
    'Sugar (白糖)': ['白糖', '糖', 'sr'],
    'Cotton (棉花)': ['棉花', '棉', 'cf'],
    'Rubber (橡胶)': ['橡胶', 'ru'],
};

const CommoditiesDashboard = () => {
    const [metals, setMetals] = useState([]);
    const [chartData, setChartData] = useState({ times: [], values: [] });
    const [macroData, setMacroData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [alerts, setAlerts] = useState([]);
    const [inventory, setInventory] = useState([]);
    const [timeframe, setTimeframe] = useState('1H');
    const [searchText, setSearchText] = useState('');

    const refreshLockRef = useRef(false);

    useEffect(() => {
        fetchData(timeframe);

        const intervalId = window.setInterval(async () => {
            if (refreshLockRef.current) return;
            refreshLockRef.current = true;
            try {
                await fetchData(timeframe, { silent: true });
            } finally {
                refreshLockRef.current = false;
            }
        }, 5000);

        return () => window.clearInterval(intervalId);
    }, [timeframe]);

    const fetchData = async (selectedTimeframe, { silent = false } = {}) => {
        if (!silent) setLoading(true);
        try {
            const [listRes, chartRes, macroRes, alertsRes, inventoryRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/commodities/list`),
                axios.get(`${API_BASE_URL}/api/commodities/chart`, { params: { timeframe: selectedTimeframe } }),
                axios.get(`${API_BASE_URL}/api/commodities/macro`),
                axios.get(`${API_BASE_URL}/api/commodities/alerts`),
                axios.get(`${API_BASE_URL}/api/commodities/inventory`)
            ]);
            setMetals(listRes.data);
            setChartData(chartRes.data);
            setMacroData(macroRes.data);
            setAlerts(alertsRes.data);
            setInventory(inventoryRes.data);
        } catch (error) {
            if (!silent) {
                console.error("Failed to fetch commodities data:", error);
                message.error("获取大宗商品数据失败");
            }
        } finally {
            if (!silent) setLoading(false);
        }
    };

    // Helper to get icon
    const getIcon = (name) => {
        if (name.includes('Gold') || name.includes('黄金')) return <GoldOutlined style={{ color: '#FFD700' }} />;
        if (name.includes('Silver') || name.includes('白银')) return <div style={{ width: 14, height: 14, background: '#C0C0C0', borderRadius: '50%' }} />;
        if (name.includes('Copper') || name.includes('铜')) return <div style={{ width: 14, height: 14, background: '#B87333', borderRadius: '50%' }} />;
        if (name.includes('Oil') || name.includes('原油')) return <GlobalOutlined style={{ color: '#cf1322' }} />;
        if (name.includes('Iron') || name.includes('钢') || name.includes('矿')) return <BankOutlined style={{ color: '#faad14' }} />;
        return <div style={{ width: 14, height: 14, background: '#888', borderRadius: '50%' }} />;
    };

    const chartOption = {
        backgroundColor: 'transparent',
        grid: { top: 30, bottom: 30, left: 40, right: 20 },
        xAxis: { 
            type: 'category', 
            data: chartData.times,
            axisLine: { lineStyle: { color: '#888' } }
        },
        yAxis: { 
            type: 'value', 
            scale: true,
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
        },
        series: [{
            data: chartData.values,
            type: 'line',
            smooth: true,
            lineStyle: { color: '#FFD700', width: 2 },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [{ offset: 0, color: 'rgba(255, 215, 0, 0.3)' }, { offset: 1, color: 'rgba(255, 215, 0, 0)' }]
                }
            }
        }]
    };

    const normalizedQuery = String(searchText || '').trim().toLowerCase();
    const filteredMetals = normalizedQuery
        ? metals.filter((item) => {
            const name = String(item.name || '');
            const keywords = COMMODITY_KEYWORDS[item.name] || [];
            const candidates = [name, ...keywords];
            return candidates.some((val) => String(val || '').toLowerCase().includes(normalizedQuery));
        })
        : metals;

    return (
        <div style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
            <div style={{ marginBottom: '24px' }}>
                <h1 style={{ color: '#fff', display: 'flex', alignItems: 'center', gap: '12px', margin: 0 }}>
                    <GoldOutlined style={{ color: '#FFD700' }} />
                    大宗商品与贵金属 (Commodities & Metals)
                </h1>
                <p style={{ color: 'rgba(255,255,255,0.45)' }}>全球宏观对冲 • 抗通胀资产管理 • 供应链金融</p>
                <div style={{ marginTop: '16px', maxWidth: '420px' }}>
                    <Input.Search
                        placeholder="搜索品种/中文名/合约缩写"
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        allowClear
                    />
                </div>
            </div>

            <style>{`
                @keyframes aiqMarqueeCommodities {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
            `}</style>

            <div className="glass-panel" style={{ marginBottom: '16px', padding: '10px 12px', overflow: 'hidden' }}>
                <div style={{ display: 'flex', width: '200%', animation: 'aiqMarqueeCommodities 18s linear infinite' }}>
                    {[0, 1].map((dup) => (
                        <div key={dup} style={{ display: 'inline-flex', alignItems: 'center', gap: '18px', width: '50%', whiteSpace: 'nowrap' }}>
                            {filteredMetals.map((m) => (
                                <span key={`c-${dup}-${m.name}`} style={{ color: Number(m.change) >= 0 ? 'var(--color-secondary)' : '#ff4d4f', fontFamily: 'JetBrains Mono' }}>
                                    {m.name} {Number(m.price).toLocaleString()} {(Number(m.change) > 0 ? '+' : '') + Number(m.change).toFixed(2)}%
                                </span>
                            ))}
                        </div>
                    ))}
                </div>
            </div>

            <Row gutter={24}>
                {/* Left: Price Cards */}
                <Col span={6}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {filteredMetals.map((m, i) => (
                            <div key={i} className="glass-card" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ color: '#888', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        {getIcon(m.name)} {m.name}
                                    </div>
                                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fff', fontFamily: 'JetBrains Mono', marginTop: '8px' }}>
                                        {m.price.toLocaleString()} <span style={{ fontSize: '12px' }}>{m.unit}</span>
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ 
                                        color: m.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f', 
                                        fontWeight: 'bold',
                                        fontSize: '16px' 
                                    }}>
                                        {m.change > 0 ? '+' : ''}{m.change}%
                                    </div>
                                </div>
                            </div>
                        ))}
                        
                        <div className="glass-card" style={{ padding: '20px', background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.3)' }}>
                            <div style={{ color: '#FFD700', fontWeight: 'bold', marginBottom: '8px' }}>
                                <AlertOutlined /> AI 交易机会提醒
                            </div>
                            <div style={{ color: '#fff', fontSize: '13px' }}>
                                {alerts[0]?.message || '暂无最新提示'}
                            </div>
                            <Button size="small" style={{ marginTop: '12px', background: '#FFD700', color: '#000', border: 'none' }}>
                                查看详情
                            </Button>
                        </div>
                    </div>
                </Col>

                {/* Middle: Main Chart */}
                <Col span={12}>
                    <div className="glass-card" style={{ height: '100%', padding: '20px', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                            <span style={{ color: '#fff', fontWeight: 'bold' }}>XAU/USD 实时走势</span>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <Button size="small" type={timeframe === '1H' ? 'primary' : 'default'} ghost={timeframe !== '1H'} onClick={() => setTimeframe('1H')}>1H</Button>
                                <Button size="small" type={timeframe === '4H' ? 'primary' : 'default'} ghost={timeframe !== '4H'} onClick={() => setTimeframe('4H')}>4H</Button>
                                <Button size="small" type={timeframe === '1D' ? 'primary' : 'default'} ghost={timeframe !== '1D'} onClick={() => setTimeframe('1D')}>1D</Button>
                            </div>
                        </div>
                        <div style={{ flex: 1 }}>
                            <ReactECharts option={chartOption} style={{ height: '100%' }} />
                        </div>
                    </div>
                </Col>

                {/* Right: Macro Indicators */}
                <Col span={6}>
                    <div className="glass-card" style={{ height: '100%', padding: '20px' }}>
                        <h3 style={{ color: '#fff', marginTop: 0 }}>宏观驱动因子 (Macro Drivers)</h3>
                        
                        <List itemLayout="horizontal">
                            {macroData.map((item, index) => (
                                <List.Item key={index}>
                                    <div style={{ width: '100%' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#ccc', marginBottom: '4px' }}>
                                            <span>{item.name}</span>
                                            <span style={{ color: item.status === 'high' ? '#ff4d4f' : (item.status === 'low' ? 'var(--color-secondary)' : '#faad14') }}>
                                                {item.value} ({item.change})
                                            </span>
                                        </div>
                                        <Progress 
                                            percent={item.percent} 
                                            strokeColor={item.status === 'high' ? '#ff4d4f' : (item.status === 'low' ? 'var(--color-secondary)' : '#faad14')} 
                                            showInfo={false} 
                                            size="small" 
                                        />
                                    </div>
                                </List.Item>
                            ))}
                        </List>

                        <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                            <h4 style={{ color: '#fff' }}>全球库存监控</h4>
                            {inventory.length === 0 ? (
                                <div style={{ color: '#888', fontSize: '12px' }}>暂无数据</div>
                            ) : (
                                inventory.map((item, index) => (
                                    <div key={index} style={{ display: 'flex', justifyContent: 'space-between', color: '#888', fontSize: '12px', marginBottom: index === inventory.length - 1 ? 0 : '8px' }}>
                                        <span>{item.name}</span>
                                        <span>{item.value} ({item.status})</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export default CommoditiesDashboard;
