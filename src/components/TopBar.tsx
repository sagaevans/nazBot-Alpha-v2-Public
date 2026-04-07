import React from 'react'

interface Props {
  botStatus: 'ON' | 'OFF'
  walletBalance: number
  onToggle: () => void
  onPanic: () => void
}

export function TopBar({ botStatus, walletBalance, onToggle, onPanic }: Props) {
  const isOn = botStatus === 'ON'

  return (
    <div
      style={{
        background: '#0d1b2e',
        borderBottom: '1px solid #1e3a5f',
        padding: '14px 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            background: 'linear-gradient(135deg,#1d4ed8,#2563eb)',
            padding: '9px',
            borderRadius: '10px',
            boxShadow: '0 4px 14px rgba(37,99,235,0.4)',
          }}
        >
          <svg width="20" height="20" fill="none" stroke="#fff" strokeWidth="2"
               strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
            <path d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1
              style={{
                fontSize: '16px',
                fontWeight: 800,
                color: '#f8fafc',
                letterSpacing: '-0.02em',
              }}
            >
              nazBot Sniper
            </h1>
            <span
              style={{
                background: '#1e3a5f',
                color: '#60a5fa',
                fontSize: '10px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '20px',
                letterSpacing: '0.06em',
              }}
            >
              BETA v4.0
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            {/* Status dot */}
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: isOn ? '#10b981' : '#4b5563',
                boxShadow: isOn ? '0 0 8px #10b981' : 'none',
                animation: isOn ? 'pulse-dot 1.4s ease infinite' : 'none',
              }}
            />
            <span style={{ fontSize: '11px', color: '#6b8fa8' }}>
              {isOn ? '⚡ Bot Running — Scanning Market' : '⏸ Bot Standby — Press START'}
            </span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ textAlign: 'right', marginRight: '4px' }}>
          <div style={{ fontSize: '10px', color: '#6b8fa8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Live Balance
          </div>
          <div
            className="font-mono-jet"
            style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}
          >
            ${walletBalance.toFixed(2)}
          </div>
        </div>

        <button
          onClick={onToggle}
          style={{
            fontWeight: 700,
            fontSize: '13px',
            padding: '9px 22px',
            borderRadius: '8px',
            border: isOn ? '1px solid #475569' : 'none',
            cursor: 'pointer',
            transition: 'all 0.2s',
            background: isOn
              ? 'linear-gradient(135deg, #1e293b, #334155)'
              : 'linear-gradient(135deg, #059669, #10b981)',
            color: isOn ? '#f43f5e' : '#fff',
            boxShadow: isOn ? 'none' : '0 4px 14px rgba(16,185,129,0.35)',
          }}
        >
          {isOn ? 'STOP BOT' : 'START BOT'}
        </button>

        <button
          onClick={onPanic}
          style={{
            fontWeight: 700,
            fontSize: '13px',
            padding: '9px 22px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            background: 'linear-gradient(135deg, #9f1239, #f43f5e)',
            color: '#fff',
            boxShadow: '0 4px 14px rgba(244,63,94,0.35)',
            transition: 'all 0.2s',
          }}
        >
          ☠️ PANIC CLOSE
        </button>
      </div>
    </div>
  )
}
