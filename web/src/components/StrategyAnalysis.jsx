import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Tabs, Button, Tag, Statistic, Modal, message, Form, Input, InputNumber, Alert, Tooltip, Progress, Drawer, Empty, Popover } from 'antd';
import { PlayCircleOutlined, InfoCircleOutlined, SafetyOutlined, HistoryOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';

import { API_BASE_URL } from '../config';

const StrategyAnalysis = ({ onApplyStrategy }) => {
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
                    message.error("获取交易记录失败");
                    console.error(err);
                })
                .finally(() => {
                    setLoadingBacktrack(false);
                });
        } else {
            message.info("此策略为预设策略，请运行回测以生成实时交易记录。");
        }
    };

    const handleModalOk = () => {
        form.validateFields().then(values => {
            const config = { ...currentStrategy.config, strategy_params: values };
            
            if (onApplyStrategy) {
                onApplyStrategy(config);
                message.success(`已加载策略 "${currentStrategy.name}"，正在前往回测页面...`);
            } else {
                message.warning("无法跳转到回测页面");
            }
            
            setIsModalVisible(false);
        });
    };

    const renderStrategyCard = (item) => (
        <Card 
            title={item.name} 
            extra={
                <div>
                    {item.source === 'history' && (
                        <Tooltip title="查看完整交易回溯">
                            <Button type="text" icon={<HistoryOutlined />} onClick={() => handleBacktrackClick(item)} style={{ marginRight: 8 }} />
                        </Tooltip>
                    )}
                    <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => handleApplyClick(item)}>立即使用</Button>
                </div>
            }
            style={{ marginBottom: 16 }}
            className="pro-card"
        >
            <div style={{ marginBottom: 16, height: 66, overflow: 'hidden' }}>
                <Tooltip title={item.description}>
                    <p style={{ 
                        color: '#aaa', 
                        display: '-webkit-box',
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        margin: 0
                    }}>
                        {item.description}
                    </p>
                </Tooltip>
            </div>
            <div style={{ marginBottom: 16 }}>
                {item.tags.map(tag => <Tag key={tag} color="blue">{tag}</Tag>)}
            </div>
            <Row gutter={16}>
                <Col span={6}>
                    <Statistic 
                        title="收益率" 
                        value={item.metrics.return_rate} 
                        precision={2} 
                        suffix="%" 
                        valueStyle={{ color: item.metrics.return_rate > 0 ? '#cf1322' : '#3f8600' }}
                    />
                </Col>
                <Col span={6}>
                    <Statistic title="胜率" value={item.metrics.win_rate} precision={2} suffix="%" />
                </Col>
                <Col span={6}>
                    <Statistic title="最大回撤" value={item.metrics.max_drawdown} precision={2} suffix="%" />
                </Col>
                <Col span={6}>
                    <Statistic title="夏普比率" value={item.metrics.sharpe_ratio} precision={2} />
                </Col>
            </Row>
            <div style={{ marginTop: 16, background: '#141414', padding: 12, borderRadius: 4 }}>
                <div style={{ color: '#888', marginBottom: 4 }}>核心参数：</div>
                <div style={{ 
                    color: '#ccc', 
                    fontFamily: 'monospace', 
                    wordBreak: 'break-all',
                    maxHeight: 60,
                    overflowY: 'auto'
                }}>
                    {JSON.stringify(item.config.strategy_params).replace(/"/g, '').replace(/{|}/g, '')}
                </div>
            </div>
        </Card>
    );

    // ... (Charts options remain same)
    const getScatterOption = () => {
        return {
            backgroundColor: 'transparent',
            title: { text: `参数敏感性 (${paramName} vs 收益率)`, textStyle: { color: '#ccc' } },
            tooltip: {
                formatter: function (params) {
                    return `参数: ${params.data[0]}<br/>收益率: ${params.data[1]}%`;
                }
            },
            xAxis: { 
                name: paramName, 
                scale: true,
                axisLine: { lineStyle: { color: '#555' } },
                axisLabel: { color: '#ccc' }
            },
            yAxis: { 
                name: '收益率(%)', 
                scale: true,
                splitLine: { lineStyle: { color: '#333' } },
                axisLine: { lineStyle: { color: '#555' } },
                axisLabel: { color: '#ccc' }
            },
            series: [{
                symbolSize: 10,
                data: scatterData,
                type: 'scatter',
                itemStyle: { color: '#1890ff' }
            }]
        };
    };

    const getCorrelationOption = () => {
        const { labels, matrix } = correlationData;
        if (!labels || !labels.length) return {};
        
        // Convert matrix to [x, y, value] format for ECharts heatmap
        const data = [];
        for (let i = 0; i < matrix.length; i++) {
            for (let j = 0; j < matrix[i].length; j++) {
                data.push([i, j, matrix[i][j]]);
            }
        }

        return {
            backgroundColor: 'transparent',
            title: { text: '策略相关性矩阵', textStyle: { color: '#ccc' } },
            tooltip: { position: 'top' },
            grid: { height: '70%', top: '15%' },
            xAxis: { 
                type: 'category', 
                data: labels, 
                splitArea: { show: true }, 
                axisLabel: { interval: 0, rotate: 30, color: '#ccc' },
                axisLine: { lineStyle: { color: '#555' } }
            },
            yAxis: { 
                type: 'category', 
                data: labels, 
                splitArea: { show: true },
                axisLabel: { color: '#ccc' },
                axisLine: { lineStyle: { color: '#555' } }
            },
            visualMap: {
                min: -1,
                max: 1,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: '0%',
                inRange: { color: ['#fff', '#1890ff'] },
                textStyle: { color: '#ccc' }
            },
            series: [{
                name: 'Correlation',
                type: 'heatmap',
                data: data,
                label: { show: true },
                emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
            }]
        };
    };

    const columns = [
        { title: '排名', render: (t, r, i) => i + 1, width: 60 },
        { title: '收益率', dataIndex: 'return_rate', render: v => v != null ? <span style={{ color: v > 0 ? '#3f8600' : '#cf1322' }}>{v.toFixed(2)}%</span> : '--' },
        { title: '夏普', dataIndex: 'sharpe_ratio', render: v => v != null ? v.toFixed(2) : '--' },
        { title: '品种', dataIndex: 'symbol' },
        { title: '参数', dataIndex: 'strategy_params', render: v => JSON.stringify(v), ellipsis: true },
    ];

    const tradeColumns = [
        { title: '时间', dataIndex: 'date', width: 150 },
        { title: '品种', dataIndex: 'symbol', width: 80 },
        { 
            title: '方向', 
            dataIndex: 'size', 
            render: (size) => size > 0 ? <Tag color="red">做多</Tag> : <Tag color="green">做空</Tag>,
            width: 80
        },
        { title: '价格', dataIndex: 'price', render: (p) => p != null ? p.toFixed(2) : '-', width: 100 },
        { title: '数量', dataIndex: 'size', render: (s) => s != null ? Math.abs(s) : '-', width: 80 },
        { title: '费用', dataIndex: 'commission', render: (c) => c != null ? c.toFixed(2) : '-', width: 80 },
        { title: '盈亏', dataIndex: 'pnl', render: (p) => p != null ? <span style={{ color: p > 0 ? '#cf1322' : '#3f8600' }}>{p.toFixed(2)}</span> : '-', width: 100 },
        { title: '账户权益', dataIndex: 'value', render: (v) => v != null ? Math.round(v) : '-', width: 120 },
        { title: '决策依据', dataIndex: 'entry_reason', render: (text, record) => record.size !== 0 && text ? <Tooltip title={text}>{text.substring(0, 20)}...</Tooltip> : '-', width: 200 }
    ];

    return (
        <div>
            <Tabs defaultActiveKey="1" style={{ marginBottom: 16 }}>
                <Tabs.TabPane tab="市场分析" key="1">
                    {/* Data Quality Dashboard */}
                    {dataQuality && (
                        <Card title={<span><SafetyOutlined /> 数据质量监控 ({selectedSymbol})</span>} className="pro-card" style={{ marginBottom: 24 }}>
                            <Row gutter={24} align="middle">
                                <Col span={6}>
                                    <div style={{ textAlign: 'center' }}>
                                        <Progress 
                                            type="circle" 
                                            percent={dataQuality.score} 
                                            status="normal"
                                            strokeColor={dataQuality.score < 80 ? '#ff4d4f' : '#52c41a'}
                                            width={80} 
                                            format={percent => <span style={{ color: dataQuality.score < 80 ? '#ff4d4f' : '#52c41a' }}>{percent}%</span>}
                                        />
                                        <div style={{ marginTop: 8, color: '#ccc' }}>综合质量评分</div>
                                    </div>
                                </Col>
                                <Col span={18}>
                                    <Row gutter={[16, 16]}>
                                        <Col span={8}>
                                            <Statistic title="总数据行数" value={dataQuality.total_rows} valueStyle={{ color: '#fff' }} />
                                        </Col>
                                        <Col span={8}>
                                            <Statistic title="数据时间跨度" value={`${dataQuality.start_date || '-'} ~ ${dataQuality.end_date || '-'}`} valueStyle={{ fontSize: 14, color: '#aaa' }} />
                                        </Col>
                                        <Col span={24}>
                                            {dataQuality.issues && dataQuality.issues.length > 0 ? (
                                                <Alert 
                                                    message={
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <span>检测到 {dataQuality.issues.length} 项数据质量问题</span>
                                                            <Popover 
                                                                content={
                                                                    <ul style={{ paddingLeft: 20, margin: 0 }}>
                                                                        {dataQuality.issues.map((issue, idx) => <li key={idx}>{issue}</li>)}
                                                                    </ul>
                                                                } 
                                                                title="问题详情"
                                                                trigger="hover"
                                                            >
                                                                <Button type="link" size="small" style={{ padding: 0 }}>查看详情</Button>
                                                            </Popover>
                                                        </div>
                                                    }
                                                    type="warning" 
                                                    showIcon 
                                                />
                                            ) : (
                                                <Alert message="数据质量良好，未发现明显异常。" type="success" showIcon />
                                            )}
                                        </Col>
                                    </Row>
                                </Col>
                            </Row>
                        </Card>
                    )}

                    <Row gutter={24}>
                        <Col span={12}>
                            <Card title="收益率排行榜 (Top 10)" bordered={false} className="pro-card" style={{ marginBottom: 24 }}>
                                <Table dataSource={leaderboard} columns={columns} rowKey="id" pagination={false} size="small" />
                            </Card>
                            <Card title="参数敏感性分析" bordered={false} className="pro-card">
                                 <ReactECharts option={getScatterOption()} style={{ height: 400 }} theme="dark" />
                            </Card>
                        </Col>
                        <Col span={12}>
                            <Card title="策略相关性矩阵" bordered={false} className="pro-card" style={{ height: '100%' }}>
                                 <ReactECharts option={getCorrelationOption()} style={{ height: 600 }} theme="dark" />
                            </Card>
                        </Col>
                    </Row>
                </Tabs.TabPane>
                <Tabs.TabPane tab="优秀策略解析" key="2">
                     <Row gutter={16}>
                        {recommendedStrategies.map(strategy => (
                            <Col span={8} key={strategy.id || strategy.name}>
                                {renderStrategyCard(strategy)}
                            </Col>
                        ))}
                     </Row>
                </Tabs.TabPane>
            </Tabs>
            
            <Modal
                title="策略参数微调"
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                width={700}
            >
                {currentStrategy && (
                    <div style={{ marginBottom: 24 }}>
                        {currentStrategy.usage_guide && (
                            <Alert
                                message="使用教程"
                                description={currentStrategy.usage_guide}
                                type="info"
                                showIcon
                                style={{ marginBottom: 12 }}
                            />
                        )}
                        {currentStrategy.risk_warning && (
                            <Alert
                                message="注意事项 & 风险提示"
                                description={currentStrategy.risk_warning}
                                type="warning"
                                showIcon
                                style={{ marginBottom: 12 }}
                            />
                        )}
                    </div>
                )}
                <Form form={form} layout="vertical">
                    {currentStrategy && currentStrategy.config && currentStrategy.config.strategy_params && Object.entries(currentStrategy.config.strategy_params).map(([key, value]) => (
                         <Form.Item label={key} name={key} key={key}>
                             {typeof value === 'number' ? <InputNumber style={{ width: '100%' }} /> : <Input />}
                         </Form.Item>
                    ))}
                </Form>
            </Modal>

            <Drawer
                title="策略交易回溯"
                placement="right"
                width={800}
                onClose={() => setIsBacktrackVisible(false)}
                open={isBacktrackVisible}
            >
                {backtrackRecords.length > 0 ? (
                    <Table 
                        dataSource={backtrackRecords} 
                        columns={tradeColumns} 
                        rowKey={(record, index) => index} 
                        pagination={{ pageSize: 20 }}
                        loading={loadingBacktrack}
                        size="small"
                    />
                ) : (
                    <Empty description="暂无交易记录" />
                )}
            </Drawer>
        </div>
    );
};

export default StrategyAnalysis;

