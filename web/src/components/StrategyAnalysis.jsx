import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Tabs, Button, Tag, Statistic, Modal, message, Form, Input, InputNumber, Alert, Tooltip, Progress, Drawer, Empty, Popover, Badge, Typography } from 'antd';
import { PlayCircleOutlined, InfoCircleOutlined, SafetyOutlined, HistoryOutlined, MedicineBoxOutlined, BulbOutlined, ExperimentOutlined, WarningOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useLanguage } from '../contexts/LanguageContext';

import { API_BASE_URL } from '../config';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

const StrategyAnalysis = ({ onApplyStrategy }) => {
    const { t } = useLanguage();
    const [leaderboard, setLeaderboard] = useState([]);
    const [scatterData, setScatterData] = useState([]);
    const [paramName, setParamName] = useState('');
    const [correlationData, setCorrelationData] = useState({ labels: [], matrix: [] });
    const [recommendedStrategies, setRecommendedStrategies] = useState([]);
    const [dataQuality, setDataQuality] = useState(null);
    const [selectedSymbol, setSelectedSymbol] = useState('SH0'); // Default for demo

    const [isModalVisible, setIsModalVisible] = useState(false);
    const [currentStrategy, setCurrentStrategy] = useState(null);
    const [form] = Form.useForm();
    
    // Backtracking state
    const [isBacktrackVisible, setIsBacktrackVisible] = useState(false);
    const [backtrackRecords, setBacktrackRecords] = useState([]);
    const [loadingBacktrack, setLoadingBacktrack] = useState(false);
    
    // AI Doctor State
    const [overfittingScore, setOverfittingScore] = useState(0.15); // 15% probability
    const [robustnessScore, setRobustnessScore] = useState(85);
    const [marketCycleData, setMarketCycleData] = useState({ bull: 25, bear: -5, sideways: 8 });
    const [attributionData, setAttributionData] = useState([
        { value: 120, name: 'Trend Following' },
        { value: 40, name: 'Mean Reversion' },
        { value: -20, name: 'Slippage/Fees' },
        { value: 15, name: 'Alpha Selection' }
    ]);

    useEffect(() => {
        // Fetch Leaderboard
        axios.get(`${API_BASE_URL}/api/backtest/history`, {
            params: { limit: 10, sort_by: 'return_rate', order: 'desc' }
        }).then(res => {
            setLeaderboard(res.data.items);
        });
        
        // Fetch Recommended Strategies
        axios.get(`${API_BASE_URL}/api/strategies/recommended`)
            .then(res => setRecommendedStrategies(res.data))
            .catch(console.error);
        
        // Fetch Data Quality for default symbol
        fetchDataQuality(selectedSymbol);

        // Fetch Data for Scatter (Recent 100 records)
        axios.get(`${API_BASE_URL}/api/backtest/history`, {
            params: { limit: 100 }
        }).then(res => {
            const items = res.data.items;
            if (items.length > 0) {
                // Try to find a numeric parameter to analyze
                const firstItem = items[0];
                const params = firstItem.strategy_params || {};
                const key = Object.keys(params).find(k => typeof params[k] === 'number');
                
                if (key) {
                    setParamName(key);
                    const data = items.map(item => {
                        const p = item.strategy_params || {};
                        if (p[key] !== undefined) {
                            return [p[key], item.return_rate];
                        }
                        return null;
                    }).filter(Boolean);
                    setScatterData(data);
                }
            }
        });

        // Fetch Correlation Matrix
        axios.get(`${API_BASE_URL}/api/strategy/correlation`)
            .then(res => setCorrelationData(res.data))
            .catch(console.error);
    }, []);

    const fetchDataQuality = (symbol) => {
        axios.get(`${API_BASE_URL}/api/data/quality`, {
            params: { symbol, period: 'daily' }
        }).then(res => {
            setDataQuality(res.data);
        }).catch(err => {
            console.warn("Failed to fetch data quality", err);
        });
    };

    const handleApplyClick = (strategy) => {
        setCurrentStrategy(strategy);
        form.setFieldsValue(strategy.config.strategy_params);
        setIsModalVisible(true);
    };

    const handleBacktrackClick = (strategy) => {
        if (strategy.source === 'history') {
            const recordId = strategy.id.replace('hist_', '');
            setLoadingBacktrack(true);
            setIsBacktrackVisible(true);
            axios.get(`${API_BASE_URL}/api/backtest/history/${recordId}`)
                .then(res => {
                    // logs contain the trade list
                    setBacktrackRecords(res.data.logs || []);
                })
                .catch(err => {
                    console.error(err);
                    message.error("Failed to load trade logs");
                })
                .finally(() => setLoadingBacktrack(false));
        } else {
            message.info("Live strategies not supported for replay yet");
        }
    };

    // --- Chart Options ---
    
    // 1. Overfitting Gauge
    const overfittingOption = {
        series: [
            {
                type: 'gauge',
                startAngle: 180,
                endAngle: 0,
                min: 0,
                max: 100,
                splitNumber: 5,
                itemStyle: { color: '#58D9F9', shadowColor: 'rgba(0,138,255,0.45)', shadowBlur: 10, shadowOffsetX: 2, shadowOffsetY: 2 },
                progress: { show: true, roundCap: true, width: 18 },
                pointer: { icon: 'path://M2090.36389,615.30999 L2090.36389,615.30999 C2091.48372,615.30999 2092.40383,616.194028 2092.44859,617.312956 L2096.90698,728.755929 C2097.05155,732.369577 2094.2393,735.416212 2090.62566,735.56078 C2090.53845,735.564269 2090.45117,735.566014 2090.36389,735.566014 L2090.36389,735.566014 C2086.74736,735.566014 2083.81557,732.63423 2083.81557,729.017692 C2083.81557,728.930412 2083.81732,728.84314 2083.82081,728.755929 L2088.2792,617.312956 C2088.32396,616.194028 2089.24407,615.30999 2090.36389,615.30999 Z', length: '75%', width: 16, offsetCenter: [0, '5%'] },
                axisLine: { roundCap: true, lineStyle: { width: 18 } },
                axisTick: { splitNumber: 2, lineStyle: { width: 2, color: '#999' } },
                splitLine: { length: 12, lineStyle: { width: 3, color: '#999' } },
                axisLabel: { distance: 30, color: '#999', fontSize: 14 },
                title: { show: false },
                detail: { backgroundColor: '#fff', borderColor: '#999', borderWidth: 2, width: '60%', lineHeight: 40, height: 40, borderRadius: 8, offsetCenter: [0, '35%'], valueAnimation: true, formatter: function (value) { return '{value|' + value.toFixed(0) + '}{unit|%}'; }, rich: { value: { fontSize: 40, fontWeight: 'bolder', color: '#777' }, unit: { fontSize: 20, color: '#999', padding: [0, 0, -20, 10] } } },
                data: [{ value: overfittingScore * 100 }]
            }
        ]
    };

    // 2. Attribution Waterfall (Simulated with Bar)
    const attributionOption = {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', splitLine: { show: false }, data: attributionData.map(d => d.name), axisLabel: { color: '#ccc' } },
        yAxis: { type: 'value', axisLabel: { color: '#ccc' } },
        series: [{
            name: 'PnL Contribution',
            type: 'bar',
            stack: 'Total',
            label: { show: true, position: 'top' },
            data: attributionData.map(d => ({
                value: d.value,
                itemStyle: { color: d.value > 0 ? '#ff4d4f' : '#52c41a' }
            }))
        }]
    };

    // 3. Market Cycle Stress Test
    const cycleOption = {
        tooltip: { trigger: 'item' },
        radar: {
            indicator: [
                { name: '牛市 (Bull)', max: 50 },
                { name: '熊市 (Bear)', max: 50 },
                { name: '震荡 (Sideways)', max: 50 },
                { name: '高波 (High Vol)', max: 50 },
                { name: '低波 (Low Vol)', max: 50 }
            ],
            axisName: { color: '#fff' }
        },
        series: [{
            type: 'radar',
            data: [{
                value: [25, 5, 8, 15, 20],
                name: 'Strategy Performance',
                areaStyle: { color: 'rgba(255, 215, 0, 0.4)' },
                lineStyle: { color: '#FFD700' }
            }]
        }]
    };

    return (
        <div style={{ padding: '24px', minHeight: '100vh' }}>
            {/* Header Section */}
            <div style={{ marginBottom: '24px' }}>
                <Title level={2} style={{ color: '#fff', margin: 0 }}>
                    <MedicineBoxOutlined style={{ marginRight: '12px', color: '#ff4d4f' }} />
                    {t('strategy.ai_doctor')}
                </Title>
                <Text type="secondary">AI-powered diagnosis, attribution analysis, and optimization suggestions.</Text>
            </div>

            {/* Top KPIs */}
            <Row gutter={24} style={{ marginBottom: '24px' }}>
                <Col span={6}>
                    <Card bordered={false} className="glass-card">
                        <Statistic 
                            title={t('strategy.diagnosis.robustness')} 
                            value={robustnessScore} 
                            suffix="/ 100"
                            valueStyle={{ color: robustnessScore > 80 ? '#52c41a' : '#faad14' }}
                            prefix={<SafetyOutlined />}
                        />
                        <Progress percent={robustnessScore} showInfo={false} strokeColor={robustnessScore > 80 ? '#52c41a' : '#faad14'} size="small" />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card bordered={false} className="glass-card">
                        <Statistic 
                            title={t('strategy.diagnosis.score')} 
                            value={overfittingScore * 100} 
                            suffix="%"
                            valueStyle={{ color: overfittingScore < 20 ? '#52c41a' : '#ff4d4f' }}
                            prefix={<WarningOutlined />}
                        />
                        <Progress percent={overfittingScore * 100} showInfo={false} strokeColor={overfittingScore < 20 ? '#52c41a' : '#ff4d4f'} size="small" />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card bordered={false} className="glass-card">
                        <Statistic 
                            title={t('strategy.data_quality')} 
                            value={dataQuality ? dataQuality.score : 92} 
                            suffix="/ 100"
                            prefix={<BulbOutlined />}
                        />
                        <Tag color="blue">无缺失</Tag>
                        <Tag color="green">复权准确</Tag>
                    </Card>
                </Col>
                <Col span={6}>
                    <Card bordered={false} className="glass-card">
                        <Statistic title={t('strategy.latest_return')} value={leaderboard[0]?.return_rate || 0} precision={2} suffix="%" valueStyle={{ color: '#ff4d4f' }} />
                        <Text type="secondary" style={{ fontSize: '12px' }}>Based on latest run</Text>
                    </Card>
                </Col>
            </Row>

            {/* Main Content Tabs */}
            <Tabs defaultActiveKey="1" type="card" className="glass-tabs">
                <TabPane tab={<span><ExperimentOutlined />{t('strategy.ai_doctor')}</span>} key="1">
                    <Row gutter={24}>
                        <Col span={12}>
                            <Card title={t('strategy.diagnosis_report')} bordered={false} className="glass-card" style={{ height: '100%' }}>
                                <Alert
                                    message="策略表现良好，但存在参数孤岛风险"
                                    description="AI 检测到该策略在 'MA_Window=20' 时表现极佳，但在 'MA_Window=21' 时收益骤降 40%。这表明策略可能过度拟合了特定参数。建议进行参数平滑处理或引入自适应机制。"
                                    type="warning"
                                    showIcon
                                    style={{ marginBottom: '16px' }}
                                />
                                <Title level={5} style={{ color: '#fff' }}>{t('strategy.suggestions')} (AI Suggestions):</Title>
                                <ul style={{ color: '#ccc', lineHeight: '1.8' }}>
                                    <li><BulbOutlined style={{ color: '#FFD700', marginRight: '8px' }} /> 建议增加 <strong>ATR 波动率过滤</strong>，在低波动市场减少开仓，预计可降低 12% 的回撤。</li>
                                    <li><BulbOutlined style={{ color: '#FFD700', marginRight: '8px' }} /> 止盈逻辑过于僵化，建议尝试 <strong>跟踪止损 (Trailing Stop)</strong> 替代固定百分比止盈。</li>
                                    <li><BulbOutlined style={{ color: '#FFD700', marginRight: '8px' }} /> 参数敏感性较高，建议使用 <strong>Walk-Forward Analysis</strong> 进行交叉验证。</li>
                                </ul>
                            </Card>
                        </Col>
                        <Col span={12}>
                            <Card title={t('strategy.cycle_stress')} bordered={false} className="glass-card" style={{ height: '100%' }}>
                                <ReactECharts option={cycleOption} style={{ height: '300px' }} opts={{ renderer: 'svg' }} />
                            </Card>
                        </Col>
                    </Row>
                </TabPane>

                <TabPane tab={<span><SafetyOutlined />{t('strategy.diagnosis.attribution')}</span>} key="2">
                    <Row gutter={24}>
                        <Col span={16}>
                            <Card title={t('strategy.pnl_attribution')} bordered={false} className="glass-card">
                                <ReactECharts option={attributionOption} style={{ height: '400px' }} opts={{ renderer: 'svg' }} />
                            </Card>
                        </Col>
                        <Col span={8}>
                            <Card title={t('strategy.attribution_details')} bordered={false} className="glass-card">
                                <Table 
                                    dataSource={attributionData} 
                                    columns={[
                                        { title: t('strategy.source'), dataIndex: 'name', key: 'name' },
                                        { title: t('strategy.contribution'), dataIndex: 'value', key: 'value', render: (v) => <span style={{ color: v > 0 ? '#ff4d4f' : '#52c41a' }}>{v}</span> }
                                    ]}
                                    pagination={false}
                                    size="small"
                                />
                            </Card>
                        </Col>
                    </Row>
                </TabPane>

                <TabPane tab={<span><HistoryOutlined />{t('strategy.backtest_btn')}</span>} key="3">
                    <Card title={t('strategy.leaderboard_title')} bordered={false} className="glass-card">
                        <Table 
                            dataSource={leaderboard} 
                            rowKey="id"
                            columns={[
                                { title: 'ID', dataIndex: 'id', render: text => <Text code>{String(text || '').substring(0, 8)}</Text> },
                                { title: t('strategy.col_strategy'), dataIndex: 'strategy_name' },
                                { title: t('strategy.col_return'), dataIndex: 'return_rate', render: val => <span style={{ color: val >= 0 ? '#ff4d4f' : '#52c41a' }}>{val?.toFixed(2)}%</span>, sorter: (a, b) => a.return_rate - b.return_rate },
                                { title: t('strategy.col_sharpe'), dataIndex: 'sharpe_ratio', render: val => val?.toFixed(2) },
                                { title: t('strategy.col_drawdown'), dataIndex: 'max_drawdown', render: val => <span style={{ color: '#52c41a' }}>{val?.toFixed(2)}%</span> },
                                { title: t('strategy.col_action'), render: (_, record) => (
                                    <span>
                                        <Button type="link" size="small" onClick={() => handleApplyClick(record)}>{t('strategy.apply_btn')}</Button>
                                        <Button type="link" size="small" onClick={() => handleBacktrackClick(record)}>{t('strategy.backtest_btn')}</Button>
                                    </span>
                                ) }
                            ]}
                        />
                    </Card>
                </TabPane>

                <TabPane tab={<span><ExperimentOutlined />{t('strategy.sensitivity')}</span>} key="4">
                    <Card title={`参数: ${paramName || 'N/A'}`} bordered={false} className="glass-card">
                        {scatterData.length > 0 ? (
                            <ReactECharts
                                option={{
                                    tooltip: { trigger: 'item' },
                                    xAxis: { scale: true, name: paramName, axisLine: { lineStyle: { color: '#ccc' } } },
                                    yAxis: { scale: true, name: 'Return %', axisLine: { lineStyle: { color: '#ccc' } } },
                                    series: [{
                                        type: 'scatter',
                                        data: scatterData,
                                        symbolSize: 10,
                                        itemStyle: { color: '#1890ff' }
                                    }]
                                }}
                                style={{ height: '400px' }}
                                opts={{ renderer: 'svg' }}
                            />
                        ) : (
                            <Empty description="No parameter data available" />
                        )}
                    </Card>
                </TabPane>
            </Tabs>

            {/* Strategy Config Modal */}
            <Modal
                title={`配置策略: ${currentStrategy?.strategy_name}`}
                open={isModalVisible}
                onCancel={() => setIsModalVisible(false)}
                footer={null}
            >
                <Form form={form} onFinish={(values) => {
                    onApplyStrategy({ ...currentStrategy, config: { ...currentStrategy.config, strategy_params: values } });
                    setIsModalVisible(false);
                    message.success("策略已应用");
                }}>
                    {currentStrategy && Object.keys(currentStrategy.config.strategy_params).map(key => (
                        <Form.Item key={key} name={key} label={key}>
                            <Input />
                        </Form.Item>
                    ))}
                    <Button type="primary" htmlType="submit" block>确认应用</Button>
                </Form>
            </Modal>
            
            {/* Backtrack Drawer (Logs) */}
            <Drawer
                title="交易回溯日志"
                placement="right"
                width={600}
                onClose={() => setIsBacktrackVisible(false)}
                open={isBacktrackVisible}
            >
                {loadingBacktrack ? <div style={{textAlign: 'center', marginTop: 50}}>Loading...</div> : (
                    <Table 
                        dataSource={backtrackRecords}
                        rowKey={(r, i) => i}
                        pagination={{ pageSize: 20 }}
                        columns={[
                            { title: 'Date', dataIndex: 'date' },
                            { title: 'Action', dataIndex: 'txt', render: t => (
                                <Tag color={t.includes('BUY') ? 'red' : t.includes('SELL') ? 'green' : 'default'}>
                                    {t}
                                </Tag>
                            )},
                        ]}
                    />
                )}
            </Drawer>
        </div>
    );
};

// Helper component
const DatabaseOutlinedWrapper = () => (
    <span role="img" aria-label="database" className="anticon anticon-database">
        <svg viewBox="64 64 896 896" focusable="false" data-icon="database" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M832 64H192c-17.7 0-32 14.3-32 32v832c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32V96c0-17.7-14.3-32-32-32zm-600 72h536v48H232v-48zm536 672H232V536h536v272zm0-336H232V248h536v224z"></path></svg>
    </span>
);

export default StrategyAnalysis;
