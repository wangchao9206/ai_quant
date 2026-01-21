import React, { useState, useEffect } from 'react';
import { Card, Form, Select, DatePicker, InputNumber, Space, Button, Table, Popconfirm, Modal, Row, Col, App } from 'antd';
import { SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import dayjs from 'dayjs';
import ReactECharts from 'echarts-for-react';
import ResultView from './ResultView';

const { Option } = Select;
const { RangePicker } = DatePicker;

const HistoryPanel = ({ symbols }) => {
    const { message } = App.useApp();
    const [stats, setStats] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
    const [detailVisible, setDetailVisible] = useState(false);
    const [currentDetail, setCurrentDetail] = useState(null);
    const [detailChartType, setDetailChartType] = useState('line');
    const [filters, setFilters] = useState({
        symbol: null,
        dateRange: null,
        minReturn: null
    });

    const fetchStats = () => {
        axios.get(`${API_BASE_URL}/api/backtest/stats`)
            .then(res => setStats(res.data))
            .catch(console.error);
    };

    const fetchHistory = (page = 1, pageSize = 20) => {
        setLoading(true);
        const params = { skip: (page - 1) * pageSize, limit: pageSize };
        if (filters.symbol) params.symbol = filters.symbol;
        if (filters.dateRange) {
            params.start_date = filters.dateRange[0].format('YYYY-MM-DD');
            params.end_date = filters.dateRange[1].format('YYYY-MM-DD');
        }
        if (filters.minReturn !== null) params.min_return = filters.minReturn;

        axios.get(`${API_BASE_URL}/api/backtest/history`, { params })
        .then(res => {
            setHistory(res.data.items);
            setPagination({ ...pagination, current: page, pageSize, total: res.data.total });
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchStats();
        fetchHistory();
    }, []);

    const handleExport = () => {
        const params = {};
        if (filters.symbol) params.symbol = filters.symbol;
        if (filters.dateRange) {
            params.start_date = filters.dateRange[0].format('YYYY-MM-DD');
            params.end_date = filters.dateRange[1].format('YYYY-MM-DD');
        }
        if (filters.minReturn !== null) params.min_return = filters.minReturn;
        
        const queryString = new URLSearchParams(params).toString();
        window.open(`${API_BASE_URL}/api/backtest/export?${queryString}`, '_blank');
    };

    const handleExportPDF = () => {
        const params = {};
        if (filters.symbol) params.symbol = filters.symbol;
        if (filters.dateRange) {
            params.start_date = filters.dateRange[0].format('YYYY-MM-DD');
            params.end_date = filters.dateRange[1].format('YYYY-MM-DD');
        }
        if (filters.minReturn !== null) params.min_return = filters.minReturn;
        
        const queryString = new URLSearchParams(params).toString();
        window.open(`${API_BASE_URL}/api/backtest/export/pdf?${queryString}`, '_blank');
    };

    const viewDetail = async (id) => {
        try {
            const res = await axios.get(`${API_BASE_URL}/api/backtest/${id}`);
            const record = res.data;
            
            // Fetch Summary
            let summaryText = null;
            try {
                const sumRes = await axios.get(`${API_BASE_URL}/api/strategy/summary/${id}`);
                summaryText = sumRes.data.summary;
            } catch (e) {
                console.error("Failed to fetch summary", e);
            }

            // 转换数据结构适配 ResultView
            const transformed = {
                metrics: {
                    initial_cash: record.initial_cash,
                    final_value: record.final_value,
                    net_profit: record.net_profit,
                    sharpe_ratio: record.sharpe_ratio,
                    max_drawdown: record.max_drawdown,
                    total_trades: record.total_trades,
                    win_rate: record.win_rate,
                },
                equity_curve: record.equity_curve || [],
                logs: record.logs || [],
                optimization_info: record.is_optimized ? { triggered: true, message: "优化结果", original_return: 0, optimized_return: record.return_rate } : null
            };
            setCurrentDetail({ ...transformed, summary: summaryText });
            setDetailVisible(true);
        } catch (err) {
            message.error("加载详情失败");
        }
    };

    const deleteRecord = async (id) => {
        try {
            await axios.delete(`${API_BASE_URL}/api/backtest/${id}`);
            message.success("删除成功");
            fetchHistory(pagination.current, pagination.pageSize);
            fetchStats();
        } catch (err) {
            message.error("删除失败");
        }
    };

    const columns = [
        { title: '时间', dataIndex: 'timestamp', render: t => dayjs(t).format('YYYY-MM-DD HH:mm') },
        { title: '品种', dataIndex: 'symbol' },
        { title: '周期', dataIndex: 'period' },
        { title: '收益率', dataIndex: 'return_rate', render: v => v != null ? <span style={{ color: v > 0 ? '#3f8600' : '#cf1322' }}>{v.toFixed(2)}%</span> : <span>--</span> },
        { title: '夏普比率', dataIndex: 'sharpe_ratio', render: v => v != null ? v.toFixed(3) : '--' },
        { title: '最大回撤', dataIndex: 'max_drawdown', render: v => v != null ? `${v.toFixed(2)}%` : '--' },
        { title: '操作', render: (_, r) => (
            <Space>
                <a onClick={() => viewDetail(r.id)}>详情</a>
                <Popconfirm title="确定删除?" onConfirm={() => deleteRecord(r.id)}>
                    <a style={{ color: '#cf1322' }}>删除</a>
                </Popconfirm>
            </Space>
        ) }
    ];

    const getDistributionOption = () => {
        if (!stats) return {};
        const data = Object.entries(stats.return_distribution).map(([k, v]) => ({ name: k, value: v }));
        return {
            backgroundColor: 'transparent',
            title: { text: '收益率分布', textStyle: { color: '#ccc' } },
            tooltip: { trigger: 'item' },
            series: [{
                type: 'pie',
                radius: '50%',
                data: data,
                label: { color: '#ccc' },
                emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
            }]
        };
    };

    return (
        <div className="history-panel">
            <Card bordered={false} className="pro-card" style={{ marginBottom: 24 }}>
                <Form layout="inline">
                    <Form.Item label="品种">
                        <Select 
                            showSearch 
                            style={{ width: 150 }} 
                            allowClear 
                            placeholder="选择品种"
                            onChange={v => setFilters({...filters, symbol: v})}
                            filterOption={(input, option) => option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0}
                        >
                            {symbols.map(s => <Option key={s.code} value={s.code}>{s.name} ({s.code})</Option>)}
                        </Select>
                    </Form.Item>
                    <Form.Item label="时间范围">
                        <RangePicker onChange={v => setFilters({...filters, dateRange: v})} />
                    </Form.Item>
                    <Form.Item label="最低收益率(%)">
                        <InputNumber onChange={v => setFilters({...filters, minReturn: v})} />
                    </Form.Item>
                    <Form.Item>
                        <Space>
                            <Button type="primary" icon={<SearchOutlined />} onClick={() => fetchHistory(1, pagination.pageSize)}>查询</Button>
                            <Button icon={<DownloadOutlined />} onClick={handleExport}>导出Excel</Button>
                            <Button icon={<DownloadOutlined />} onClick={handleExportPDF}>导出PDF</Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Card>

            {stats && (
                <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={6}>
                        <Card title="总回测次数" bordered={false} className="pro-card"><span style={{fontSize: '24px', color: '#1890ff'}}>{stats.total_count}</span></Card>
                    </Col>
                    <Col span={6}>
                        <Card title="平均收益率" bordered={false} className="pro-card"><span style={{fontSize: '24px', color: stats.avg_return > 0 ? '#3f8600' : '#cf1322'}}>{stats.avg_return.toFixed(2)}%</span></Card>
                    </Col>
                    <Col span={6}>
                        <Card title="平均夏普" bordered={false} className="pro-card"><span style={{fontSize: '24px', color: '#1890ff'}}>{stats.avg_sharpe.toFixed(2)}</span></Card>
                    </Col>
                    <Col span={6}>
                        <Card title="正收益占比" bordered={false} className="pro-card"><span style={{fontSize: '24px', color: '#3f8600'}}>{(stats.win_rate_avg * 100).toFixed(1)}%</span></Card>
                    </Col>
                </Row>
            )}

            <Row gutter={24}>
                <Col span={16}>
                    <Card title="回测记录列表" bordered={false} className="pro-card">
                        <Table 
                            dataSource={history} 
                            columns={columns} 
                            rowKey="id" 
                            pagination={{ ...pagination, onChange: fetchHistory }}
                            loading={loading}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card title="收益分布" bordered={false} className="pro-card">
                         <ReactECharts option={getDistributionOption()} style={{ height: 300 }} theme="dark" />
                    </Card>
                </Col>
            </Row>

            <Modal
                title="回测详情"
                open={detailVisible}
                onCancel={() => setDetailVisible(false)}
                footer={null}
                width={1000}
                className="pro-modal"
            >
                <ResultView 
                    results={currentDetail} 
                    chartType={detailChartType} 
                    setChartType={setDetailChartType} 
                    summary={currentDetail?.summary} 
                />
            </Modal>
        </div>
    );
};

export default HistoryPanel;
