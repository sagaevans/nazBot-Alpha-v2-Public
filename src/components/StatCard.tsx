import React from 'react'

interface Props {
  label: string
  value: React.ReactNode
  sub?: string
  glow?: 'blue' | 'green' | 'red' | 'yellow'
}

const glowMap = {
  blue:   'shadow-blue-900/40',
  green:  'shadow-emerald-900/40',
  red:    'shadow-rose-900/40',
  yellow: 'shadow-amber-900/40',
}

export function StatCard({ label, value, sub, glow }: Props) {
  return (
    <div
      className={`rounded-xl p-5 fade-up ${glow ? `shadow-lg ${glowMap[glow]}` : ''}`}
      style={{
        background: 'linear-gradient(135deg, #112035 0%, #0a1628 100%)',
        border: '1px solid #1e3a5f',
      }}
    >
      <div
        style={{
          fontSize: '10px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#6b8fa8',
          marginBottom: '8px',
        }}
      >
        {label}
      </div>
      <div className="font-mono-jet" style={{ fontSize: '22px', fontWeight: 700, color: '#f8fafc' }}>
        {value}
      </div>
      {sub && (
        <div style={{ marginTop: '6px', fontSize: '11px', color: '#6b8fa8' }}>{sub}</div>
      )}
    </div>
  )
}
