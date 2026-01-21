import React, { useState, useEffect } from 'react';
import { Row, Col, Statistic, Table, Tag, Input, Button, Progress, List, Badge, message, Spin } from 'antd';
import { 
    SearchOutlined, 
    StockOutlined, 
    RiseOutlined, 
    FallOutlined,
    HeatMapOutlined,
    AlertOutlined,
    ThunderboltOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import '../styles/design-tokens.css';
import { useLanguage } from '../contexts/LanguageContext';

const StockDashboard = () => {
    const { t } = useLanguage();
    const [symbol, setSymbol] = useState('600519');
    const [loading, setLoading] = useState(false);
    
    const [marketIndices, setMarketIndices] = useState([]);
    const [stockQuote, setStockQuote] = useState(null);
    const [orderBook, setOrderBook] = useState({ asks: [], bids: [] });
    const [sectorData, setSectorData] = useState([]);
    const [klineData, setKlineData] = useState({ times: [], values: [] });

    useEffect(() => {
        fetchAllData();
    }, [symbol]);

    const fetchAllData = async () => {
        setLoading(true);
        try {
            // 并行请求所有数据
            const [indicesRes, sectorsRes, quoteRes, orderBookRes, intradayRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/market/indices`),
                axios.get(`${API_BASE_URL}/api/market/sectors`),
                axios.get(`${API_BASE_URL}/api/stock/quote`, { params: { symbol } }),
                axios.get(`${API_BASE_URL}/api/stock/orderbook`, { params: { symbol } }),
                axios.get(`${API_BASE_URL}/api/stock/intraday`, { params: { symbol } })
            ]);

            setMarketIndices(indicesRes.data);
            setSectorData(sectorsRes.data);
            setStockQuote(quoteRes.data);
            setOrderBook(orderBookRes.data);
            setKlineData(intradayRes.data);
        } catch (error) {
            console.error("Failed to fetch stock data:", error);
            message.error(t('stock.fetch_error'));
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (value) => {
        if (value) {
            setSymbol(value);
        }
    };

    // --- Chart Options ---
    const klineOption = {
        backgroundColor: 'transparent',
        grid: { left: 50, right: 50, top: 30, bottom: 30 },
        xAxis: { 
            type: 'category', 
            data: klineData.times,
            axisLine: { lineStyle: { color: '#888' } }
        },
        yAxis: { 
            scale: true,
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
        },
        series: [{
            type: 'candlestick',
            data: klineData.values, // [Open, Close, Low, High]
            itemStyle: {
                color: 'var(--color-secondary)',
                color0: '#ff4d4f',
                borderColor: 'var(--color-secondary)',
                borderColor0: '#ff4d4f'
            }
        }]
    };

    if (loading && !stockQuote) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#fff' }}>
                <Spin tip={t('stock.loading')} />
            </div>
        );
    }

    // 防御性渲染，如果数据还没加载好
    if (!stockQuote) return null;

    return (
        <div style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ color: '#fff', display: 'flex', alignItems: 'center', gap: '12px', margin: 0 }}>
                    <StockOutlined style={{ color: 'var(--color-primary)' }} />
                    {t('stock.title')}
                </h1>
                <Input.Search 
                    placeholder={t('stock.enter_code')} 
                    onSearch={handleSearch}
                    style={{ width: 300 }}
                    allowClear
                    defaultValue={symbol}
                />
            </div>


            {/* Market Indices */}
            <Row gutter={16} style={{ marginBottom: '24px' }}>
                {marketIndices.map((idx, i) => (
                    <Col span={6} key={i}>
                        <div className="glass-card" style={{ padding: '16px', textAlign: 'center' }}>
                            <div style={{ color: '#888', marginBottom: '4px' }}>{idx.name}</div>
                            <div style={{ 
                                fontSize: '20px', 
                                fontWeight: 'bold', 
                                color: idx.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f',
                                fontFamily: 'JetBrains Mono'
                            }}>
                                {idx.value.toFixed(2)}
                            </div>
                            <div style={{ fontSize: '12px', color: idx.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f' }}>
                                {idx.change > 0 ? '+' : ''}{idx.change}% <span style={{ color: '#666', marginLeft: '8px' }}>Vol: {idx.volume}</span>
                            </div>
                        </div>
                    </Col>
                ))}
            </Row>

            <Row gutter={24}>
                {/* Main Chart Area */}
                <Col span={14}>
                    <div className="glass-card" style={{ padding: '20px', height: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #303030', paddingBottom: '16px' }}>
                            <div>
                                <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#fff', marginRight: '12px' }}>{stockQuote.name}</span>
                                <span style={{ fontSize: '16px', color: '#888', fontFamily: 'JetBrains Mono' }}>{stockQuote.code}</span>
                                <Tag color="blue" style={{ marginLeft: '12px' }}>{t('stock.margin')}</Tag>
                                <Tag color="gold">{t('stock.connect')}</Tag>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <span style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--color-secondary)', fontFamily: 'JetBrains Mono' }}>
                                    {stockQuote.price.toFixed(2)}
                                </span>
                                <span style={{ marginLeft: '12px', color: 'var(--color-secondary)' }}>
                                    +{stockQuote.change}% (+{stockQuote.changeAmt})
                                </span>
                            </div>
                        </div>
                        
                        <div style={{ height: '400px' }}>
                            <ReactECharts option={klineOption} style={{ height: '100%' }} />
                        </div>

                        <div style={{ display: 'flex', gap: '24px', marginTop: '16px', color: '#ccc', fontSize: '13px' }}>
                            <div>{t('stock.open')}: <span style={{ color: '#fff' }}>{stockQuote.open}</span></div>
                            <div>{t('stock.high')}: <span style={{ color: 'var(--color-secondary)' }}>{stockQuote.high}</span></div>
                            <div>{t('stock.low')}: <span style={{ color: '#ff4d4f' }}>{stockQuote.low}</span></div>
                            <div>{t('stock.volume')}: <span style={{ color: '#fff' }}>{stockQuote.vol}</span></div>
                            <div>{t('stock.turnover')}: <span style={{ color: '#fff' }}>{stockQuote.amt}</span></div>
                            <div>{t('stock.pe')}: <span style={{ color: '#fff' }}>{stockQuote.pe}</span></div>
                        </div>
                    </div>
                </Col>

                {/* Right Side: Order Book & Sector */}
                <Col span={10}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
                        {/* Order Book */}
                        <div className="glass-card" style={{ padding: '0', flex: 1 }}>
                            <div style={{ padding: '12px', borderBottom: '1px solid #303030', fontWeight: 'bold', color: '#fff' }}>
                                {t('stock.level2')}
                            </div>
                            <div style={{ padding: '12px', fontFamily: 'JetBrains Mono' }}>
                                {orderBook.asks.slice().reverse().map((ask, i) => (
                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ color: '#888' }}>{t('stock.ask')}{5-i}</span>
                                        <span style={{ color: '#ff4d4f' }}>{ask.p.toFixed(2)}</span>
                                        <span style={{ color: '#fff' }}>{ask.v}</span>
                                    </div>
                                ))}
                                <div style={{ borderTop: '1px dashed #444', margin: '8px 0' }} />
                                {orderBook.bids.map((bid, i) => (
                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ color: '#888' }}>{t('stock.bid')}{i+1}</span>
                                        <span style={{ color: 'var(--color-secondary)' }}>{bid.p.toFixed(2)}</span>
                                        <span style={{ color: '#fff' }}>{bid.v}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Sector Heatmap & AI Alert */}
                        <div className="glass-card" style={{ padding: '16px', flex: 1 }}>
                            <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ color: '#fff', fontWeight: 'bold' }}><HeatMapOutlined /> {t('stock.sector_heatmap')}</span>
                                <span style={{ color: '#888', fontSize: '12px' }}>{t('stock.fund_flow')}</span>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {sectorData.map((s, i) => (
                                    <div key={i} style={{ 
                                        padding: '8px 12px', 
                                        background: s.change >= 0 ? 'rgba(0, 230, 118, 0.1)' : 'rgba(255, 77, 79, 0.1)',
                                        border: `1px solid ${s.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f'}`,
                                        borderRadius: '4px',
                                        flex: '1 0 30%'
                                    }}>
                                        <div style={{ color: '#fff', fontSize: '13px' }}>{s.name}</div>
                                        <div style={{ 
                                            color: s.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f', 
                                            fontWeight: 'bold' 
                                        }}>
                                            {s.change > 0 ? '+' : ''}{s.change}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                            
                            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                                <div style={{ color: '#faad14', fontSize: '13px', display: 'flex', gap: '8px' }}>
                                    <AlertOutlined /> AI 异动提醒:
                                </div>
                                <div style={{ color: '#ccc', fontSize: '12px', marginTop: '4px' }}>
                                    14:30 酿酒板块出现大额主力净流入 (+5.2亿)
                                </div>
                            </div>
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export default StockDashboard;
