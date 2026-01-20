import React, { useState, useEffect } from 'react';
import { Card, Form, Select, Input, Switch, Button, Row, Col, DatePicker, Space, App, Modal, Tag, Tooltip } from 'antd';
import { PlayCircleOutlined, SettingOutlined, BulbOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import ResultView from './ResultView';

const { Option } = Select;
const { TextArea } = Input;

const BacktestDashboard = ({ symbols, strategyConfig, onStrategyApplied }) => {
    const { message } = App.useApp();
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);
    const [chartType, setChartType] = useState('line');
    const [form] = Form.useForm();
    const [autoOptimize, setAutoOptimize] = useState(true);
    const [currentConfig, setCurrentConfig] = useState(null);

    // Smart Strategy State
    const [nlInput, setNlInput] = useState('');
    const [generatedCode, setGeneratedCode] = useState('');
    const [isPreviewVisible, setIsPreviewVisible] = useState(false);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        if (symbols.length > 0) {
            // Only set default if form is not touched or empty (simplified check)
            // But actually we want to ensure default is set on load
            const currentSymbol = form.getFieldValue('symbol');
            if (!currentSymbol) {
                const defaultSymbol = symbols.find(s => s.code === 'SH0') || symbols[0];
                form.setFieldsValue({ 
                    symbol: defaultSymbol.code, 
                    contract_multiplier: defaultSymbol.multiplier 
                });
            }
        }
        
        // Handle incoming strategy config from props
        if (strategyConfig) {
            const config = strategyConfig;
            
            // Map config parameters to form fields
            const formValues = { ...form.getFieldsValue() };
            
            if (config.symbol) formValues.symbol = config.symbol;
            if (config.period) formValues.period = config.period;
            
            if (config.strategy_params) {
                Object.keys(config.strategy_params).forEach(key => {
                    formValues[key] = config.strategy_params[key];
                });
            }
            
            form.setFieldsValue(formValues);
            message.success('策略参数已加载');
            
            // Notify parent that strategy has been applied
            if (onStrategyApplied) {
                onStrategyApplied();
            }
        }
    }, [symbols, form, strategyConfig, onStrategyApplied]);

    const onSymbolChange = (value) => {
        const selected = symbols.find(s => s.code === value);
        if (selected) {
            form.setFieldsValue({ contract_multiplier: selected.multiplier });
        }
    };

    const handleGenerate = async () => {
        if (!nlInput.trim()) {
            message.warning("请输入策略描述");
            return;
        }
        setGenerating(true);
        try {
            const res = await axios.post(`${API_BASE_URL}/api/strategies/generate`, { text: nlInput });
            const { code, config } = res.data;
            setGeneratedCode(code);
            
            // Auto-fill form fields if applicable
            if (config.fast_period) form.setFieldsValue({ fast_period: config.fast_period });
            if (config.slow_period) form.setFieldsValue({ slow_period: config.slow_period });
            // Note: Our generated strategy handles stop loss internally via code, 
            // but we can update UI for visual reference if mapped
            
            setIsPreviewVisible(true);
            message.success("策略已生成，参数已自动填充");
        } catch (err) {
            console.error(err);
            message.error("生成失败: " + (err.response?.data?.detail || err.message));
        } finally {
            setGenerating(false);
        }
    };

    const clearCustomStrategy = () => {
        setGeneratedCode('');
        setNlInput('');
        message.info("已清除自定义策略，恢复默认配置");
    };
  
    const onFinish = async (values) => {
      setLoading(true);
      setResults(null);
      try {
        const params = {
            fast_period: parseInt(values.fast_period),
            slow_period: parseInt(values.slow_period),
            atr_period: parseInt(values.atr_period),
            atr_multiplier: parseFloat(values.atr_multiplier),
            risk_per_trade: parseFloat(values.risk_per_trade),
            contract_multiplier: parseInt(values.contract_multiplier)
        };
  
        const payload = {
          symbol: values.symbol,
          period: values.period,
          strategy_params: params,
          strategy_code: generatedCode || undefined, // Use custom code if generated
          auto_optimize: autoOptimize,
          start_date: values.date_range ? values.date_range[0].format('YYYY-MM-DD') : null,
          end_date: values.date_range ? values.date_range[1].format('YYYY-MM-DD') : null,
          initial_cash: parseFloat(values.initial_cash)
        };
        
        const response = await axios.post(`${API_BASE_URL}/api/backtest`, payload);
        setResults(response.data);
        
        // Save current config for ResultView linkage
        setCurrentConfig({
            symbol: values.symbol,
            period: values.period,
            start_date: payload.start_date,
            end_date: payload.end_date
        });

        message.success('回测完成');
      } catch (error) {
        console.error(error);
        message.error('回测失败: ' + (error.response?.data?.detail || error.message));
      } finally {
        setLoading(false);
      }
    };

    return (
        <Row gutter={24} style={{ height: '100%' }}>
            <Col span={6} style={{ height: '100%' }}>
                <Card title="策略配置" bordered={false} className="pro-card" style={{ height: '100%', overflowY: 'auto' }}>
                    
                    {/* Smart Strategy Section */}
                    <Card type="inner" title={<span><BulbOutlined /> 白话策略配置</span>} style={{ marginBottom: 16 }} size="small">
                        <TextArea 
                            placeholder="例如：当5日均线上穿20日均线时买入，跌破时卖出；止损5%" 
                            rows={3} 
                            value={nlInput}
                            onChange={e => setNlInput(e.target.value)}
                            style={{ marginBottom: 8 }}
                        />
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <Button type="primary" size="small" onClick={handleGenerate} loading={generating}>
                                生成策略
                            </Button>
                            {generatedCode && (
                                <Space>
                                    <Button size="small" icon={<EditOutlined />} onClick={() => setIsPreviewVisible(true)}>预览</Button>
                                    <Button size="small" danger icon={<DeleteOutlined />} onClick={clearCustomStrategy} />
                                </Space>
                            )}
                        </Space>
                        {generatedCode && (
                            <div style={{ marginTop: 8 }}>
                                <Tag color="green">已启用自定义策略</Tag>
                            </div>
                        )}
                    </Card>

                    <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{
                        period: 'daily',
                        fast_period: 10,
                        slow_period: 20,
                        atr_period: 14,
                        atr_multiplier: 2.0,
                        risk_per_trade: 0.02,
                        contract_multiplier: 30,
                        initial_cash: 1000000
                    }}>
                        <Form.Item name="symbol" label="交易品种" rules={[{ required: true }]}>
                            <Select 
                                onChange={onSymbolChange}
                                showSearch
                                placeholder="选择或搜索品种"
                                optionFilterProp="children"
                                filterOption={(input, option) =>
                                    option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                                }
                            >
                                {symbols.map(s => (
                                    <Option key={s.code} value={s.code}>{s.name}</Option>
                                ))}
                            </Select>
                        </Form.Item>
                        
                        <Form.Item label="初始本金" name="initial_cash" rules={[{ required: true }]}>
                            <Input type="number" step="10000" addonAfter="元" />
                        </Form.Item>

                        <Form.Item label="回测周期" name="period">
                            <Select>
                                <Option value="1">1分钟</Option>
                                <Option value="5">5分钟</Option>
                                <Option value="15">15分钟</Option>
                                <Option value="30">30分钟</Option>
                                <Option value="60">1小时</Option>
                                <Option value="240">4小时</Option>
                                <Option value="daily">日线</Option>
                                <Option value="weekly">周线</Option>
                            </Select>
                        </Form.Item>

                        <Form.Item label="时间范围" name="date_range">
                            <DatePicker.RangePicker style={{ width: '100%' }} />
                        </Form.Item>

                        <Row gutter={16}>
                            <Col span={12}>
                                <Form.Item name="fast_period" label="快线周期">
                                    <Input type="number" />
                                </Form.Item>
                            </Col>
                            <Col span={12}>
                                <Form.Item name="slow_period" label="慢线周期">
                                    <Input type="number" />
                                </Form.Item>
                            </Col>
                        </Row>

                        <Form.Item name="atr_multiplier" label="ATR止损倍数">
                            <Input type="number" step="0.1" />
                        </Form.Item>
                        <Form.Item name="risk_per_trade" label="单笔风险系数 (0.02=2%)">
                            <Input type="number" step="0.01" />
                        </Form.Item>
                        
                        <Form.Item name="contract_multiplier" label="合约乘数" hidden>
                            <Input type="number" />
                        </Form.Item>
                        <Form.Item name="atr_period" hidden><Input /></Form.Item>

                        <Form.Item label="自动优化">
                            <Space>
                                <Switch checked={autoOptimize} onChange={setAutoOptimize} />
                                <span style={{ color: '#999', fontSize: '12px' }}>若收益&lt;20%则自动尝试优化</span>
                            </Space>
                        </Form.Item>

                        <Button type="primary" htmlType="submit" loading={loading} block size="large" icon={<PlayCircleOutlined />}>
                            开始回测
                        </Button>
                    </Form>
                </Card>
            </Col>
            
            <Col span={18} style={{ height: '100%', overflowY: 'auto' }}>
                {results ? (
                    <ResultView 
                        results={results} 
                        chartType={chartType} 
                        setChartType={setChartType} 
                        config={currentConfig}
                    />
                ) : (
                    <Card bordered={false} className="pro-card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ textAlign: 'center', color: '#555' }}>
                            <div style={{ fontSize: '64px', marginBottom: '24px', opacity: 0.5 }}><SettingOutlined /></div>
                            <h2 style={{ color: '#ccc' }}>准备就绪</h2>
                            <p>请在左侧配置策略参数，点击“开始回测”查看结果</p>
                        </div>
                    </Card>
                )}
            </Col>

            <Modal 
                title="生成策略代码预览" 
                open={isPreviewVisible} 
                onOk={() => setIsPreviewVisible(false)} 
                onCancel={() => setIsPreviewVisible(false)}
                width={800}
                footer={[
                    <Button key="close" onClick={() => setIsPreviewVisible(false)}>
                        关闭
                    </Button>
                ]}
            >
                <Input.TextArea value={generatedCode} autoSize={{ minRows: 10, maxRows: 20 }} readOnly style={{ fontFamily: 'monospace' }} />
            </Modal>
        </Row>
    );
};

export default BacktestDashboard;
