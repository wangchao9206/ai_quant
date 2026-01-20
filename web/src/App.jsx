import React, { useState, useEffect } from 'react';
import { ConfigProvider, theme, App as AntdApp, Spin } from 'antd';
import axios from 'axios';
import { API_BASE_URL } from './config';
import MainLayout from './layouts/MainLayout';
import BacktestDashboard from './components/BacktestDashboard';
import HistoryPanel from './components/HistoryPanel';
import StrategyAnalysis from './components/StrategyAnalysis';
import StrategyEditor from './components/StrategyEditor';
import './App.css';

const InnerApp = () => {
    const { message } = AntdApp.useApp();
    const [loading, setLoading] = useState(true);
    const [symbols, setSymbols] = useState([]);
    const [activeKey, setActiveKey] = useState('1');
    const [strategyConfig, setStrategyConfig] = useState(null);

    const handleApplyStrategy = (config) => {
        setStrategyConfig(config);
        setActiveKey('1');
    };

    const handleStrategyApplied = () => {
        setStrategyConfig(null);
    };

    useEffect(() => {
        // Listen for tab switch requests
        const handleSwitchTab = (e) => {
            if (e.detail) {
                setActiveKey(e.detail);
            }
        };

        window.addEventListener('switchTab', handleSwitchTab);

        // Fetch Symbols
        axios.get(`${API_BASE_URL}/api/symbols`)
            .then(res => {
                setSymbols(res.data.futures);
            })
            .catch(err => {
                console.error(err);
                message.error('无法连接到后端服务');
            })
            .finally(() => {
                setLoading(false);
            });

        return () => {
            window.removeEventListener('switchTab', handleSwitchTab);
        };
    }, []);

    const renderContent = () => {
        if (loading) {
            return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin size="large" /></div>;
        }

        switch (activeKey) {
            case '1':
                return (
                    <BacktestDashboard 
                        symbols={symbols} 
                        strategyConfig={strategyConfig}
                        onStrategyApplied={handleStrategyApplied}
                    />
                );
            case '2':
                return <HistoryPanel symbols={symbols} />;
            case '3':
                return <StrategyAnalysis onApplyStrategy={handleApplyStrategy} />;
            case '4':
                return <StrategyEditor />;
            default:
                return (
                    <BacktestDashboard 
                        symbols={symbols} 
                        strategyConfig={strategyConfig}
                        onStrategyApplied={handleStrategyApplied}
                    />
                );
        }
    };

    return (
        <MainLayout activeKey={activeKey} setActiveKey={setActiveKey}>
            {renderContent()}
        </MainLayout>
    );
};

const App = () => {
    return (
        <ConfigProvider
            theme={{
                algorithm: theme.darkAlgorithm,
                token: {
                    colorPrimary: '#1890ff',
                    borderRadius: 2,
                    colorBgContainer: '#141414',
                },
            }}
        >
            <AntdApp>
                <InnerApp />
            </AntdApp>
        </ConfigProvider>
    );
};

export default App;
