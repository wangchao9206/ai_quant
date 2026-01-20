import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Statistic, Alert, Tag, Radio, Table, Tabs, Empty, Space, message, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const ResultView = ({ results, chartType, setChartType, summary, config }) => {
    const [activeTab, setActiveTab] = useState('equity');
    const chartRef = useRef(null);
    const [klineData, setKlineData] = useState(null);
    const [period, setPeriod] = useState('daily');
    const [loadingKline, setLoadingKline] = useState(false);

    useEffect(() => {
        if (results && results.chart_data) {
            setKlineData(results.chart_data);
            if (config && config.period) {
                setPeriod(config.period);
            }
        }
    }, [results, config]);

    if (!results) return null;

    const handlePeriodChange = async (e) => {
        const newPeriod = e.target.value;
        setPeriod(newPeriod);
        
        if (!config || !config.symbol) {
            console.warn('Missing config for period change');
            return;
        }

        setLoadingKline(true);
        try {
            console.log('Fetching kline:', config.symbol, newPeriod);
            const response = await axios.get(`${API_BASE_URL}/api/data/kline`, {
                params: {
                    symbol: config.symbol,
                    period: newPeriod,
                    start_date: config.start_date,
                    end_date: config.end_date
                }
            });
            console.log('Kline data received:', response.data);
            setKlineData(response.data);
            
            // Re-render chart explicitly if needed
            if (chartRef.current) {
                // ECharts usually updates automatically when options change, 
                // but sometimes state update timing might be tricky.
            }
        } catch (error) {
            // Retry without date range if 404 (likely due to limited historical minute data)
            if (error.response && error.response.status === 404) {
                try {
                    console.log('Retrying fetch without date range...');
                    const response = await axios.get(`${API_BASE_URL}/api/data/kline`, {
                        params: {
                            symbol: config.symbol,
                            period: newPeriod
                        }
                    });
                    setKlineData(response.data);
                    message.warning('该周期历史数据缺失，已为您展示最新行情数据');
                    return;
                } catch (retryError) {
                    console.error('Retry failed:', retryError);
                }
            }

            console.error('Error fetching kline:', error);
            message.error('获取K线数据失败: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoadingKline(false);
        }
    };

    const getEquityOption = () => {
        return {
            backgroundColor: 'transparent',
            title: { text: '账户权益曲线', textStyle: { color: '#ccc' } },
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { 
                type: 'category', 
                data: results.equity_curve.map(item => item.date),
                axisLine: { lineStyle: { color: '#555' } },
                axisLabel: { color: '#ccc' }
            },
            yAxis: { 
                type: 'value', 
                scale: true, 
                splitLine: { lineStyle: { color: '#333' } },
                axisLabel: { color: '#ccc' }
            },
            series: [{
                name: '权益',
                data: results.equity_curve.map(item => item.value),
                type: 'line',
                smooth: true,
                areaStyle: { opacity: 0.3 },
                itemStyle: { color: '#1890ff' }
            }]
        };
    };

    const getKLineOption = () => {
        if (!klineData || !klineData.dates) return null;
        
        const { dates, ohlc, ma5, ma10, ma20, ma60, volume } = klineData;

        // 生成买卖点标记 (仅当当前周期与回测周期一致时显示)
        const showMarkers = config && period === config.period;
        const markPointData = [];
        
        if (showMarkers && results.trades) {
            results.trades.forEach(trade => {
                const isBuy = trade.direction === '多';
                const color = isBuy ? '#ef5350' : '#26a69a'; // 红涨绿跌
                
                // 开仓标记
                markPointData.push({
                    name: 'Open',
                    coord: [trade.entry_time, trade.entry_price],
                    value: isBuy ? 'Buy' : 'Short',
                    itemStyle: { color: color },
                    label: { offset: [0, -10] }
                });
                
                // 平仓标记
                markPointData.push({
                    name: 'Close',
                    coord: [trade.exit_time, trade.exit_price],
                    value: isBuy ? 'Sell' : 'Cover',
                    itemStyle: { color: isBuy ? '#26a69a' : '#ef5350' }, // 平多用绿(卖)，平空用红(买)
                    label: { offset: [0, 10] },
                    symbolRotate: 180
                });
            });
        }

        return {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' },
                borderWidth: 1,
                borderColor: '#ccc',
                padding: 10,
                textStyle: { color: '#000' },
                backgroundColor: 'rgba(255,255,255,0.9)'
            },
            legend: {
                data: ['KLine', 'MA5', 'MA10', 'MA20', 'MA60'],
                textStyle: { color: '#ccc' },
                top: 30
            },
            axisPointer: { link: [{ xAxisIndex: 'all' }] },
            grid: [
                { left: '5%', right: '5%', top: '10%', height: '60%' },
                { left: '5%', right: '5%', top: '75%', height: '15%' }
            ],
            xAxis: [
                {
                    type: 'category',
                    data: dates,
                    scale: true,
                    boundaryGap: false,
                    axisLine: { onZero: false, lineStyle: { color: '#555' } },
                    splitLine: { show: false },
                    axisLabel: { color: '#ccc' },
                    min: 'dataMin',
                    max: 'dataMax'
                },
                {
                    type: 'category',
                    gridIndex: 1,
                    data: dates,
                    axisLabel: { show: false }
                }
            ],
            yAxis: [
                {
                    scale: true,
                    splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.01)', 'rgba(255,255,255,0.05)'] } },
                    axisLine: { lineStyle: { color: '#555' } },
                    splitLine: { lineStyle: { color: '#333' } },
                    axisLabel: { color: '#ccc' }
                },
                {
                    scale: true,
                    gridIndex: 1,
                    splitNumber: 2,
                    axisLabel: { show: false },
                    axisLine: { show: false },
                    splitLine: { show: false }
                }
            ],
            dataZoom: [
                { type: 'inside', xAxisIndex: [0, 1], start: 80, end: 100 },
                { show: true, xAxisIndex: [0, 1], type: 'slider', bottom: '2%', start: 80, end: 100, textStyle: { color: '#ccc' } }
            ],
            series: [
                {
                    name: 'KLine',
                    type: 'candlestick',
                    data: ohlc,
                    itemStyle: {
                        color: '#ef5350',
                        color0: '#26a69a',
                        borderColor: '#ef5350',
                        borderColor0: '#26a69a'
                    },
                    markPoint: {
                        label: { formatter: '{b}', color: '#fff' },
                        data: markPointData,
                        symbolSize: 40
                    }
                },
                { name: 'MA5', type: 'line', data: ma5, smooth: true, lineStyle: { opacity: 0.8, width: 1 } },
                { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { opacity: 0.8, width: 1 } },
                { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { opacity: 0.8, width: 1 } },
                { name: 'MA60', type: 'line', data: ma60, smooth: true, lineStyle: { opacity: 0.8, width: 1 } },
                {
                    name: 'Volume',
                    type: 'bar',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: volume,
                    itemStyle: { color: '#7f8c8d' }
                }
            ]
        };
    };

    const handleTradeClick = (record) => {
        // 如果当前周期不匹配，无法跳转
        if (config && period !== config.period) {
            message.warning(`请先切换回 ${config.period} 周期查看交易点位`);
            setPeriod(config.period);
            setKlineData(results.chart_data);
            // 之后会触发 useEffect 吗？不，这里手动设置了。
            // 最好是设置 period，让 useEffect 或者 handler 去处理。
            // 但这里直接设置数据最快。
        }

        setActiveTab('kline');
        setTimeout(() => {
            if (chartRef.current && results.chart_data) { // Use results.chart_data because we switch back
                const instance = chartRef.current.getEchartsInstance();
                const dates = results.chart_data.dates;
                const index = dates.indexOf(record.entry_time);
                
                if (index !== -1) {
                    const total = dates.length;
                    const range = 100;
                    const start = Math.max(0, index - range / 2);
                    const end = Math.min(total, start + range);
                    
                    const startPercent = (start / total) * 100;
                    const endPercent = (end / total) * 100;

                    instance.dispatchAction({
                        type: 'dataZoom',
                        start: startPercent,
                        end: endPercent
                    });
                } else {
                    message.warning('该交易时间点在图表中未找到');
                }
            }
        }, 100);
    };

    const getMetricsData = () => {
        const m = results.metrics;
        return [
            { key: '1', metric: '最终权益', value: m.final_value != null ? m.final_value.toFixed(2) : '--' },
            { key: '2', metric: '净利润', value: m.net_profit != null ? m.net_profit.toFixed(2) : '--' },
            { key: '3', metric: '夏普比率', value: m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(4) : '--' },
            { key: '4', metric: '最大回撤', value: m.max_drawdown != null ? `${m.max_drawdown.toFixed(2)}%` : '--' },
            { key: '5', metric: '总交易次数', value: m.total_trades != null ? m.total_trades : '--' },
            { key: '6', metric: '胜率', value: m.win_rate != null ? `${m.win_rate.toFixed(2)}%` : '--' },
        ];
    };

    const tradeColumns = [
        { 
            title: '开仓信息', 
            children: [
                { title: '时间', dataIndex: 'entry_time', width: 140, sorter: (a, b) => a.entry_time.localeCompare(b.entry_time) },
                { title: '价格', dataIndex: 'entry_price', width: 100, render: v => v != null ? v.toFixed(4) : '--', sorter: (a, b) => a.entry_price - b.entry_price },
                { title: '数量', dataIndex: 'size', width: 80 },
                { title: '开仓依据', dataIndex: 'entry_reason', width: 200, ellipsis: true },
            ]
        },
        { 
            title: '方向', 
            dataIndex: 'direction', 
            width: 80, 
            render: (t) => <Tag color={t === '多' ? 'red' : 'green'}>{t}</Tag>,
            filters: [{ text: '多', value: '多' }, { text: '空', value: '空' }],
            onFilter: (value, record) => record.direction === value
        },
        { 
            title: '平仓信息',
            children: [
                { title: '时间', dataIndex: 'exit_time', width: 140, sorter: (a, b) => a.exit_time.localeCompare(b.exit_time) },
                { title: '价格', dataIndex: 'exit_price', width: 100, render: v => v != null ? v.toFixed(4) : '--' },
                { title: '平仓依据', dataIndex: 'exit_reason', width: 200, ellipsis: true },
            ]
        },
        { 
            title: '绩效',
            children: [
                { 
                    title: '点数', 
                    dataIndex: 'profit_points', 
                    width: 100, 
                    render: v => v != null ? <span style={{ color: v > 0 ? '#ef5350' : '#26a69a' }}>{v.toFixed(4)}</span> : '--', 
                    sorter: (a, b) => a.profit_points - b.profit_points 
                },
                { 
                    title: '收益率', 
                    dataIndex: 'return_rate', 
                    width: 100, 
                    render: v => v != null ? <span style={{ color: v > 0 ? '#ef5350' : '#26a69a' }}>{v.toFixed(2)}%</span> : '--', 
                    sorter: (a, b) => a.return_rate - b.return_rate 
                },
                { 
                    title: '净利', 
                    dataIndex: 'net_pnl', 
                    width: 100, 
                    render: v => v != null ? <span style={{ color: v > 0 ? '#ef5350' : '#26a69a', fontWeight: 'bold' }}>{v.toFixed(2)}</span> : '--', 
                    sorter: (a, b) => a.net_pnl - b.net_pnl 
                },
            ]
        },
        { title: 'K线数', dataIndex: 'bars', width: 80 }
    ];

    const chartItems = [
        {
            key: 'equity',
            label: '权益曲线',
            children: <ReactECharts option={getEquityOption()} style={{ height: 400 }} theme="dark" />
        },
        {
            key: 'kline',
            label: 'K线复盘',
            children: (
                <div style={{ position: 'relative' }}>
                    <div style={{ marginBottom: 10, textAlign: 'right' }}>
                        <Space>
                            <span style={{ color: '#ccc' }}>周期切换:</span>
                            <Radio.Group value={period} onChange={handlePeriodChange} size="small" buttonStyle="solid">
                                <Radio.Button value="1">1分钟</Radio.Button>
                                <Radio.Button value="5">5分钟</Radio.Button>
                                <Radio.Button value="15">15分钟</Radio.Button>
                                <Radio.Button value="30">30分钟</Radio.Button>
                                <Radio.Button value="60">1小时</Radio.Button>
                                <Radio.Button value="240">4小时</Radio.Button>
                                <Radio.Button value="daily">日线</Radio.Button>
                                <Radio.Button value="weekly">周线</Radio.Button>
                            </Radio.Group>
                        </Space>
                    </div>
                    {loadingKline ? (
                        <div style={{ height: 500, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                            <Spin size="large" tip="加载数据中..." />
                        </div>
                    ) : (
                        klineData ? 
                        <ReactECharts ref={chartRef} option={getKLineOption()} style={{ height: 500 }} theme="dark" /> : 
                        <Empty description="无K线数据" />
                    )}
                </div>
            )
        }
    ];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {results.optimization_info?.triggered && (
                <Alert
                    message="策略已自动优化"
                    description={
                        <div>
                            <p>{results.optimization_info.message}</p>
                            <div>
                                <Tag color="orange">原始收益: {results.optimization_info.original_return.toFixed(2)}%</Tag>
                                <Tag color="green">优化后收益: {results.optimization_info.optimized_return.toFixed(2)}%</Tag>
                            </div>
                        </div>
                    }
                    type="success"
                    showIcon
                />
            )}

            <Row gutter={16}>
                {getMetricsData().map(item => (
                    <Col span={4} key={item.key}>
                        <Card bordered={false} className="pro-card">
                            <Statistic 
                                title={item.metric} 
                                value={item.value} 
                                valueStyle={{ color: item.metric === '净利润' && parseFloat(item.value) > 0 ? '#ef5350' : undefined }}
                            />
                        </Card>
                    </Col>
                ))}
            </Row>

            <Card bordered={false} className="pro-card">
                <Tabs activeKey={activeTab} onChange={setActiveTab} items={chartItems} />
            </Card>

            <Card title="交易清单 (点击行可跳转K线)" bordered={false} className="pro-card">
                <Table 
                    dataSource={results.trades} 
                    columns={tradeColumns} 
                    rowKey={(record, index) => `${record.entry_time}-${index}`}
                    scroll={{ x: 1200 }}
                    pagination={{ pageSize: 10 }}
                    onRow={(record) => ({
                        onClick: () => handleTradeClick(record),
                        style: { cursor: 'pointer' }
                    })}
                />
            </Card>

            {summary && (
                <Card title="策略总结报告" bordered={false} className="pro-card">
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#d9d9d9' }}>
                        {summary}
                    </div>
                </Card>
            )}
        </div>
    );
};

export default ResultView;
