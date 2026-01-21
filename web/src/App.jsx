import React, { useState, useEffect } from 'react';
import { ConfigProvider, theme, App as AntdApp, Spin } from 'antd';
import axios from 'axios';
import { API_BASE_URL } from './config';
import MainLayout from './layouts/MainLayout';
import BacktestDashboard from './components/BacktestDashboard';
import HistoryPanel from './components/HistoryPanel';
import StrategyAnalysis from './components/StrategyAnalysis';
import StrategyEditor from './components/StrategyEditor';
import ConceptDashboard from './components/ConceptDashboard';
import FundDashboard from './components/FundDashboard';
import DerivativesDashboard from './components/DerivativesDashboard';
import CommoditiesDashboard from './components/CommoditiesDashboard';
import StockDashboard from './components/StockDashboard';
import MarketReplay from './components/tools/MarketReplay';
import MacroCalendar from './components/tools/MacroCalendar';
import SentimentRadar from './components/tools/SentimentRadar';
import RiskCenter from './components/tools/RiskCenter';
import './App.css';
import { LanguageProvider } from './contexts/LanguageContext';

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
            // --- Market Views ---
            case '9':
                return <StockDashboard />;
            case '6':
                return <FundDashboard />;
            case '7':
                return <DerivativesDashboard />;
            case '8':
                return <CommoditiesDashboard />;

            // --- Quant Tools ---
            case '1':
                return (
                    <BacktestDashboard 
                        symbols={symbols} 
                        strategyConfig={strategyConfig}
                        onStrategyApplied={handleStrategyApplied}
                    />
                );
            case '3':
                return <StrategyAnalysis onApplyStrategy={handleApplyStrategy} />;
            case '4':
                return <StrategyEditor />;
            case '2':
                return <HistoryPanel symbols={symbols} />;

            // --- Advanced Tools ---
            case '10':
                return <MarketReplay />;
            case '11':
                return <MacroCalendar />;
            case '12':
                return <SentimentRadar />;
            case '13':
                return <RiskCenter />;

            // --- Wealth ---
            case '5':
                return <ConceptDashboard />;

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
        <LanguageProvider>
            <ConfigProvider
                theme={{
                    algorithm: theme.darkAlgorithm,
                    token: {
                        colorPrimary: '#1890ff',
                        colorBgContainer: '#141414',
                    },
                }}
            >
                <AntdApp>
                    <InnerApp />
                </AntdApp>
            </ConfigProvider>
        </LanguageProvider>
    );
};

export default App;
