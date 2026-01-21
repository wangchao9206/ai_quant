import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Progress, Tag, List, Badge, Statistic, Spin, message } from 'antd';
import { 
    SoundOutlined, 
    FireOutlined, 
    RiseOutlined, 
    FallOutlined,
    RobotOutlined,
    TwitterOutlined,
    ReadOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../../config';

const SentimentRadar = () => {
    // --- State ---
    const [sentimentData, setSentimentData] = useState({ score: 50, trend: [], status: 'Neutral' });
    const [hotTopics, setHotTopics] = useState([]);
    const [newsStream, setNewsStream] = useState([]);
    const [loading, setLoading] = useState(false);

    // --- Fetch Data ---
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const [overviewRes, topicsRes, newsRes] = await Promise.all([
                    axios.get(`${API_BASE_URL}/api/analysis/sentiment/overview`),
                    axios.get(`${API_BASE_URL}/api/analysis/sentiment/topics`),
                    axios.get(`${API_BASE_URL}/api/analysis/sentiment/news`)
                ]);

                setSentimentData(overviewRes.data);
                setHotTopics(topicsRes.data);
                setNewsStream(newsRes.data);
            } catch (error) {
                console.error("Failed to fetch sentiment data:", error);
                message.error("获取舆情数据失败");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const { score: sentimentScore, trend: sentimentTrend, status: sentimentStatus } = sentimentData;

    // --- Chart Options ---
    const gaugeOption = {
        series: [
            {
                type: 'gauge',
                startAngle: 180,
                endAngle: 0,
                min: 0,
                max: 100,
                splitNumber: 5,
                itemStyle: { color: '#FFD700' },
                progress: {
                    show: true,
                    width: 18,
                    itemStyle: {
                        color: sentimentScore > 50 ? '#ff4d4f' : '#52c41a'
                    }
                },
                pointer: {
                    icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                    length: '12%',
                    width: 20,
                    offsetCenter: [0, '-60%'],
                    itemStyle: { color: 'auto' }
                },
                axisLine: {
                    lineStyle: { width: 18, color: [[1, '#333']] }
                },
                axisTick: { show: false },
                splitLine: { length: 15, lineStyle: { color: 'auto', width: 2 } },
                axisLabel: { color: '#fff', fontSize: 14, distance: -50 },
                title: { offsetCenter: [0, '-20%'], fontSize: 30 },
                detail: {
                    valueAnimation: true,
                    offsetCenter: [0, '10%'],
                    fontSize: 50,
                    fontWeight: 'bolder',
                    formatter: '{value}',
                    color: 'inherit'
                },
                data: [{ value: sentimentScore, name: '贪婪指数' }]
            }
        ]
    };

    const trendOption = {
        backgroundColor: 'transparent',
        grid: { top: 10, bottom: 20, left: 30, right: 10 },
        xAxis: {
            type: 'category',
            data: ['1H', '2H', '3H', '4H', '5H', '6H', '7H', '8H'],
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: '#666' }
        },
        yAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
            axisLabel: { show: false }
        },
        series: [{
            data: sentimentTrend,
            type: 'line',
            smooth: true,
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(255, 77, 79, 0.5)' },
                        { offset: 1, color: 'rgba(255, 77, 79, 0)' }
                    ]
                }
            },
            itemStyle: { color: '#ff4d4f' }
        }]
    };

    return (
        <div style={{ height: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <SoundOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                <h2 style={{ margin: 0, color: '#fff' }}>AI 舆情雷达 (Sentiment Radar)</h2>
                <Tag color="processing">Real-time NLP</Tag>
            </div>

            <Row gutter={24} style={{ flex: 1 }}>
                {/* Left Column: Sentiment Gauge & Trend */}
                <Col span={8} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    <div className="glass-card" style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                        <h3 style={{ color: '#aaa', marginBottom: '20px' }}>全市场情绪温度计</h3>
                        <div style={{ width: '100%', height: '300px' }}>
                            <ReactECharts option={gaugeOption} style={{ height: '100%', width: '100%' }} />
                        </div>
                        <div style={{ textAlign: 'center', marginTop: '-40px' }}>
                            <span style={{ color: sentimentScore > 50 ? '#ff4d4f' : '#52c41a', fontSize: '20px', fontWeight: 'bold' }}>
                                {sentimentStatus}
                            </span>
                            <div style={{ color: '#666', marginTop: '8px' }}>基于 24h 社交媒体与新闻数据</div>
                        </div>
                    </div>
                    
                    <div className="glass-card" style={{ padding: '24px', height: '250px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                            <span style={{ color: '#fff' }}>情绪趋势 (8H)</span>
                            <span style={{ color: '#ff4d4f' }}><RiseOutlined /> 上升趋势</span>
                        </div>
                        <ReactECharts option={trendOption} style={{ height: '180px', width: '100%' }} />
                    </div>
                </Col>

                {/* Middle Column: Hot Topics Word Cloud (Mock) */}
                <Col span={8}>
                    <div className="glass-card" style={{ height: '100%', padding: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
                            <FireOutlined style={{ color: '#ff4d4f' }} />
                            <h3 style={{ margin: 0, color: '#fff' }}>热门概念 (Hot Topics)</h3>
                        </div>
                        
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignContent: 'center', height: 'calc(100% - 60px)' }}>
                            {hotTopics.map((topic, index) => (
                                <Tag 
                                    key={index}
                                    style={{ 
                                        padding: '8px 16px', 
                                        fontSize: `${12 + topic.weight * 1.5}px`,
                                        cursor: 'pointer',
                                        border: 'none',
                                        background: topic.sentiment === 'bullish' ? 'rgba(255, 77, 79, 0.1)' : (topic.sentiment === 'bearish' ? 'rgba(82, 196, 26, 0.1)' : 'rgba(255, 255, 255, 0.05)'),
                                        color: topic.sentiment === 'bullish' ? '#ff4d4f' : (topic.sentiment === 'bearish' ? '#52c41a' : '#ccc')
                                    }}
                                >
                                    {topic.text}
                                </Tag>
                            ))}
                        </div>
                    </div>
                </Col>

                {/* Right Column: AI News Stream */}
                <Col span={8}>
                    <div className="glass-card" style={{ height: '100%', padding: '24px', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
                            <RobotOutlined style={{ color: '#1890ff' }} />
                            <h3 style={{ margin: 0, color: '#fff' }}>AI 智能解读 (News Alpha)</h3>
                        </div>

                        <div style={{ overflowY: 'auto', flex: 1, paddingRight: '8px' }}>
                            <List
                                itemLayout="vertical"
                                dataSource={newsStream}
                                renderItem={item => (
                                    <List.Item style={{ padding: '16px', background: '#1f1f1f', borderRadius: '8px', marginBottom: '16px', border: '1px solid #303030' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                            <Space size={8}>
                                                <Tag color="blue">{item.source}</Tag>
                                                <span style={{ color: '#666', fontSize: '12px' }}>{item.time}</span>
                                            </Space>
                                            <Tag color={item.sentiment === 'bullish' ? 'red' : (item.sentiment === 'bearish' ? 'green' : 'default')}>
                                                影响力: {item.impact}
                                            </Tag>
                                        </div>
                                        <div style={{ color: '#fff', fontSize: '15px', fontWeight: '500', marginBottom: '12px' }}>
                                            {item.title}
                                        </div>
                                        <div style={{ background: 'rgba(24, 144, 255, 0.1)', padding: '12px', borderRadius: '4px', display: 'flex', gap: '12px' }}>
                                            <RobotOutlined style={{ color: '#1890ff', marginTop: '4px' }} />
                                            <span style={{ color: '#ccc', fontSize: '13px' }}>{item.analysis}</span>
                                        </div>
                                    </List.Item>
                                )}
                            />
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

// Helper for Space
const Space = ({ children, size }) => <div style={{ display: 'flex', gap: `${size}px`, alignItems: 'center' }}>{children}</div>;

export default SentimentRadar;
