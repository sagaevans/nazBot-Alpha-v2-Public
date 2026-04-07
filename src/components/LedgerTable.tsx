import React from 'react'
import { LedgerRow } from '../types'
import { fmtMoney, fmtPct } from '../utils/format'

interface Props {
  rows: LedgerRow[]
}

export function LedgerTable({ rows }: Props) {
  const headers = [
    'Waktu', 'Pair', 'Profit $', 'ROE %',
    'Tot PNL $', 'Tot ROE %', 'Saldo $', 'Growth %',
  ]

  return (
    <div
      className="rounded-xl overflow-hidden fade-up"
      style={{ border: '1px solid #1e3a5f' }}
    >
      <div
        className="px-5 py-3"
        style={{ background: '#112035', borderBottom: '1px solid #1e3a5f' }}
      >
        <h3 style={{ fontWeight: 700, color: '#34d399', fontSize: '13px' }}>
          📗 Profit Ledger — Jurnal 8 Kolom (Last 20 Trades)
        </h3>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ background: '#08121f' }}>
              {headers.map((h, i) => (
                <th
                  key={h}
                  style={{
                    padding: '10px 14px',
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
            {rows.length === 0 ? (
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
                  📭 No closed trades yet...
                </td>
              </tr>
            ) : (
              rows.map((r, idx) => {
                const profit = fmtMoney(r.profit)
                const roe    = fmtPct(r.roe)
                const totPnl = fmtMoney(r.tot_pnl)
                const totRoe = fmtPct(r.tot_roe)
                const growth = fmtPct(r.growth)

                const colorOf = (c: { cls: string }) =>
                  c.cls.includes('emerald') ? '#10b981'
                  : c.cls.includes('rose')  ? '#f43f5e'
                  : '#6b8fa8'

                return (
                  <tr
                    key={idx}
                    style={{ borderTop: '1px solid #1a3050', transition: 'background 0.15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(37,99,235,0.06)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', color: '#6b8fa8', fontSize: '11px' }}
                    >
                      {r.time}
                    </td>
                    <td style={{ padding: '9px 14px', fontWeight: 700, color: '#e2e8f0' }}>
                      {r.symbol}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', textAlign: 'right', fontWeight: 700, color: colorOf(profit) }}
                    >
                      {profit.text}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', textAlign: 'right', fontWeight: 700, color: colorOf(roe) }}
                    >
                      {roe.text}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', textAlign: 'right', color: colorOf(totPnl) }}
                    >
                      {totPnl.text}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', textAlign: 'right', color: colorOf(totRoe) }}
                    >
                      {totRoe.text}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', textAlign: 'right', color: '#60a5fa', fontWeight: 700 }}
                    >
                      ${parseFloat(r.saldo).toFixed(2)}
                    </td>
                    <td
                      className="font-mono-jet"
                      style={{ padding: '9px 14px', textAlign: 'right', fontWeight: 700, color: colorOf(growth) }}
                    >
                      {growth.text}
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
