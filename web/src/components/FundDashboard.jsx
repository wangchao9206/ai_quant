import React, { useState, useEffect } from 'react';
import { Input, Tag, Table, Button, Space, Typography, Row, Col, Card, message } from 'antd';
import { SearchOutlined, FilterOutlined, FireOutlined, RiseOutlined, CheckCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import '../styles/design-tokens.css';
import { useLanguage } from '../contexts/LanguageContext';

const { Title, Text } = Typography;

const FundDashboard = () => {
    const { t } = useLanguage();
    const [searchText, setSearchText] = useState('');
    const [fundsData, setFundsData] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchFunds();
    }, []);

    const fetchFunds = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/fund/list`);
            setFundsData(response.data);
        } catch (error) {
            console.error("Failed to fetch funds:", error);
            message.error(t('fund.fetch_error'));
        } finally {
            setLoading(false);
        }
    };

    // Mini Sparkline Component (SVG)
    const Sparkline = ({ trend }) => {
        const isUp = trend > 0;
        const color = isUp ? 'var(--color-secondary)' : '#ff4d4f'; // Neon Green or Red
        const points = isUp 
            ? "0,20 10,18 20,15 30,19 40,10 50,5" 
            : "0,5 10,8 20,12 30,10 40,18 50,20";
        
        return (
            <svg width="60" height="25" style={{ overflow: 'visible' }}>
                <polyline 
                    points={points} 
                    fill="none" 
                    stroke={color} 
                    strokeWidth="2" 
                />
                {isUp && <circle cx="50" cy="5" r="2" fill={color} />}
                {!isUp && <circle cx="50" cy="20" r="2" fill={color} />}
            </svg>
        );
    };

    const columns = [
        {
            title: t('fund.columns.info'),
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: '#fff', fontWeight: 'bold' }}>{text}</span>
                    <span style={{ fontSize: '12px', color: '#888' }}>{record.code} | {record.manager}</span>
                </div>
            )
        },
        {
            title: t('fund.columns.type'),
            dataIndex: 'type',
            key: 'type',
            render: type => {
                let color = 'blue';
                if (type === 'Stock') color = 'purple';
                if (type === 'Bond') color = 'orange';
                return <Tag color={color}>{type}</Tag>;
            }
        },
        {
            title: t('fund.columns.nav'),
            dataIndex: 'nav',
            key: 'nav',
            align: 'right',
            render: text => <span style={{ fontFamily: 'JetBrains Mono' }}>{text}</span>
        },
        {
            title: t('fund.columns.trend'),
            key: 'trend',
            render: (_, record) => <Sparkline trend={record.return1y} />
        },
        {
            title: t('fund.columns.return'),
            dataIndex: 'return1y',
            key: 'return1y',
            align: 'right',
            render: text => (
                <span style={{ color: text >= 0 ? 'var(--color-secondary)' : '#ff4d4f', fontFamily: 'JetBrains Mono' }}>
                    {text > 0 ? '+' : ''}{text}%
                </span>
            )
        },
        {
            title: t('fund.columns.sharpe'),
            dataIndex: 'sharpe',
            key: 'sharpe',
            align: 'right',
            render: text => <span style={{ fontFamily: 'JetBrains Mono' }}>{text}</span>
        },
        {
            title: t('fund.columns.action'),
            key: 'action',
            render: () => (
                <Space size="small">
                    <Button type="primary" size="small" ghost>{t('fund.columns.details')}</Button>
                    <Button size="small" style={{ borderColor: 'var(--color-secondary)', color: 'var(--color-secondary)' }}>{t('fund.columns.purchase')}</Button>
                </Space>
            )
        }
    ];

    return (
        <div className="fund-dashboard-container" style={{ color: '#fff', height: '100%', overflowY: 'auto' }}>
            {/* Header Section */}
            <div style={{ 
                marginBottom: '24px', 
                padding: '24px', 
                background: 'rgba(255, 255, 255, 0.04)', 
                borderRadius: '8px', 
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.1)' 
            }}>
                <Title level={2} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <FireOutlined style={{ color: '#ff4d4f' }} />
                    {t('fund.title')}
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.45)' }}>{t('fund.subtitle')}</Text>
                
                <div style={{ marginTop: '24px', maxWidth: '800px' }}>
                    <Input 
                        size="large" 
                        placeholder={t('fund.search_placeholder')} 
                        prefix={<SearchOutlined style={{ color: 'var(--color-primary)' }} />} 
                        value={searchText}
                        onChange={e => setSearchText(e.target.value)}
                        style={{ 
                            background: 'rgba(0,0,0,0.3)', 
                            border: '1px solid var(--color-primary)', 
                            color: '#fff',
                            borderRadius: '4px'
                        }}
                    />
                </div>

                <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ color: '#888', marginRight: '8px' }}>{t('fund.hot_tags')}:</span>
                    <Tag icon={<CheckCircleOutlined />} color="success">{t('fund.tags.morningstar')}</Tag>
                    <Tag icon={<RiseOutlined />} color="processing">{t('fund.tags.positive_3y')}</Tag>
                    <Tag color="warning">{t('fund.tags.high_sharpe')}</Tag>
                    <Tag color="error">{t('fund.tags.tmt')}</Tag>
                    <Tag color="default">{t('fund.tags.double_ten')}</Tag>
                </div>
            </div>

            {/* Main Content Area */}
            <Row gutter={24}>
                <Col span={6}>
                    {/* Filter Sidebar */}
                    <Card 
                        title={<span style={{ color: '#fff' }}><FilterOutlined /> {t('fund.filters')}</span>}
                        bordered={false}
                        style={{ 
                            background: 'rgba(20, 20, 20, 0.6)', 
                            border: '1px solid #303030' 
                        }}
                        headStyle={{ borderBottom: '1px solid #303030' }}
                        bodyStyle={{ padding: '16px' }}
                    >
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ color: '#888', marginBottom: '8px' }}>{t('fund.filter_types.type')}</div>
                            <Space wrap>
                                <Tag.CheckableTag checked>{t('fund.filter_types.all')}</Tag.CheckableTag>
                                <Tag.CheckableTag checked={false}>{t('fund.filter_types.stock')}</Tag.CheckableTag>
                                <Tag.CheckableTag checked={false}>{t('fund.filter_types.hybrid')}</Tag.CheckableTag>
                                <Tag.CheckableTag checked={false}>{t('fund.filter_types.bond')}</Tag.CheckableTag>
                            </Space>
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ color: '#888', marginBottom: '8px' }}>{t('fund.filter_types.inception')}</div>
                            <Space wrap>
                                <Tag.CheckableTag checked={false}>&gt;1年</Tag.CheckableTag>
                                <Tag.CheckableTag checked={false}>&gt;3年</Tag.CheckableTag>
                                <Tag.CheckableTag checked>&gt;5年</Tag.CheckableTag>
                            </Space>
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ color: '#888', marginBottom: '8px' }}>{t('fund.filter_types.scale')}</div>
                            <Space wrap>
                                <Tag.CheckableTag checked>2-10亿</Tag.CheckableTag>
                                <Tag.CheckableTag checked={false}>&gt;10亿</Tag.CheckableTag>
                            </Space>
                        </div>
                        <Button type="primary" block icon={<FilterOutlined />}>{t('fund.filter_types.apply')}</Button>
                    </Card>
                </Col>
                
                <Col span={18}>
                    {/* Results Table */}
                    <div className="glass-table-container">
                        <Table 
                            columns={columns} 
                            dataSource={fundsData} 
                            pagination={false}
                            rowClassName="glass-row"
                            style={{ background: 'transparent' }}
                        />
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export default FundDashboard;
