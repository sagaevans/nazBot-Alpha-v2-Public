import React, { useEffect, useRef, useState } from 'react'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine
} from 'recharts'
import { ChartData } from '../types'

interface Props {
  chartData: ChartData
}

type Mode = 'saldo' | 'growth'

const CustomTooltip = ({ active, payload, label, mode }: any) => {
  if (!active || !payload?.length) return null
  const v = payload[0].value
  return (
    <div
      style={{
        background: '#0d1b2e',
        border: '1px solid #1e3a5f',
        borderRadius: '8px',
        padding: '10px 14px',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '12px',
        color: '#c9daea',
      }}
    >
      <div style={{ color: '#6b8fa8', marginBottom: '4px', fontSize: '11px' }}>{label}</div>
      <div style={{ fontWeight: 700, color: '#f8fafc' }}>
        {mode === 'saldo' ? `$${v.toFixed(2)}` : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`}
      </div>
    </div>
  )
}

export function GrowthChart({ chartData }: Props) {
  const [mode, setMode] = useState<Mode>('saldo')

  const data = chartData.labels.map((label, i) => ({
    label,
    saldo:  chartData.saldo[i]  ?? 0,
    growth: chartData.growth[i] ?? 0,
  }))

  const color     = mode === 'saldo' ? '#2563eb' : '#10b981'
  const fillColor = mode === 'saldo' ? 'rgba(37,99,235,0.15)' : 'rgba(16,185,129,0.15)'
  const dataKey   = mode

  return (
    <div
      className="rounded-xl overflow-hidden fade-up"
      style={{ border: '1px solid #1e3a5f' }}
    >
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ background: '#112035', borderBottom: '1px solid #1e3a5f' }}
      >
        <h3 style={{ fontWeight: 700, color: '#60a5fa', fontSize: '13px' }}>
          📈 Wallet Growth Visualization
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(['saldo', 'growth'] as Mode[]).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                fontSize: '11px',
                fontWeight: 700,
                padding: '3px 12px',
                borderRadius: '6px',
                border: `1px solid ${mode === m ? (m === 'saldo' ? '#2563eb' : '#10b981') : '#1e3a5f'}`,
                background: mode === m ? (m === 'saldo' ? '#1e3a5f' : '#0f2820') : '#0a1628',
                color: mode === m ? (m === 'saldo' ? '#60a5fa' : '#10b981') : '#6b8fa8',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {m === 'saldo' ? '💰 Saldo' : '📊 Growth %'}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: '20px', height: '280px' }}>
        {data.length === 0 ? (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#6b8fa8',
              fontStyle: 'italic',
              fontSize: '13px',
            }}
          >
            Chart will populate as trades close...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" vertical={false} />
              <XAxis
                dataKey="label"
                stroke="#1e3a5f"
                tick={{ fill: '#6b8fa8', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#1e3a5f"
                tick={{ fill: '#6b8fa8', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => mode === 'saldo' ? `$${v}` : `${v}%`}
                width={60}
              />
              {mode === 'growth' && <ReferenceLine y={0} stroke="#475569" strokeDasharray="4 2" />}
              <Tooltip content={<CustomTooltip mode={mode} />} />
              <Area
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2.5}
                fill="url(#chartGrad)"
                dot={data.length < 30 ? { fill: color, r: 3, strokeWidth: 0 } : false}
                activeDot={{ r: 5, fill: color, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
