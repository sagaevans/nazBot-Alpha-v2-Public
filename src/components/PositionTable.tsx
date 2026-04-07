import React from 'react'
import { Position } from '../types'
import { SideBadge } from './SideBadge'
import { fmtMoney, fmtPct, fmtPrice } from '../utils/format'

interface Props {
  title: string
  emoji: string
  color: string
  positions: Position[]
  max: number
  emptyMsg: string
  badgeStyle?: React.CSSProperties
}

export function PositionTable({ title, emoji, color, positions, max, emptyMsg, badgeStyle }: Props) {
  return (
    <div
      className="rounded-xl overflow-hidden fade-up"
      style={{ border: '1px solid #1e3a5f' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ background: '#112035', borderBottom: '1px solid #1e3a5f' }}
      >
        <h3 style={{ fontWeight: 700, color, fontSize: '13px' }}>
          {emoji} {title}
        </h3>
        <span
          className="font-mono-jet"
          style={{
            fontSize: '11px',
            fontWeight: 700,
            padding: '3px 10px',
            borderRadius: '20px',
            ...badgeStyle,
          }}
        >
          {positions.length} / {max}
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#08121f' }}>
              {['Symbol', 'Side', 'Lev', 'Margin ($)', 'Entry', 'Mark', 'ROE %', 'Unrealized ($)'].map((h, i) => (
                <th
                  key={h}
                  style={{
                    padding: '10px 16px',
                    fontSize: '10px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: '#6b8fa8',
                    textAlign: i < 2 ? 'left' : 'right',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  style={{
                    padding: '20px',
                    textAlign: 'center',
                    color: '#6b8fa8',
                    fontStyle: 'italic',
                    fontSize: '12px',
                  }}
                >
                  {emptyMsg}
                </td>
              </tr>
            ) : (
              positions.map((p, idx) => {
                const roe = fmtPct(p.roe)
                const unr = fmtMoney(p.unrealized)
                return (
                  <tr
                    key={idx}
                    style={{ borderTop: '1px solid #1a3050', transition: 'background 0.15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(37,99,235,0.06)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '10px 16px', fontWeight: 700, color: '#e2e8f0' }}>
                      {p.symbol}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                      <SideBadge side={p.side} />
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '10px 16px', textAlign: 'right', color: '#6b8fa8' }}
                    >
                      {p.leverage}×
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '10px 16px', textAlign: 'right', color: '#c9daea' }}
                    >
                      ${p.margin.toFixed(2)}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '10px 16px', textAlign: 'right', color: '#6b8fa8' }}
                    >
                      {fmtPrice(p.entry_price)}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '10px 16px', textAlign: 'right', color: '#6b8fa8' }}
                    >
                      {fmtPrice(p.mark_price)}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: roe.cls.includes('emerald') ? '#10b981' : roe.cls.includes('rose') ? '#f43f5e' : '#6b8fa8' }}
                    >
                      {roe.text}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: unr.cls.includes('emerald') ? '#10b981' : unr.cls.includes('rose') ? '#f43f5e' : '#6b8fa8' }}
                    >
                      {unr.text}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
