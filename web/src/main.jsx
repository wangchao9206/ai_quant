import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './i18n';
import App from './App.jsx'
import 'antd/dist/reset.css'; // 引入 Antd 重置样式

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Suspense fallback={<div style={{ color: '#fff', padding: 20 }}>Loading...</div>}>
      <App />
    </Suspense>
  </StrictMode>,
)
