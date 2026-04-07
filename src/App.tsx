import React, { useState, useEffect, useCallback } from 'react'
import { TopBar } from './components/TopBar'
import { StatCard } from './components/StatCard'
import { PositionTable } from './components/PositionTable'
import { LedgerTable } from './components/LedgerTable'
import { GrowthChart } from './components/GrowthChart'
import { AlertModal } from './components/AlertModal'
import { DashboardData, ChartData, LedgerRow } from './types'
import { fmtMoney, fmtPct, DEMO_LEDGER } from './utils/format'

// ── Demo / fallback state ───────────────────────────────────────────────────
const DEMO_CHART: ChartData = {
  labels:  DEMO_LEDGER.map(r => r.time),
  saldo:   DEMO_LEDGER.map(r => parseFloat(r.saldo)),
  growth:  DEMO_LEDGER.map(r => parseFloat(r.growth.replace(/[+%]/g, ''))),
  tot_pnl: DEMO_LEDGER.map(r => parseFloat(r.tot_pnl.replace(/[+$]/g, ''))),
}

const INITIAL_STATE: DashboardData = {
  status:           'success',
  bot_status:       'OFF',
  wallet_balance:   5027.50,
  equity:           5027.50,
  net_profit:       '+27.50',
  net_roe:          '+550.00%',
  total_unrealized: 0,
  total_active_roe: 0,
  total_margin:     0,
  gold_positions:   [],
  vip_positions:    [],
  alt_positions:    [],
  ledger:           DEMO_LEDGER as LedgerRow[],
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function ColorValue({ val, isMoney = false }: { val: string | number; isMoney?: boolean }) {
  const fmt = isMoney ? fmtMoney(val) : fmtPct(val)
  const color = fmt.cls.includes('emerald') ? '#10b981'
              : fmt.cls.includes('rose')    ? '#f43f5e'
              : '#94a3b8'
  return <span style={{ color, fontFamily: 'JetBrains Mono, monospace' }}>{fmt.text}</span>
}

// ── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [data,        setData]        = useState<DashboardData>(INITIAL_STATE)
  const [chartData,   setChartData]   = useState<ChartData>(DEMO_CHART)
  const [showPanic,   setShowPanic]   = useState(false)
  const [toast,       setToast]       = useState<{ msg: string; type: 'ok' | 'err' } | null>(null)
  const [apiOk,       setApiOk]       = useState(false)   // true when Flask API is reachable

  // ── Data Fetching ─────────────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/data', { signal: AbortSignal.timeout(3000) })
      if (!res.ok) throw new Error('non-200')
      const json = await res.json()
      if (json.status === 'success') {
        setData(json)
        setApiOk(true)
      }
    } catch {
      // Flask not reachable — keep demo data (Blink preview mode)
    }
  }, [])

  const fetchChart = useCallback(async () => {
    try {
      const res = await fetch('/api/ledger_chart', { signal: AbortSignal.timeout(3000) })
      if (!res.ok) throw new Error('non-200')
      const json = await res.json()
      if (json.status === 'success') {
        setChartData(json.chart)
      }
    } catch {
      // keep demo chart
    }
  }, [])

  useEffect(() => {
    fetchData()
    fetchChart()
    const t1 = setInterval(fetchData, 2000)
    const t2 = setInterval(fetchChart, 10000)
    return () => { clearInterval(t1); clearInterval(t2) }
  }, [fetchData, fetchChart])

  // ── Toast Helper ──────────────────────────────────────────────────────────
  const showToast = (msg: string, type: 'ok' | 'err') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleToggle = async () => {
    if (!apiOk) {
      // Simulate local toggle in demo mode
      setData(d => ({ ...d, bot_status: d.bot_status === 'ON' ? 'OFF' : 'ON' }))
      return
    }
    try {
      const res  = await fetch('/api/toggle', { method: 'POST' })
      const json = await res.json()
      if (json.status === 'success') {
        setData(d => ({ ...d, bot_status: json.bot_status }))
      }
    } catch {
      showToast('Failed to toggle bot status.', 'err')
    }
  }

  const handlePanicConfirm = async () => {
    setShowPanic(false)
    if (!apiOk) {
      showToast('Demo mode: Panic close simulated (Flask not connected).', 'ok')
      return
    }
    try {
      const res  = await fetch('/api/close_all', { method: 'POST' })
      const json = await res.json()
      if (json.status === 'success') {
        showToast(json.message, 'ok')
        fetchData()
      } else {
        showToast(json.message, 'err')
      }
    } catch {
      showToast('Failed to call close_all API.', 'err')
    }
  }

  // ── KPI values ────────────────────────────────────────────────────────────
  const floatingColor = data.total_unrealized >= 0 ? '#10b981' : '#f43f5e'
  const floatingSign  = data.total_unrealized >= 0 ? '+' : ''
  const netPnlFmt     = fmtMoney(data.net_profit)
  const netRoeFmt     = fmtPct(data.net_roe)

  return (
    <div style={{ minHeight: '100vh', background: '#060d1a' }}>
      {/* TOP BAR */}
      <TopBar
        botStatus={data.bot_status}
        walletBalance={data.wallet_balance}
        onToggle={handleToggle}
        onPanic={() => setShowPanic(true)}
      />

      {/* DEMO BANNER */}
      {!apiOk && (
        <div
          style={{
            background: 'rgba(37,99,235,0.12)',
            borderBottom: '1px solid rgba(37,99,235,0.25)',
            padding: '8px 28px',
            fontSize: '12px',
            color: '#60a5fa',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span style={{ fontWeight: 700 }}>ℹ️ Preview Mode:</span>
          Demo data shown. Deploy on Replit/server and run{' '}
          <code
            style={{
              background: '#0d1b2e',
              padding: '1px 6px',
              borderRadius: '4px',
              fontFamily: 'JetBrains Mono, monospace',
              color: '#f8fafc',
            }}
          >
            python main.py
          </code>{' '}
          to connect live Binance data.
        </div>
      )}

      {/* MAIN CONTENT */}
      <div style={{ padding: '24px 28px', maxWidth: '1600px', margin: '0 auto' }}>

        {/* KPI CARDS */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '24px',
          }}
        >
          <StatCard
            label="💰 Wallet Balance (USDT)"
            value={`$${data.wallet_balance.toFixed(2)}`}
            sub="Available margin"
          />
          <StatCard
            label="📈 Total Equity"
            value={`$${data.equity.toFixed(2)}`}
            sub="Wallet + Floating"
          />
          <StatCard
            label="💹 Floating PNL / ROE"
            value={
              <span style={{ fontSize: '18px' }}>
                <span style={{ color: floatingColor }}>
                  {floatingSign}${Math.abs(data.total_unrealized).toFixed(2)}
                </span>
                <span style={{ fontSize: '14px', marginLeft: '6px', color: '#6b8fa8' }}>
                  ({floatingSign}{Math.abs(data.total_active_roe).toFixed(2)}%)
                </span>
              </span>
            }
            sub="Unrealized positions"
          />
          <StatCard
            label="🏆 Net Profit (Ledger)"
            value={
              <span style={{ fontSize: '18px' }}>
                <span style={{ color: netPnlFmt.cls.includes('emerald') ? '#10b981' : '#f43f5e' }}>
                  {netPnlFmt.text}
                </span>
                <span style={{ fontSize: '14px', marginLeft: '6px', color: '#6b8fa8' }}>
                  ({netRoeFmt.text})
                </span>
              </span>
            }
            sub="All closed trades"
          />
          <StatCard
            label="📊 Total Active Margin"
            value={`$${(data.total_margin ?? 0).toFixed(2)}`}
            sub="Across all positions"
          />
        </div>

        {/* POSITION TABLES */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* GOLD */}
          <PositionTable
            title="Radar Emas — PAXG Only"
            emoji="🏅"
            color="#f59e0b"
            positions={data.gold_positions}
            max={1}
            emptyMsg="⛏️ No Gold position active — scanning PAXG..."
            badgeStyle={{
              background: '#1c2a10',
              color: '#84cc16',
              border: '1px solid #365314',
            }}
          />

          {/* VIP */}
          <PositionTable
            title="VIP Positions — BTC ETH SOL BNB ADA DOT XRP ALICE"
            emoji="👑"
            color="#a78bfa"
            positions={data.vip_positions}
            max={8}
            emptyMsg="🎯 No VIP positions — waiting for pinbar signal..."
            badgeStyle={{
              background: '#1e1030',
              color: '#a78bfa',
              border: '1px solid #4c1d95',
            }}
          />

          {/* ALT */}
          <PositionTable
            title="Altcoin Positions — 4 Aggressive (5m) + 4 Safe (15m)"
            emoji="🚀"
            color="#f472b6"
            positions={data.alt_positions}
            max={8}
            emptyMsg="🎯 No Altcoin positions — parallel scanner active..."
            badgeStyle={{
              background: '#2d1040',
              color: '#f472b6',
              border: '1px solid #831843',
            }}
          />

          {/* CHART */}
          <GrowthChart chartData={chartData} />

          {/* LEDGER TABLE */}
          <LedgerTable rows={data.ledger} />

          {/* FOOTER */}
          <div
            style={{
              textAlign: 'center',
              padding: '16px 0',
              color: '#4b6a84',
              fontSize: '11px',
              lineHeight: 1.9,
              borderTop: '1px solid #1e3a5f',
            }}
          >
            <strong style={{ color: '#6b8fa8' }}>nazBot Sniper BETA v4.0</strong>
            {' '}— 50× Leverage · $5 Base Margin · 100% ROE TP · -150% ROE SL (Short only)
            <br />
            5-Layer Confluence: EMA 200 (Trend) · MA 99 + BB (Dynamic Walls) · Static S/R · Volume Spike · Pinbar PA
            <br />
            Long: No SL — 3-Stage DCA · Short: Stop Market -150% ROE · TP: Instant Limit Order
          </div>
        </div>
      </div>

      {/* PANIC MODAL */}
      <AlertModal
        open={showPanic}
        title="☠️ PANIC CLOSE ALL?"
        message="Bot akan dimatikan. Semua order LIMIT/SL dibatalkan. Semua posisi ditutup MARKET."
        onConfirm={handlePanicConfirm}
        onCancel={() => setShowPanic(false)}
      />

      {/* TOAST */}
      {toast && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: toast.type === 'ok' ? '#0f2820' : '#1a0a10',
            border: `1px solid ${toast.type === 'ok' ? '#10b981' : '#f43f5e'}`,
            color: toast.type === 'ok' ? '#10b981' : '#f43f5e',
            padding: '12px 20px',
            borderRadius: '10px',
            fontSize: '13px',
            fontWeight: 600,
            boxShadow: `0 8px 24px ${toast.type === 'ok' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}`,
            zIndex: 9999,
            maxWidth: '360px',
          }}
        >
          {toast.type === 'ok' ? '✅ ' : '❌ '}{toast.msg}
        </div>
      )}
    </div>
  )
}
