import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Tag, Statistic, Spin, Divider, List, Badge } from 'antd';
import { ThunderboltOutlined, FireOutlined, CompassOutlined, CrownOutlined, SafetyOutlined, LineChartOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const { Title, Text, Paragraph } = Typography;

const YiDaoDashboard = () => {
    const [loading, setLoading] = useState(true);
    const [forecast, setForecast] = useState(null);
    const [wisdom, setWisdom] = useState(null);
    const [rotation, setRotation] = useState(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [forecastRes, wisdomRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/yidao/forecast`),
                axios.get(`${API_BASE_URL}/api/yidao/wisdom`)
            ]);
            setForecast(forecastRes.data);
            setWisdom(wisdomRes.data);
            try {
                const rotationRes = await axios.get(`${API_BASE_URL}/api/yidao/rotation`);
                setRotation(rotationRes.data);
            } catch (err) {
                setRotation(null);
            }
        } catch (error) {
            console.error("YiDao Fetch Error:", error);
        } finally {
            setLoading(false);
        }
    };

    const renderHexagram = (code) => {
        // code is string "010..." (Top to Bottom)
        // So we render directly
        const lines = code.split('');
        
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '20px 0' }}>
                {lines.map((bit, index) => (
                    <div key={index} style={{ margin: '4px 0', width: '120px', height: '16px', display: 'flex', justifyContent: 'space-between' }}>
                        {bit === '1' ? (
                            <div style={{ width: '100%', background: '#1890ff', borderRadius: '2px' }}></div>
                        ) : (
                            <>
                                <div style={{ width: '45%', background: '#595959', borderRadius: '2px' }}></div>
                                <div style={{ width: '45%', background: '#595959', borderRadius: '2px' }}></div>
                            </>
                        )}
                    </div>
                ))}
            </div>
        );
    };

    const getTrendColor = (trend) => {
        if (trend.includes("涨") || trend.includes("多") || trend.includes("牛") || trend.includes("升") || trend.includes("火")) return '#cf1322';
        if (trend.includes("跌") || trend.includes("空") || trend.includes("熊") || trend.includes("困") || trend.includes("损")) return '#3f8600';
        return '#faad14';
    };

    if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

    return (
        <div style={{ padding: '24px' }}>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                <Title level={2} style={{ marginBottom: 0 }}>
                    <CompassOutlined /> 易道投资智慧
                </Title>
                <Paragraph type="secondary">
                    观象授时 · 顺势而为 · 象数理占
                </Paragraph>
                {wisdom && (
                    <Card style={{ background: '#f6ffed', borderColor: '#b7eb8f', maxWidth: '800px', margin: '0 auto' }} bodyStyle={{ padding: '12px' }}>
                        <Text strong style={{ fontSize: '16px', color: '#389e0d' }}>
                            <CrownOutlined /> 大师锦囊：{wisdom.content}
                        </Text>
                    </Card>
                )}
            </div>

            {forecast && (
                <Row gutter={[24, 24]}>
                    <Col xs={24} md={8}>
                        <Card title="今日卦象" bordered={false} hoverable>
                            <div style={{ textAlign: 'center' }}>
                                <Title level={3}>{forecast.hexagram.name}</Title>
                                <Tag color="blue">{forecast.hexagram.upper_trigram} 上</Tag>
                                <Tag color="cyan">{forecast.hexagram.lower_trigram} 下</Tag>
                                {renderHexagram(forecast.hexagram.code)}
                                <Divider />
                                <Statistic 
                                    title="卦义" 
                                    value={forecast.hexagram.meaning} 
                                    valueStyle={{ fontSize: '16px', whiteSpace: 'pre-wrap' }} 
                                />
                            </div>
                        </Card>
                    </Col>
                    
                    <Col xs={24} md={10}>
                        <Card title="市场运势解读" bordered={false} hoverable style={{ height: '100%' }}>
                            <Statistic
                                title="趋势判断"
                                value={forecast.hexagram.trend}
                                valueStyle={{ color: getTrendColor(forecast.hexagram.trend), fontWeight: 'bold' }}
                                prefix={<FireOutlined />}
                            />
                            <Divider />
                            <Row gutter={12}>
                                <Col span={12}>
                                    <Statistic title="市场温度" value={`${forecast.market_change_pct ?? 0}%`} prefix={<LineChartOutlined />} />
                                </Col>
                                <Col span={12}>
                                    <Statistic title="风险等级" value={forecast.risk_level} valueStyle={{ color: forecast.risk_level === '高' ? '#cf1322' : forecast.risk_level === '中' ? '#faad14' : '#3f8600' }} />
                                </Col>
                            </Row>
                            <Divider />
                            <Title level={5}>投资建议</Title>
                            <Paragraph style={{ fontSize: '16px' }}>
                                {forecast.hexagram.advice}
                            </Paragraph>
                            <Divider />
                            <Title level={5}>变卦推演</Title>
                            <Paragraph type="secondary">
                                动爻在第 {forecast.moving_line} 爻，未来演化为 
                                <Text strong>【{forecast.future_hexagram.name}】</Text>
                                ({forecast.future_hexagram.trend})
                            </Paragraph>
                            <Divider />
                            <Title level={5}>六爻判断</Title>
                            <Paragraph type="secondary">{forecast.liuyao?.judgement}</Paragraph>
                        </Card>
                    </Col>

                    <Col xs={24} md={6}>
                        <Card title="奇门时空" bordered={false} hoverable style={{ height: '100%' }}>
                            <List size="small">
                                <List.Item>
                                    <List.Item.Meta title="当前五行" description={<Tag color="gold">{forecast.qimen.current_element}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta 
                                        title="吉时方位" 
                                        description={
                                            <span>
                                                {forecast.qimen.lucky_time[0]}方 
                                                <Badge status="processing" text={forecast.qimen.lucky_time[1]} style={{ marginLeft: 8 }} />
                                            </span>
                                        } 
                                    />
                                </List.Item>
                                <List.Item>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>
                                        注：方位指资金流向或利好板块方位（如南方属火，对应科技/能源）。
                                    </Text>
                                </List.Item>
                            </List>
                            <Divider />
                            <div style={{ textAlign: 'center', color: '#999' }}>
                                <ThunderboltOutlined style={{ fontSize: '48px', opacity: 0.2 }} />
                                <div style={{ marginTop: 8 }}>天人合一</div>
                            </div>
                        </Card>
                    </Col>
                </Row>
            )}

            {forecast && (
                <Row gutter={[24, 24]} style={{ marginTop: 12 }}>
                    <Col xs={24} md={8}>
                        <Card title="五行与板块" bordered={false} hoverable>
                            <List size="small">
                                <List.Item>
                                    <List.Item.Meta title="主导五行" description={<Tag color="gold">{forecast.qimen.current_element}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="季节周期" description={<Tag color="blue">{forecast.season_cycle}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="重点板块" description={(forecast.sector_focus || []).map((s) => <Tag key={s} color="purple">{s}</Tag>)} />
                                </List.Item>
                            </List>
                        </Card>
                    </Col>
                    <Col xs={24} md={8}>
                        <Card title="仓位与风控" bordered={false} hoverable>
                            <List size="small">
                                <List.Item>
                                    <List.Item.Meta title="仓位建议" description={<Tag color="cyan">{forecast.position?.range}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="策略风格" description={<Tag color="geekblue">{forecast.position?.style}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="持仓周期" description={<Tag color="blue">{forecast.holding_cycle}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="操作窗口" description={<Text>{forecast.time_window}</Text>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="大师风控" description={<Text>{wisdom?.risk}</Text>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="仓位纪律" description={<Text>{wisdom?.position}</Text>} />
                                </List.Item>
                            </List>
                        </Card>
                    </Col>
                    <Col xs={24} md={8}>
                        <Card title="方法论" bordered={false} hoverable>
                            <List size="small">
                                <List.Item>
                                    <List.Item.Meta title="多维验证" description={(forecast.analysis?.methods || []).map((m) => <Tag key={m} color="volcano">{m}</Tag>)} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="一句话结论" description={<Text>{forecast.analysis?.summary}</Text>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="市场风格" description={<Tag color="purple">{forecast.market_style}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="信号要点" description={(forecast.signals || []).map((s) => <Tag key={s} color="green">{s}</Tag>)} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="操作节奏" description={(forecast.action_steps || []).map((s) => <Tag key={s} color="green">{s}</Tag>)} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="大师原则" description={<Text><SafetyOutlined /> {wisdom?.principle}</Text>} />
                                </List.Item>
                            </List>
                        </Card>
                    </Col>
                </Row>
            )}

            {wisdom && (
                <Row gutter={[24, 24]} style={{ marginTop: 12 }}>
                    <Col xs={24} md={12}>
                        <Card title="交易前自检" bordered={false} hoverable>
                            <List size="small">
                                {(wisdom.checklist || []).map((item) => (
                                    <List.Item key={item}>
                                        <Badge status="processing" text={item} />
                                    </List.Item>
                                ))}
                            </List>
                        </Card>
                    </Col>
                    <Col xs={24} md={12}>
                        <Card title="今日准则" bordered={false} hoverable>
                            <List size="small">
                                <List.Item>
                                    <List.Item.Meta title="总则" description={<Text>{wisdom.content}</Text>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="原则" description={<Text>{wisdom.principle}</Text>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="日期" description={<Text>{wisdom.date}</Text>} />
                                </List.Item>
                            </List>
                        </Card>
                    </Col>
                </Row>
            )}

            {rotation && (
                <Row gutter={[24, 24]} style={{ marginTop: 12 }}>
                    <Col xs={24} md={12}>
                        <Card title="板块轮动清单" bordered={false} hoverable>
                            <List size="small">
                                <List.Item>
                                    <List.Item.Meta title="轮动窗口" description={<Text>{rotation.window}</Text>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="主导五行" description={<Tag color="gold">{rotation.element}</Tag>} />
                                </List.Item>
                                <List.Item>
                                    <List.Item.Meta title="市场趋势" description={<Tag color="purple">{rotation.trend}</Tag>} />
                                </List.Item>
                            </List>
                            <Divider />
                            <List
                                size="small"
                                dataSource={rotation.sectors || []}
                                renderItem={(item) => (
                                    <List.Item>
                                        <List.Item.Meta
                                            title={
                                                <span>
                                                    <Text>{item.name}</Text>
                                                    <Tag color={item.change >= 0 ? 'red' : 'green'} style={{ marginLeft: 8 }}>
                                                        {(item.change > 0 ? '+' : '') + item.change}%
                                                    </Tag>
                                                </span>
                                            }
                                            description={
                                                <span>
                                                    <Tag color={item.action === '跟随' ? 'red' : item.action === '关注' ? 'orange' : item.action === '回避' ? 'default' : 'blue'}>
                                                        {item.action}
                                                    </Tag>
                                                    <Text type="secondary" style={{ marginLeft: 8 }}>{item.reason}</Text>
                                                </span>
                                            }
                                        />
                                    </List.Item>
                                )}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} md={12}>
                        <Card title="执行清单" bordered={false} hoverable>
                            <List size="small">
                                {(rotation.checklist || []).map((item) => (
                                    <List.Item key={item}>
                                        <Badge status="processing" text={item} />
                                    </List.Item>
                                ))}
                            </List>
                        </Card>
                    </Col>
                </Row>
            )}

            <div style={{ marginTop: '48px', textAlign: 'center', color: '#bfbfbf' }}>
                <small>声明：易学预测仅供文化研究与娱乐参考，不构成任何投资建议。市场有风险，投资需谨慎。</small>
            </div>
        </div>
    );
};

export default YiDaoDashboard;
