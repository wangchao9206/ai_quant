import React from 'react';
import { Layout, Menu } from 'antd';
import { 
    LineChartOutlined, 
    HistoryOutlined, 
    CodeOutlined, 
    PieChartOutlined, 
    StockOutlined, 
    FundOutlined, 
    RocketOutlined,
    ThunderboltOutlined,
    GoldOutlined,
    ClockCircleOutlined,
    SoundOutlined,
    SafetyCertificateOutlined,
    GlobalOutlined,
    CompassOutlined
} from '@ant-design/icons';
import { Button, Dropdown } from 'antd';
import { useLanguage } from '../contexts/LanguageContext';

const { Header, Content, Sider } = Layout;

const MainLayout = ({ activeKey, setActiveKey, children }) => {
    const { language, setLanguage, t } = useLanguage();

    const menuItems = [
        { 
            key: 'g_market', 
            type: 'group', 
            label: t('menu.market_overview'), 
            children: [
                { key: '9', icon: <StockOutlined />, label: t('menu.stock') },
                { key: '6', icon: <FundOutlined />, label: t('menu.fund') },
                { key: '7', icon: <ThunderboltOutlined />, label: t('menu.derivs') },
                { key: '8', icon: <GoldOutlined style={{ color: '#FFD700' }} />, label: t('menu.metals') },
            ]
        },
        { 
            key: 'g_tools', 
            type: 'group', 
            label: t('menu.quant_tools'), 
            children: [
                { key: '1', icon: <LineChartOutlined />, label: t('menu.backtest') },
                { key: '3', icon: <PieChartOutlined />, label: t('menu.analysis') },
                { key: '4', icon: <CodeOutlined />, label: t('menu.code') },
                { key: '2', icon: <HistoryOutlined />, label: t('menu.history') },
            ]
        },
        { 
            key: 'g_advanced', 
            type: 'group', 
            label: t('menu.advanced_tools'), 
            children: [
                { key: '10', icon: <ClockCircleOutlined style={{ color: '#52c41a' }} />, label: t('menu.replay') },
                { key: '11', icon: <GlobalOutlined style={{ color: '#1890ff' }} />, label: t('menu.macro') },
                { key: '12', icon: <SoundOutlined style={{ color: '#ff4d4f' }} />, label: t('menu.sentiment') },
                { key: '13', icon: <SafetyCertificateOutlined style={{ color: '#faad14' }} />, label: t('menu.risk') },
            ]
        },
        { 
            key: 'g_wealth', 
            type: 'group', 
            label: t('menu.wealth'), 
            children: [
                { key: '5', icon: <RocketOutlined style={{ color: '#D500F9' }} />, label: t('menu.concept') },
            ]
        },
        { 
            key: 'g_yidao', 
            type: 'group', 
            label: '东方智慧', 
            children: [
                { key: '14', icon: <CompassOutlined style={{ color: '#eb2f96' }} />, label: '易道投资' },
            ]
        },
    ];

    const getTitle = () => {
        switch (activeKey) {
            case '9': return t('header.stock_market');
            case '6': return t('header.fund_screener');
            case '7': return t('header.derivs_desk');
            case '8': return t('header.commodities');
            
            case '1': return t('header.backtest_workbench');
            case '3': return t('header.analysis_dashboard');
            case '4': return t('header.code_manager');
            case '2': return t('header.history_query');
            
            case '10': return t('header.replay_camp');
            case '11': return t('header.macro_calendar');
            case '12': return t('header.sentiment_radar');
            case '13': return t('header.risk_center');

            case '5': return t('header.wealth_cockpit');
            case '14': return '易道投资智慧';
            default: return '';
        }
    };

    const languageItems = [
        { key: 'zh-CN', label: '中文' },
        { key: 'en-US', label: 'English' }
    ];

    return (
        <Layout style={{ height: '100vh', overflow: 'hidden' }}>
            <Sider width={240} style={{ borderRight: '1px solid #303030' }}>
                <div className="logo" style={{ height: 48, display: 'flex', alignItems: 'center', paddingLeft: 24, color: '#fff', fontSize: 16, fontWeight: 'bold', borderBottom: '1px solid #303030' }}>
                    <LineChartOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                    AI Quant Pro
                </div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[activeKey]}
                    items={menuItems}
                    onClick={({ key }) => setActiveKey(key)}
                    style={{ borderRight: 0, marginTop: 12, height: 'calc(100% - 48px)', overflowY: 'auto' }}
                />
            </Sider>
            <Layout>
                <Header style={{ padding: 0, background: '#000', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: 24 }}>
                    <div style={{ paddingLeft: 24, fontSize: 14, color: '#888' }}>
                        {getTitle()}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <Dropdown 
                            menu={{ 
                                items: languageItems, 
                                onClick: ({ key }) => setLanguage(key),
                                selectedKeys: [language]
                            }} 
                            placement="bottomRight"
                        >
                            <Button type="text" style={{ color: '#fff' }} icon={<GlobalOutlined />}>
                                {language === 'zh-CN' ? '中文' : 'English'}
                            </Button>
                        </Dropdown>
                        <div style={{ color: '#888', fontSize: 12 }}>
                            Status: <span style={{ color: '#3f8600' }}>{t('header.status_connected')}</span>
                        </div>
                    </div>
                </Header>
                <Content style={{ margin: 0, padding: 0, background: '#000', overflowY: 'auto', height: '100%' }}>
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
};

export default MainLayout;
