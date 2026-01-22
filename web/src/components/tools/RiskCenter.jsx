import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Alert, Spin, message, Tag } from 'antd';
import { 
    SafetyCertificateOutlined, 
    WarningOutlined, 
    DashboardOutlined, 
    FallOutlined,
    ThunderboltOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../../config';
import { useLanguage } from '../../contexts/LanguageContext';

const RiskCenter = () => {
    const { t } = useLanguage();
    // --- State ---
    const [portfolioRisk, setPortfolioRisk] = useState({
        var95: 0,
        var99: 0,
        beta: 0,
        sharpe: 0,
        maxDrawdown: 0
    });
    const [correlationInfo, setCorrelationInfo] = useState({ assets: [], matrix: [] });
    const [stressTests, setStressTests] = useState([]);
    const [loading, setLoading] = useState(false);

    // --- Fetch Data ---
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const [metricsRes, corrRes, stressRes] = await Promise.all([
                    axios.get(`${API_BASE_URL}/api/analysis/risk/metrics`),
                    axios.get(`${API_BASE_URL}/api/analysis/risk/correlation`),
                    axios.get(`${API_BASE_URL}/api/analysis/risk/stress-test`)
                ]);

                setPortfolioRisk(metricsRes.data);
                setCorrelationInfo(corrRes.data);
                setStressTests(stressRes.data);
            } catch (error) {
                console.error("Failed to fetch risk data:", error);
                message.error(t('risk.fetch_error'));
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const { assets, matrix: correlationData } = correlationInfo;


    // --- Chart Options ---
    const heatmapOption = {
        tooltip: { position: 'top' },
        grid: { height: '80%', top: '10%' },
        xAxis: { type: 'category', data: assets, axisLabel: { color: '#ccc' } },
        yAxis: { type: 'category', data: assets, axisLabel: { color: '#ccc' } },
        visualMap: {
            min: -1, max: 1,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '0%',
            inRange: { color: ['#52c41a', '#141414', '#ff4d4f'] } // Green (neg corr) -> Black -> Red (pos corr)
        },
        series: [{
            name: 'Correlation',
            type: 'heatmap',
            data: correlationData,
            label: { show: true, color: '#fff' },
            itemStyle: {
                emphasis: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
            }
        }]
    };

    const varOption = {
        color: ['#1890ff'],
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { 
            type: 'category', 
            boundaryGap: false, 
            data: portfolioRisk.dates && portfolioRisk.dates.length > 0 ? portfolioRisk.dates : Array.from({length: 30}, (_, i) => `T-${30-i}`),
            axisLine: { lineStyle: { color: '#666' } }
        },
        yAxis: { 
            type: 'value',
            splitLine: { lineStyle: { color: '#333' } },
            scale: true
        },
        series: [{
            name: 'Portfolio Value',
            type: 'line',
            smooth: true,
            data: portfolioRisk.curve && portfolioRisk.curve.length > 0 ? portfolioRisk.curve : [],
            markArea: {
                itemStyle: { color: 'rgba(255, 77, 79, 0.1)' },
                data: [[{ xAxis: 'T-5' }, { xAxis: 'T-1' }]]
            }
        }]
    };

    return (
        <div style={{ height: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <SafetyCertificateOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                <h2 style={{ margin: 0, color: '#fff' }}>{t('risk.title')}</h2>
            </div>

            {/* Top Stats */}
            <Row gutter={24}>
                <Col span={6}>
                    <div className="glass-card" style={{ padding: '20px' }}>
                        <Statistic 
                            title={t('risk.metrics.var95')} 
                            value={portfolioRisk.var95} 
                            prefix="¥" 
                            valueStyle={{ color: '#ff4d4f' }} 
                        />
                        <div style={{ color: '#666', fontSize: '12px', marginTop: '8px' }}>最大可能单日亏损 (95%置信度)</div>
                    </div>
                </Col>
                <Col span={6}>
                    <div className="glass-card" style={{ padding: '20px' }}>
                        <Statistic 
                            title={t('risk.metrics.beta')} 
                            value={portfolioRisk.beta} 
                            precision={2}
                            valueStyle={{ color: portfolioRisk.beta > 1 ? '#faad14' : '#fff' }} 
                        />
                        <div style={{ color: '#666', fontSize: '12px', marginTop: '8px' }}>相对市场波动率</div>
                    </div>
                </Col>
                <Col span={6}>
                    <div className="glass-card" style={{ padding: '20px' }}>
                        <Statistic 
                            title={t('risk.metrics.sharpe')} 
                            value={portfolioRisk.sharpe} 
                            precision={2}
                            valueStyle={{ color: '#52c41a' }} 
                        />
                        <div style={{ color: '#666', fontSize: '12px', marginTop: '8px' }}>风险调整后收益</div>
                    </div>
                </Col>
                <Col span={6}>
                    <div className="glass-card" style={{ padding: '20px' }}>
                        <Statistic 
                            title={t('risk.metrics.drawdown')} 
                            value={portfolioRisk.maxDrawdown} 
                            precision={2}
                            suffix="%"
                            valueStyle={{ color: '#ff4d4f' }} 
                        />
                        <div style={{ color: '#666', fontSize: '12px', marginTop: '8px' }}>历史最大跌幅</div>
                    </div>
                </Col>
            </Row>

            <Row gutter={24} style={{ flex: 1 }}>
                {/* Correlation Matrix */}
                <Col span={12}>
                    <div className="glass-card" style={{ height: '100%', padding: '24px', display: 'flex', flexDirection: 'column' }}>
                        <h3 style={{ color: '#fff', marginBottom: '20px' }}>{t('risk.correlation_matrix')}</h3>
                        <div style={{ flex: 1 }}>
                            <ReactECharts option={heatmapOption} style={{ height: '100%', width: '100%' }} />
                        </div>
                    </div>
                </Col>

                {/* Stress Test & Alerts */}
                <Col span={12} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    <div className="glass-card" style={{ flex: 1, padding: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
                            <ThunderboltOutlined style={{ color: '#faad14' }} />
                            <h3 style={{ margin: 0, color: '#fff' }}>{t('risk.stress_test')}</h3>
                        </div>
                        <Table 
                            dataSource={stressTests}
                            pagination={false}
                            rowKey="scenario"
                            columns={[
                                { title: '情景假设', dataIndex: 'scenario', key: 'scenario', render: t => <span style={{ color: '#fff' }}>{t}</span> },
                                { title: '预计净值影响', dataIndex: 'impact', key: 'impact', render: t => <span style={{ color: t.includes('-') ? '#ff4d4f' : '#52c41a', fontWeight: 'bold' }}>{t}</span> },
                                { title: '发生概率', dataIndex: 'probability', key: 'probability', render: t => <Tag color={t === 'Low' ? 'blue' : 'orange'}>{t}</Tag> }
                            ]}
                        />
                    </div>

                    <div className="glass-card" style={{ padding: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                            <WarningOutlined style={{ color: '#ff4d4f' }} />
                            <h3 style={{ margin: 0, color: '#fff' }}>风控预警 (Active Alerts)</h3>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <Alert message="持仓集中度警告: 科技板块占比超过 40%" type="warning" showIcon style={{ background: 'rgba(250, 173, 20, 0.1)', border: '1px solid #faad14' }} />
                            <Alert message="流动性风险: 某持仓个股日均成交额过低" type="error" showIcon style={{ background: 'rgba(255, 77, 79, 0.1)', border: '1px solid #ff4d4f' }} />
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export default RiskCenter;
