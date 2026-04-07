import React from 'react'

export function SideBadge({ side }: { side: 'LONG' | 'SHORT' | string }) {
  if (side === 'LONG') {
    return (
      <span
        style={{
          background: 'rgba(16,185,129,0.12)',
          border: '1px solid rgba(16,185,129,0.3)',
          color: '#10b981',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 800,
          letterSpacing: '0.08em',
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        LONG
      </span>
    )
  }
  return (
    <span
      style={{
        background: 'rgba(244,63,94,0.12)',
        border: '1px solid rgba(244,63,94,0.3)',
        color: '#f43f5e',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: 800,
        letterSpacing: '0.08em',
        fontFamily: 'JetBrains Mono, monospace',
      }}
    >
      SHORT
    </span>
  )
}
