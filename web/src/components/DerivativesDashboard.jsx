import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Tabs, Button, Space, Typography, message } from 'antd';
import { 
    ThunderboltOutlined, 
    FallOutlined, 
    RiseOutlined, 
    CodeSandboxOutlined,
    WarningOutlined,
    DotChartOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import '../styles/design-tokens.css';

const { Title, Text } = Typography;

const DerivativesDashboard = () => {
    const [activeTab, setActiveTab] = useState('futures');
    const [futuresData, setFuturesData] = useState([]);
    const [optionsData, setOptionsData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState({ basis: 0, vix: 0, signal: '-' });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [futuresRes, optionsRes, summaryRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/derivatives/futures`),
                axios.get(`${API_BASE_URL}/api/derivatives/options`),
                axios.get(`${API_BASE_URL}/api/derivatives/summary`)
            ]);
            setFuturesData(futuresRes.data);
            setOptionsData(optionsRes.data);
            setSummary(summaryRes.data);
        } catch (error) {
            console.error("Failed to fetch derivatives data:", error);
            message.error("获取衍生品数据失败");
        } finally {
            setLoading(false);
        }
    };
    const futuresColumns = [
        { title: '合约代码', dataIndex: 'symbol', key: 'symbol', render: t => <b style={{color: '#fff'}}>{t}</b> },
        { title: '名称', dataIndex: 'name', key: 'name' },
        { 
            title: '最新价', 
            dataIndex: 'price', 
            key: 'price',
            render: (text, record) => (
                <span style={{ color: record.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f', fontFamily: 'JetBrains Mono' }}>
                    {text.toFixed(1)}
                </span>
            )
        },
        { 
            title: '涨跌幅', 
            dataIndex: 'change', 
            key: 'change',
            render: text => (
                <Tag color={text >= 0 ? 'success' : 'error'}>
                    {text >= 0 ? '+' : ''}{text}%
                </Tag>
            )
        },
        { title: '成交量', dataIndex: 'volume', key: 'volume', align: 'right' },
        { title: '持仓量', dataIndex: 'openInt', key: 'openInt', align: 'right' },
        { 
            title: '基差 (Basis)', 
            dataIndex: 'basis', 
            key: 'basis', 
            align: 'right',
            render: text => <span style={{ color: text > 0 ? '#faad14' : '#1890ff' }}>{text}</span>
        },
    ];

    // --- Options T-Quote Data (Mock) ---
    // const optionsData = [ ... ] // Replaced by API state

    const tQuoteColumns = [
        { title: 'Call Price', dataIndex: 'callPrice', key: 'callPrice', align: 'right', className: 't-call', render: t => <span style={{color: '#ff4d4f'}}>{t}</span> },
        { title: 'Call Vol', dataIndex: 'callVol', key: 'callVol', align: 'right', className: 't-call' },
        { 
            title: 'Strike', 
            dataIndex: 'strike', 
            key: 'strike', 
            align: 'center',
            render: t => <Tag color="processing" style={{ width: '80px', textAlign: 'center', fontSize: '14px', fontWeight: 'bold' }}>{t}</Tag>
        },
        { title: 'Put Vol', dataIndex: 'putVol', key: 'putVol', className: 't-put' },
        { title: 'Put Price', dataIndex: 'putPrice', key: 'putPrice', className: 't-put', render: t => <span style={{color: 'var(--color-secondary)'}}>{t}</span> },
    ];

    // Volatility Surface Chart Option
    const volSurfaceOption = {
        backgroundColor: 'transparent',
        tooltip: {},
        visualMap: {
            show: false,
            dimension: 2,
            min: 0,
            max: 30,
            inRange: {
                color: ['#1710c0', '#0b5ea8', '#0098d9', '#00c9b1', '#99f37c', '#edf37c', '#f39e7c', '#f3507c']
            }
        },
        xAxis3D: { type: 'category', name: 'Strike' },
        yAxis3D: { type: 'category', name: 'Expiry' },
        zAxis3D: { type: 'value', name: 'IV' },
        grid3D: {
            boxWidth: 200,
            boxDepth: 80,
            viewControl: { projection: 'perspective' },
            light: { main: { intensity: 1.2 }, ambient: { intensity: 0.3 } }
        },
        series: [{
            type: 'bar3D',
            data: [
                [0, 0, 15], [1, 0, 14], [2, 0, 16],
                [0, 1, 18], [1, 1, 17], [2, 1, 19],
                [0, 2, 22], [1, 2, 21], [2, 2, 24],
            ],
            shading: 'lambert',
            itemStyle: { opacity: 0.8 }
        }]
    };

    return (
        <div className="derivatives-container" style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
            <div className="header-section" style={{ marginBottom: '24px' }}>
                <Title level={2} style={{ color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <ThunderboltOutlined style={{ color: '#faad14' }} />
                    衍生品交易台 (Derivatives Desk)
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.45)' }}>高频期货交易 • 期权波动率策略 • 风险对冲中心</Text>
            </div>

            <Row gutter={24} style={{ marginBottom: '24px' }}>
                <Col span={6}>
                    <Statistic 
                        title="主力合约基差 (Basis)" 
                        value={summary.basis} 
                        precision={2} 
                        valueStyle={{ color: '#faad14' }} 
                        prefix={<WarningOutlined />}
                        className="glass-card"
                        style={{ padding: '16px' }}
                    />
                </Col>
                <Col span={6}>
                    <Statistic 
                        title="VIX 波动率指数" 
                        value={summary.vix} 
                        precision={1} 
                        valueStyle={{ color: '#cf1322' }} 
                        prefix={<RiseOutlined />} 
                        suffix={summary.vix >= 25 ? 'High' : 'Normal'}
                        className="glass-card"
                        style={{ padding: '16px' }}
                    />
                </Col>
                <Col span={12}>
                     <div className="glass-card" style={{ padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                            <div style={{ color: '#888' }}>当前策略信号</div>
                            <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#fff' }}>{summary.signal}</div>
                        </div>
                        <Button type="primary" icon={<CodeSandboxOutlined />}>执行策略</Button>
                     </div>
                </Col>
            </Row>

            <Tabs 
                activeKey={activeTab} 
                onChange={setActiveTab} 
                type="card"
                items={[
                    {
                        key: 'futures',
                        label: '期货主力 (Futures)',
                        children: (
                            <div className="glass-card" style={{ padding: '0' }}>
                                <Table 
                                    columns={futuresColumns} 
                                    dataSource={futuresData} 
                                    pagination={false} 
                                    rowClassName="glass-row"
                                />
                            </div>
                        )
                    },
                    {
                        key: 'options',
                        label: '期权链 (Options Chain)',
                        children: (
                            <Row gutter={24}>
                                <Col span={16}>
                                    <div className="glass-card">
                                        <div style={{ padding: '12px', borderBottom: '1px solid #303030', textAlign: 'center', fontWeight: 'bold', color: '#fff' }}>
                                            IO2312 沪深300期权 T型报价 (Call vs Put)
                                        </div>
                                        <Table 
                                            columns={tQuoteColumns} 
                                            dataSource={optionsData} 
                                            pagination={false} 
                                            size="small"
                                            rowClassName="glass-row"
                                        />
                                    </div>
                                </Col>
                                <Col span={8}>
                                    <div className="glass-card" style={{ padding: '12px', height: '100%' }}>
                                        <div style={{ color: '#fff', marginBottom: '8px' }}>IV Surface (波动率曲面)</div>
                                        <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
                                            {/* ECharts 3D surface placeholder - simplified for 2D render if 3D not available */}
                                            <DotChartOutlined style={{ fontSize: '64px', opacity: 0.5 }} />
                                            <div style={{ marginLeft: '12px' }}>3D Surface Visualization</div>
                                        </div>
                                    </div>
                                </Col>
                            </Row>
                        )
                    }
                ]}
            />
        </div>
    );
};

export default DerivativesDashboard;
