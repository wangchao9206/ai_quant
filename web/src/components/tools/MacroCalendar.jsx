import React, { useState, useEffect } from 'react';
import { Table, Tag, Badge, Tooltip, Select, Button, Calendar, Spin, message } from 'antd';
import { 
    GlobalOutlined, 
    FlagOutlined, 
    InfoCircleOutlined, 
    CalendarOutlined,
    StarFilled
} from '@ant-design/icons';
import dayjs from 'dayjs';
import axios from 'axios';
import { API_BASE_URL } from '../../config';

const MacroCalendar = () => {
    // --- State ---
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedCountries, setSelectedCountries] = useState(['US', 'CN', 'EU']);
    const [selectedDate, setSelectedDate] = useState(dayjs());

    // --- Fetch Data ---
    useEffect(() => {
        const fetchEvents = async () => {
            setLoading(true);
            try {
                const countriesStr = selectedCountries.join(',');
                const dateStr = selectedDate.format('YYYY-MM-DD');
                // Note: Backend currently mocks data regardless of date, but accepts it.
                // It also accepts comma separated countries.
                const response = await axios.get(`${API_BASE_URL}/api/market/macro/calendar`, {
                    params: {
                        date: dateStr,
                        countries: countriesStr
                    }
                });
                setEvents(response.data);
            } catch (error) {
                console.error("Failed to fetch macro calendar:", error);
                message.error("获取宏观日历失败");
            } finally {
                setLoading(false);
            }
        };

        fetchEvents();
    }, [selectedCountries, selectedDate]);

    const columns = [
        {
            title: '时间',
            dataIndex: 'time',
            key: 'time',
            width: 100,
            render: text => <span style={{ fontFamily: 'JetBrains Mono', color: '#888' }}>{text}</span>
        },
        {
            title: '地区',
            dataIndex: 'country',
            key: 'country',
            width: 80,
            align: 'center',
            render: (code) => {
                const flags = { 'US': '🇺🇸', 'EU': '🇪🇺', 'CN': '🇨🇳', 'JP': '🇯🇵', 'UK': '🇬🇧' };
                return <span style={{ fontSize: '20px' }}>{flags[code] || code}</span>;
            }
        },
        {
            title: '事件 / 指标',
            dataIndex: 'event',
            key: 'event',
            render: (text, record) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#fff', fontWeight: 500 }}>{text}</span>
                    {record.importance === 'high' && <Tag color="red">重要</Tag>}
                </div>
            )
        },
        {
            title: '重要性',
            dataIndex: 'importance',
            key: 'importance',
            width: 100,
            render: (imp) => {
                const stars = imp === 'high' ? 3 : (imp === 'medium' ? 2 : 1);
                return (
                    <div style={{ color: imp === 'high' ? '#ff4d4f' : '#faad14' }}>
                        {[...Array(stars)].map((_, i) => <StarFilled key={i} />)}
                    </div>
                );
            }
        },
        {
            title: '今值',
            dataIndex: 'actual',
            key: 'actual',
            width: 100,
            render: (text, record) => {
                // Simple logic to colorize based on comparison (mock)
                const isBetter = parseFloat(text) > parseFloat(record.forecast);
                const color = isBetter ? 'var(--color-secondary)' : '#ff4d4f';
                return <span style={{ fontWeight: 'bold', color: color, fontFamily: 'JetBrains Mono' }}>{text}</span>;
            }
        },
        {
            title: '预测',
            dataIndex: 'forecast',
            key: 'forecast',
            width: 100,
            render: text => <span style={{ color: '#888', fontFamily: 'JetBrains Mono' }}>{text}</span>
        },
        {
            title: '前值',
            dataIndex: 'previous',
            key: 'previous',
            width: 100,
            render: text => <span style={{ color: '#888', fontFamily: 'JetBrains Mono' }}>{text}</span>
        },
        {
            title: '影响解读',
            dataIndex: 'impact',
            key: 'impact',
            render: text => <span style={{ color: '#ccc', fontSize: '12px' }}>{text}</span>
        }
    ];

    return (
        <div style={{ height: '100%', padding: '24px', display: 'flex', gap: '24px' }}>
            {/* Left: Calendar Picker & Filters */}
            <div className="glass-card" style={{ width: '320px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <h2 style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <GlobalOutlined style={{ color: '#1890ff' }} />
                    宏观日历
                </h2>
                
                <div style={{ background: '#1f1f1f', borderRadius: '8px', padding: '10px' }}>
                    <Calendar 
                        fullscreen={false} 
                        value={selectedDate}
                        onChange={setSelectedDate}
                    />
                </div>

                <div>
                    <div style={{ color: '#888', marginBottom: '8px' }}>国家/地区筛选</div>
                    <Select 
                        mode="multiple" 
                        style={{ width: '100%' }} 
                        placeholder="选择国家" 
                        value={selectedCountries}
                        onChange={setSelectedCountries}
                        options={[
                            { label: '🇺🇸 美国 (USA)', value: 'US' },
                            { label: '🇨🇳 中国 (CHN)', value: 'CN' },
                            { label: '🇪🇺 欧元区 (EUR)', value: 'EU' },
                            { label: '🇯🇵 日本 (JPN)', value: 'JP' },
                        ]}
                    />
                </div>

                <div>
                    <div style={{ color: '#888', marginBottom: '8px' }}>重要性筛选</div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <Button type="primary" danger ghost>高重要性</Button>
                        <Button>中等</Button>
                        <Button>低</Button>
                    </div>
                </div>
            </div>

            {/* Right: Data List */}
            <div className="glass-card" style={{ flex: 1, padding: '0', display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '20px', borderBottom: '1px solid #303030', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '16px', color: '#fff', fontWeight: 'bold' }}>
                        {selectedDate.format('YYYY年MM月DD日')} 财经数据概览
                    </span>
                    <Button type="link" icon={<FlagOutlined />}>查看完整周历</Button>
                </div>
                
                <Table 
                    dataSource={events} 
                    columns={columns} 
                    rowKey="id"
                    pagination={false}
                    className="custom-table"
                    loading={loading}
                />

                <div style={{ padding: '20px', marginTop: 'auto', background: 'rgba(24, 144, 255, 0.05)', borderTop: '1px solid #303030' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                        <InfoCircleOutlined style={{ color: '#1890ff', marginTop: '4px' }} />
                        <div>
                            <div style={{ color: '#fff', fontWeight: 'bold', marginBottom: '4px' }}>AI 宏观分析师观点:</div>
                            <div style={{ color: '#ccc', fontSize: '13px', lineHeight: '1.5' }}>
                                本周重点关注美国非农数据与CPI通胀指标。若非农数据显著超预期，可能推迟美联储降息预期，利空黄金与非美货币；反之则利好风险资产。建议投资者在数据发布前降低杠杆，规避短时剧烈波动风险。
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MacroCalendar;
