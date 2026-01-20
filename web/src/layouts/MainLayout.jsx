import React from 'react';
import { Layout, Menu } from 'antd';
import { LineChartOutlined, HistoryOutlined, CodeOutlined, PieChartOutlined } from '@ant-design/icons';

const { Header, Content, Sider } = Layout;

const MainLayout = ({ activeKey, setActiveKey, children }) => {
    const menuItems = [
        { key: '1', icon: <LineChartOutlined />, label: '策略回测' },
        { key: '2', icon: <HistoryOutlined />, label: '历史记录' },
        { key: '3', icon: <PieChartOutlined />, label: '数据分析' },
        { key: '4', icon: <CodeOutlined />, label: '代码编辑' },
    ];

    const getTitle = () => {
        switch (activeKey) {
            case '1': return '策略开发与回测工作台';
            case '2': return '历史回测记录查询';
            case '3': return '多维度策略表现分析';
            case '4': return '策略核心逻辑代码管理';
            default: return '';
        }
    };

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
                    style={{ borderRight: 0, marginTop: 12 }}
                />
            </Sider>
            <Layout>
                <Header style={{ padding: 0, background: '#000', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: 24 }}>
                    <div style={{ paddingLeft: 24, fontSize: 14, color: '#888' }}>
                        {getTitle()}
                    </div>
                    <div style={{ color: '#888', fontSize: 12 }}>
                        Status: <span style={{ color: '#3f8600' }}>Connected</span>
                    </div>
                </Header>
                <Content style={{ margin: 0, padding: 16, background: '#000', overflowY: 'auto' }}>
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
};

export default MainLayout;
