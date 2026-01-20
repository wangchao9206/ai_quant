import React, { useState, useEffect } from 'react';
import { Card, Button, App } from 'antd';
import Editor from '@monaco-editor/react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const StrategyEditor = () => {
    const { message } = App.useApp();
    const [strategyCode, setStrategyCode] = useState('');
    const [savingCode, setSavingCode] = useState(false);

    useEffect(() => {
        fetchStrategyCode();
    }, []);

    const fetchStrategyCode = () => {
        axios.get(`${API_BASE_URL}/api/strategy/code`)
          .then(res => {
              setStrategyCode(res.data.code);
          })
          .catch(err => {
              message.error('获取策略代码失败');
          });
    };
  
    const saveStrategyCode = () => {
        setSavingCode(true);
        axios.post(`${API_BASE_URL}/api/strategy/code`, { code: strategyCode })
          .then(res => {
              message.success('策略代码保存成功');
          })
          .catch(err => {
              message.error('保存失败: ' + (err.response?.data?.detail || err.message));
          })
          .finally(() => {
              setSavingCode(false);
          });
    };

    return (
        <Card 
            title="编辑策略逻辑 (server/core/strategy.py)" 
            bordered={false}
            className="pro-card"
            extra={
                <Button type="primary" onClick={saveStrategyCode} loading={savingCode}>
                    保存并生效
                </Button>
            }
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, padding: 0, minHeight: 0 }}
        >
            <div style={{ height: '100%' }}>
                <Editor
                    height="100%"
                    defaultLanguage="python"
                    value={strategyCode}
                    onChange={(value) => setStrategyCode(value)}
                    theme="vs-dark"
                    options={{
                        minimap: { enabled: false },
                        fontSize: 14,
                        scrollBeyondLastLine: false,
                        fontFamily: '"JetBrains Mono", monospace'
                    }}
                />
            </div>
        </Card>
    );
};

export default StrategyEditor;
