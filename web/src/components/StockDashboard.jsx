import React, { useState, useEffect, useRef } from 'react';
import { Row, Col, Statistic, Table, Tag, Input, Button, Progress, List, Badge, message, Spin, Radio } from 'antd';
import { 
    SearchOutlined, 
    StockOutlined, 
    RiseOutlined, 
    FallOutlined,
    HeatMapOutlined,
    AlertOutlined,
    ThunderboltOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import '../styles/design-tokens.css';
import { useLanguage } from '../contexts/LanguageContext';

const StockDashboard = () => {
    const { t } = useLanguage();
    const [symbol, setSymbol] = useState('600519');
    const [period, setPeriod] = useState('day');
    const [searchText, setSearchText] = useState('600519');
    const [loading, setLoading] = useState(false);
    const [tdxReady, setTdxReady] = useState(false);
    
    const [marketIndices, setMarketIndices] = useState([]);
    const [stockQuote, setStockQuote] = useState(null);
    const [orderBook, setOrderBook] = useState({ asks: [], bids: [] });
    const [sectorData, setSectorData] = useState([]);
    const [klineData, setKlineData] = useState({ times: [], values: [] });
    const [watchlist, setWatchlist] = useState(['600519', '000001']);
    const [watchQuotes, setWatchQuotes] = useState([]);
    const [watchAdd, setWatchAdd] = useState('');

    const realtimeLockRef = useRef(false);
    const lastKlineAtRef = useRef(0);

    const normalizeCode = (value) => {
        const raw = String(value || '').trim();
        const digits = raw.replace(/\D/g, '');
        if (!digits) return raw;
        if (digits.length <= 6) return digits.padStart(6, '0');
        return digits.slice(-6);
    };

    const pick = (obj, keys) => {
        for (const k of keys) {
            if (obj && obj[k] != null) return obj[k];
        }
        return undefined;
    };

    const toNumber = (v) => {
        if (v == null) return null;
        const n = Number(String(v).replace('%', '').trim());
        return Number.isFinite(n) ? n : null;
    };

    const mapTdxQuoteToUi = (data, code) => {
        const root = data && data.data != null ? data.data : data;
        const rec = Array.isArray(root) ? root[0] : root;
        if (!rec || typeof rec !== 'object') return null;

        const name = pick(rec, ['name', '名称', 'stock_name', '证券名称']) || code;
        const price = toNumber(pick(rec, ['price', 'last', '最新价', '最新', 'close', '现价'])) ?? 0;
        const open = toNumber(pick(rec, ['open', '今开', '开盘'])) ?? price;
        const high = toNumber(pick(rec, ['high', '最高'])) ?? price;
        const low = toNumber(pick(rec, ['low', '最低'])) ?? price;
        const changePct = toNumber(pick(rec, ['change', 'change_pct', '涨跌幅', '涨幅', 'pct'])) ?? 0;
        const changeAmt = toNumber(pick(rec, ['changeAmt', 'change_amt', '涨跌额', '涨跌', 'diff'])) ?? 0;
        const vol = pick(rec, ['vol', 'volume', '成交量']) ?? '-';
        const amt = pick(rec, ['amt', 'amount', '成交额']) ?? '-';
        const pe = toNumber(pick(rec, ['pe', '市盈率-动态'])) ?? 0;
        const pb = toNumber(pick(rec, ['pb', '市净率'])) ?? 0;

        const uiCode = pick(rec, ['code', '证券代码', 'stock_code']) || code;

        return {
            name: String(name),
            code: String(uiCode),
            price,
            change: changePct,
            changeAmt,
            open,
            high,
            low,
            vol: String(vol),
            amt: String(amt),
            pe,
            pb,
        };
    };

    const mapTdxOrderbookToUi = (data) => {
        const root = data && data.data != null ? data.data : data;
        const rec = Array.isArray(root) ? root[0] : root;
        if (!rec || typeof rec !== 'object') return null;

        const rawAsks = pick(rec, ['asks', 'sell', '卖盘', '卖五档']);
        const rawBids = pick(rec, ['bids', 'buy', '买盘', '买五档']);

        const mapSide = (side) => {
            if (!side) return [];
            if (Array.isArray(side)) {
                if (side.length > 0 && typeof side[0] === 'object' && side[0] != null) {
                    return side
                        .map((x) => {
                            const p = toNumber(pick(x, ['p', 'price', '价', 'Price', 'P']));
                            const v = toNumber(pick(x, ['v', 'vol', 'volume', '量', 'Volume', 'V']));
                            if (p == null) return null;
                            return { p, v: v == null ? 0 : Math.trunc(v) };
                        })
                        .filter(Boolean);
                }

                if (side.length > 0 && Array.isArray(side[0])) {
                    return side
                        .map((x) => {
                            const p = toNumber(x[0]);
                            const v = toNumber(x[1]);
                            if (p == null) return null;
                            return { p, v: v == null ? 0 : Math.trunc(v) };
                        })
                        .filter(Boolean);
                }
            }
            return [];
        };

        const asks = mapSide(rawAsks);
        const bids = mapSide(rawBids);
        return asks.length || bids.length ? { asks, bids } : null;
    };

    const mapTdxKlineToUi = (data) => {
        const root = data && data.data != null ? data.data : data;
        const rows = Array.isArray(root) ? root : Array.isArray(root?.list) ? root.list : [];
        if (!rows.length) return null;

        const times = [];
        const values = [];
        for (const r of rows) {
            if (!r) continue;
            const t = pick(r, ['datetime', 'time', 'date', 'datetime', '日期', '时间']);
            const o = toNumber(pick(r, ['open', '开盘']));
            const c = toNumber(pick(r, ['close', '收盘']));
            const l = toNumber(pick(r, ['low', '最低']));
            const h = toNumber(pick(r, ['high', '最高']));
            if (t == null || o == null || c == null || l == null || h == null) continue;
            times.push(String(t));
            values.push([o, c, l, h]);
        }
        return times.length ? { times, values } : null;
    };

    const fetchFromTdx = async (code, periodArg = 'day') => {
        const [quoteRes, klineRes] = await Promise.all([
            axios.get(`${API_BASE_URL}/api/tdx/quote`, { params: { code } }),
            axios.get(`${API_BASE_URL}/api/tdx/kline`, { params: { code, type: periodArg } }),
        ]);

        const quote = mapTdxQuoteToUi(quoteRes.data, code);
        const orderBook = mapTdxOrderbookToUi(quoteRes.data) || { asks: [], bids: [] };
        const kline = mapTdxKlineToUi(klineRes.data) || { times: [], values: [] };

        if (!quote) {
            throw new Error('invalid quote');
        }

        return { quote, orderBook, kline };
    };

    const fetchQuoteOnlyFromTdx = async (code) => {
        const quoteRes = await axios.get(`${API_BASE_URL}/api/tdx/quote`, { params: { code } });
        const quote = mapTdxQuoteToUi(quoteRes.data, code);
        const orderBook = mapTdxOrderbookToUi(quoteRes.data) || { asks: [], bids: [] };
        if (!quote) throw new Error('invalid quote');
        return { quote, orderBook };
    };

    const fetchKlineOnlyFromTdx = async (code, periodArg = 'day') => {
        const klineRes = await axios.get(`${API_BASE_URL}/api/tdx/kline`, { params: { code, type: periodArg } });
        return mapTdxKlineToUi(klineRes.data) || { times: [], values: [] };
    };

    const fetchBatchQuotesFromTdx = async (codes) => {
        const clean = (codes || []).map(normalizeCode).filter((c) => /^\d{6}$/.test(c));
        if (!clean.length) return [];

        const tryParse = (payload) => {
            const root = payload && payload.data != null ? payload.data : payload;
            const rows = Array.isArray(root) ? root : Array.isArray(root?.list) ? root.list : [];
            const mapped = rows
                .map((r) => {
                    const c = normalizeCode(pick(r || {}, ['code', '证券代码', 'stock_code']) || '');
                    const ui = mapTdxQuoteToUi(r, c);
                    return ui;
                })
                .filter(Boolean);
            return mapped;
        };

        try {
            const res = await axios.get(`${API_BASE_URL}/api/tdx/batch-quote`, { params: { codes: clean.join(',') } });
            const parsed = tryParse(res.data);
            if (parsed.length) return parsed;
        } catch {
        }

        try {
            const res = await axios.get(`${API_BASE_URL}/api/tdx/batch-quote`, { params: { code: clean } });
            const parsed = tryParse(res.data);
            if (parsed.length) return parsed;
        } catch {
        }

        const rows = [];
        for (const c of clean.slice(0, 12)) {
            try {
                const res = await axios.get(`${API_BASE_URL}/api/tdx/quote`, { params: { code: c } });
                const ui = mapTdxQuoteToUi(res.data, c);
                if (ui) rows.push(ui);
            } catch {
            }
        }
        return rows;
    };

    const refreshWatchlist = async () => {
        try {
            const quotes = await fetchBatchQuotesFromTdx(watchlist);
            if (quotes.length) {
                const byCode = new Map(quotes.map((q) => [normalizeCode(q.code), q]));
                const ordered = watchlist
                    .map((c) => byCode.get(normalizeCode(c)))
                    .filter(Boolean);
                setWatchQuotes(ordered);
            }
        } catch {
        }
    };

    const fetchTdxHealth = async () => {
        try {
            await axios.get(`${API_BASE_URL}/api/tdx/health`, { timeout: 1500 });
            setTdxReady(true);
            return true;
        } catch {
            setTdxReady(false);
            return false;
        }
    };

    useEffect(() => {
        setSearchText(symbol);
    }, [symbol]);

    useEffect(() => {
        (async () => {
            const healthy = await fetchTdxHealth();
            fetchAllData(healthy);
        })();
    }, [symbol, period]);

    useEffect(() => {
        const intervalId = window.setInterval(async () => {
            if (realtimeLockRef.current) return;
            realtimeLockRef.current = true;
            try {
                const code = normalizeCode(symbol);

                try {
                    const [indicesRes, sectorsRes] = await Promise.all([
                        axios.get(`${API_BASE_URL}/api/market/indices`),
                        axios.get(`${API_BASE_URL}/api/market/sectors`),
                    ]);
                    setMarketIndices(indicesRes.data);
                    setSectorData(sectorsRes.data);
                } catch {
                }

                let quoteFetched = false;
                if (tdxReady) {
                    try {
                        const { quote, orderBook } = await fetchQuoteOnlyFromTdx(code);
                        setStockQuote(quote);
                        setOrderBook(orderBook);
                        setTdxReady(true);
                        quoteFetched = true;
                    } catch {
                        setTdxReady(false);
                    }
                } else {
                    // Try to recover TDX occasionally (approx every 15s)
                    // Removed random check for deterministic behavior
                    if (Date.now() % 15000 < 3000) {
                        fetchTdxHealth();
                    }
                }

                if (!quoteFetched) {
                    try {
                        const [quoteRes, orderBookRes] = await Promise.all([
                            axios.get(`${API_BASE_URL}/api/stock/quote`, { params: { symbol: code } }),
                            axios.get(`${API_BASE_URL}/api/stock/orderbook`, { params: { symbol: code } }),
                        ]);
                        setStockQuote(quoteRes.data);
                        setOrderBook(orderBookRes.data);
                    } catch {
                    }
                }

                const now = Date.now();
                if (now - lastKlineAtRef.current >= 20000) {
                    lastKlineAtRef.current = now;
                    if (tdxReady) {
                        try {
                            const kline = await fetchKlineOnlyFromTdx(code, period);
                            setKlineData(kline);
                        } catch {
                            // If kline fails, we might not want to kill tdxReady immediately unless strict
                        }
                    }
                }

                if (tdxReady) {
                    refreshWatchlist();
                }
            } finally {
                realtimeLockRef.current = false;
            }
        }, 3000);

        return () => window.clearInterval(intervalId);
    }, [symbol, watchlist, tdxReady, period]);

    const fetchAllData = async (isTdxAvailable = false) => {
        setLoading(true);
        try {
            // 并行请求所有数据
            const code = normalizeCode(symbol);
            const [indicesRes, sectorsRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/market/indices`),
                axios.get(`${API_BASE_URL}/api/market/sectors`),
            ]);

            setMarketIndices(indicesRes.data);
            setSectorData(sectorsRes.data);

            let tdxSuccess = false;
            if (isTdxAvailable) {
                try {
                    const { quote, orderBook, kline } = await fetchFromTdx(code, period);
                    setStockQuote(quote);
                    setOrderBook(orderBook);
                    setKlineData(kline);
                    setTdxReady(true);
                    tdxSuccess = true;
                } catch (e) {
                    setTdxReady(false);
                }
            }

            if (!tdxSuccess) {
                const [quoteRes, orderBookRes, intradayRes] = await Promise.all([
                    axios.get(`${API_BASE_URL}/api/stock/quote`, { params: { symbol: code } }),
                    axios.get(`${API_BASE_URL}/api/stock/orderbook`, { params: { symbol: code } }),
                    axios.get(`${API_BASE_URL}/api/stock/intraday`, { params: { symbol: code } })
                ]);
                setStockQuote(quoteRes.data);
                setOrderBook(orderBookRes.data);
                setKlineData(intradayRes.data);
            }

            if (tdxSuccess) {
                refreshWatchlist();
            }
        } catch (error) {
            console.error("Failed to fetch stock data:", error);
            message.error(t('stock.fetch_error'));
        } finally {
            setLoading(false);
        }
    };

    const addToWatchlist = () => {
        const code = normalizeCode(watchAdd);
        if (!/^\d{6}$/.test(code)) return;
        setWatchlist((prev) => (prev.includes(code) ? prev : [code, ...prev]).slice(0, 12));
        setWatchAdd('');
    };

    const handleSearch = async (value) => {
        const v = String(value || '').trim();
        if (!v) return;

        const code = normalizeCode(v);
        if (/^\d{6}$/.test(code) && v.replace(/\D/g, '').length > 0) {
            setSymbol(code);
            setSearchText(code);
            return;
        }

        try {
            const candidates = [
                { keyword: v },
                { q: v },
                { query: v },
                { key: v },
                { text: v },
                { name: v },
                { s: v },
            ];

            // First try our new dedicated search endpoint
            try {
                const searchRes = await axios.get(`${API_BASE_URL}/api/stock/search`, { params: { q: v } });
                if (searchRes.data && searchRes.data.length > 0) {
                     const hit = searchRes.data[0];
                     setSymbol(hit.code);
                     setSearchText(`${hit.code} ${hit.name}`);
                     return;
                }
            } catch (e) {
                console.warn("Stock search failed", e);
            }

            for (const params of candidates) {
                const res = await axios.get(`${API_BASE_URL}/api/tdx/search`, { params });
                const root = res.data && res.data.data != null ? res.data.data : res.data;
                const rows = Array.isArray(root) ? root : Array.isArray(root?.list) ? root.list : [];
                const first = rows[0];
                const hitCode = first && (first.code || first.代码 || first.stock_code || first.证券代码);
                const normalized = normalizeCode(hitCode || '');
                if (/^\d{6}$/.test(normalized)) {
                    setSymbol(normalized);
                    setSearchText(normalized);
                    return;
                }
            }
        } catch {
        }

        message.warning(t('stock.search_not_found') || '未找到匹配的股票/指数');
    };

    // --- Chart Options ---
    const klineOption = {
        backgroundColor: 'transparent',
        grid: { left: 50, right: 50, top: 30, bottom: 30 },
        xAxis: { 
            type: 'category', 
            data: klineData.times,
            axisLine: { lineStyle: { color: '#888' } }
        },
        yAxis: { 
            scale: true,
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
        },
        series: [{
            type: 'candlestick',
            data: klineData.values, // [Open, Close, Low, High]
            itemStyle: {
                color: 'var(--color-secondary)',
                color0: '#ff4d4f',
                borderColor: 'var(--color-secondary)',
                borderColor0: '#ff4d4f'
            }
        }]
    };

    if (loading && !stockQuote) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#fff' }}>
                <Spin tip={t('stock.loading')} />
            </div>
        );
    }

    // 防御性渲染，如果数据还没加载好
    if (!stockQuote) return null;

    return (
        <div style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ color: '#fff', display: 'flex', alignItems: 'center', gap: '12px', margin: 0 }}>
                    <StockOutlined style={{ color: 'var(--color-primary)' }} />
                    {t('stock.title')}
                </h1>
                <Input.Search 
                    placeholder={t('stock.enter_code')} 
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    onSearch={handleSearch}
                    style={{ width: 300 }}
                    allowClear
                />
            </div>

            <style>{`
                @keyframes aiqMarquee {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
            `}</style>

            <div className="glass-panel" style={{ marginBottom: '16px', padding: '10px 12px', overflow: 'hidden' }}>
                <div style={{ display: 'flex', width: '200%', animation: 'aiqMarquee 18s linear infinite' }}>
                    {[0, 1].map((dup) => (
                        <div key={dup} style={{ display: 'inline-flex', alignItems: 'center', gap: '18px', width: '50%', whiteSpace: 'nowrap' }}>
                            {marketIndices.map((idx) => (
                                <span key={`idx-${dup}-${idx.name}`} style={{ color: idx.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f', fontFamily: 'JetBrains Mono' }}>
                                    {idx.name} {Number(idx.value).toFixed(2)} {(Number(idx.change) > 0 ? '+' : '') + Number(idx.change).toFixed(2)}%
                                </span>
                            ))}
                            {watchQuotes.map((q) => (
                                <span key={`w-${dup}-${q.code}`} style={{ color: Number(q.change) >= 0 ? 'var(--color-secondary)' : '#ff4d4f', fontFamily: 'JetBrains Mono' }}>
                                    {normalizeCode(q.code)} {Number(q.price).toFixed(2)} {(Number(q.change) > 0 ? '+' : '') + Number(q.change).toFixed(2)}%
                                </span>
                            ))}
                        </div>
                    ))}
                </div>
            </div>


            {/* Market Indices */}
            <Row gutter={16} style={{ marginBottom: '24px' }}>
                {marketIndices.map((idx, i) => (
                    <Col span={6} key={i}>
                        <div className="glass-card" style={{ padding: '16px', textAlign: 'center' }}>
                            <div style={{ color: '#888', marginBottom: '4px' }}>{idx.name}</div>
                            <div style={{ 
                                fontSize: '20px', 
                                fontWeight: 'bold', 
                                color: idx.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f',
                                fontFamily: 'JetBrains Mono'
                            }}>
                                {idx.value.toFixed(2)}
                            </div>
                            <div style={{ fontSize: '12px', color: idx.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f' }}>
                                {idx.change > 0 ? '+' : ''}{idx.change}% <span style={{ color: '#666', marginLeft: '8px' }}>Vol: {idx.volume}</span>
                            </div>
                        </div>
                    </Col>
                ))}
            </Row>

            <Row gutter={24}>
                {/* Main Chart Area */}
                <Col span={14}>
                    <div className="glass-card" style={{ padding: '20px', height: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #303030', paddingBottom: '16px' }}>
                            <div>
                                <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#fff', marginRight: '12px' }}>{stockQuote.name}</span>
                                <span style={{ fontSize: '16px', color: '#888', fontFamily: 'JetBrains Mono' }}>{stockQuote.code}</span>
                                <Tag color="blue" style={{ marginLeft: '12px' }}>{t('stock.margin')}</Tag>
                                <Tag color={tdxReady ? "gold" : "default"}>{t('stock.connect')}</Tag>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <span style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--color-secondary)', fontFamily: 'JetBrains Mono' }}>
                                    {stockQuote.price.toFixed(2)}
                                </span>
                                <span style={{ marginLeft: '12px', color: 'var(--color-secondary)' }}>
                                    +{stockQuote.change}% (+{stockQuote.changeAmt})
                                </span>
                            </div>
                        </div>

                        <div style={{ marginBottom: 16, textAlign: 'right' }}>
                            <Radio.Group value={period} onChange={e => setPeriod(e.target.value)} buttonStyle="solid" size="small">
                                <Radio.Button value="day">日K</Radio.Button>
                                <Radio.Button value="week">周K</Radio.Button>
                                <Radio.Button value="month">月K</Radio.Button>
                                <Radio.Button value="1min">1分</Radio.Button>
                                <Radio.Button value="5min">5分</Radio.Button>
                                <Radio.Button value="15min">15分</Radio.Button>
                                <Radio.Button value="30min">30分</Radio.Button>
                                <Radio.Button value="60min">60分</Radio.Button>
                            </Radio.Group>
                        </div>
                        
                        <div style={{ height: '400px' }}>
                            <ReactECharts option={klineOption} style={{ height: '100%' }} />
                        </div>

                        <div style={{ display: 'flex', gap: '24px', marginTop: '16px', color: '#ccc', fontSize: '13px' }}>
                            <div>{t('stock.open')}: <span style={{ color: '#fff' }}>{stockQuote.open}</span></div>
                            <div>{t('stock.high')}: <span style={{ color: 'var(--color-secondary)' }}>{stockQuote.high}</span></div>
                            <div>{t('stock.low')}: <span style={{ color: '#ff4d4f' }}>{stockQuote.low}</span></div>
                            <div>{t('stock.volume')}: <span style={{ color: '#fff' }}>{stockQuote.vol}</span></div>
                            <div>{t('stock.turnover')}: <span style={{ color: '#fff' }}>{stockQuote.amt}</span></div>
                            <div>{t('stock.pe')}: <span style={{ color: '#fff' }}>{stockQuote.pe}</span></div>
                        </div>
                    </div>
                </Col>

                {/* Right Side: Order Book & Sector */}
                <Col span={10}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
                        {/* Order Book */}
                        <div className="glass-card" style={{ padding: '0', flex: 1 }}>
                            <div style={{ padding: '12px', borderBottom: '1px solid #303030', fontWeight: 'bold', color: '#fff' }}>
                                {t('stock.level2')}
                            </div>
                            <div style={{ padding: '12px', fontFamily: 'JetBrains Mono' }}>
                                {orderBook.asks.slice().reverse().map((ask, i) => (
                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ color: '#888' }}>{t('stock.ask')}{5-i}</span>
                                        <span style={{ color: '#ff4d4f' }}>{ask.p.toFixed(2)}</span>
                                        <span style={{ color: '#fff' }}>{ask.v}</span>
                                    </div>
                                ))}
                                <div style={{ borderTop: '1px dashed #444', margin: '8px 0' }} />
                                {orderBook.bids.map((bid, i) => (
                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ color: '#888' }}>{t('stock.bid')}{i+1}</span>
                                        <span style={{ color: 'var(--color-secondary)' }}>{bid.p.toFixed(2)}</span>
                                        <span style={{ color: '#fff' }}>{bid.v}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Sector Heatmap & AI Alert */}
                        <div className="glass-card" style={{ padding: '16px', flex: 1 }}>
                            <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ color: '#fff', fontWeight: 'bold' }}><HeatMapOutlined /> {t('stock.sector_heatmap')}</span>
                                <span style={{ color: '#888', fontSize: '12px' }}>{t('stock.fund_flow')}</span>
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                    <span style={{ color: '#fff', fontWeight: 'bold' }}><ThunderboltOutlined /> TDX</span>
                                    <span style={{ color: tdxReady ? '#faad14' : '#666', fontSize: '12px' }}>{tdxReady ? '在线' : '离线'}</span>
                                </div>
                                <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                                    <Input
                                        value={watchAdd}
                                        onChange={(e) => setWatchAdd(e.target.value)}
                                        placeholder="000001"
                                        size="small"
                                    />
                                    <Button size="small" onClick={addToWatchlist}>添加</Button>
                                    <Button size="small" onClick={refreshWatchlist}>刷新</Button>
                                </div>
                                <List
                                    size="small"
                                    dataSource={watchQuotes}
                                    locale={{ emptyText: null }}
                                    renderItem={(item) => (
                                        <List.Item
                                            style={{ padding: '6px 0', cursor: 'pointer' }}
                                            onClick={() => setSymbol(normalizeCode(item.code))}
                                        >
                                            <div style={{ display: 'flex', width: '100%', justifyContent: 'space-between', gap: '12px' }}>
                                                <span style={{ color: '#fff', fontFamily: 'JetBrains Mono' }}>{normalizeCode(item.code)}</span>
                                                <span style={{ color: '#fff', fontFamily: 'JetBrains Mono' }}>{Number(item.price).toFixed(2)}</span>
                                                <span style={{ color: Number(item.change) >= 0 ? 'var(--color-secondary)' : '#ff4d4f', fontFamily: 'JetBrains Mono' }}>
                                                    {(Number(item.change) > 0 ? '+' : '') + Number(item.change).toFixed(2)}%
                                                </span>
                                            </div>
                                        </List.Item>
                                    )}
                                />
                            </div>

                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {sectorData.map((s, i) => (
                                    <div key={i} style={{ 
                                        padding: '8px 12px', 
                                        background: s.change >= 0 ? 'rgba(0, 230, 118, 0.1)' : 'rgba(255, 77, 79, 0.1)',
                                        border: `1px solid ${s.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f'}`,
                                        borderRadius: '4px',
                                        flex: '1 0 30%'
                                    }}>
                                        <div style={{ color: '#fff', fontSize: '13px' }}>{s.name}</div>
                                        <div style={{ 
                                            color: s.change >= 0 ? 'var(--color-secondary)' : '#ff4d4f', 
                                            fontWeight: 'bold' 
                                        }}>
                                            {s.change > 0 ? '+' : ''}{s.change}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                            
                            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                                <div style={{ color: '#faad14', fontSize: '13px', display: 'flex', gap: '8px' }}>
                                    <AlertOutlined /> AI 异动提醒:
                                </div>
                                <div style={{ color: '#ccc', fontSize: '12px', marginTop: '4px' }}>
                                    14:30 酿酒板块出现大额主力净流入 (+5.2亿)
                                </div>
                            </div>
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export default StockDashboard;
