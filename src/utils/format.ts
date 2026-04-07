/**
 * Format utilities — all return React-safe JSX strings or numbers
 */

export function fmtMoney(val: string | number): { text: string; cls: string } {
  const n = parseFloat(String(val).replace(/[+$]/g, ''))
  if (isNaN(n)) return { text: String(val), cls: 'text-slate-400' }
  const abs = Math.abs(n).toFixed(2)
  if (n > 0) return { text: `+$${abs}`, cls: 'text-emerald-400' }
  if (n < 0) return { text: `-$${abs}`, cls: 'text-rose-400' }
  return { text: `$${abs}`, cls: 'text-slate-400' }
}

export function fmtPct(val: string | number): { text: string; cls: string } {
  const n = parseFloat(String(val).replace(/[+%]/g, ''))
  if (isNaN(n)) return { text: String(val), cls: 'text-slate-400' }
  const abs = Math.abs(n).toFixed(2)
  if (n > 0) return { text: `+${abs}%`, cls: 'text-emerald-400' }
  if (n < 0) return { text: `-${abs}%`, cls: 'text-rose-400' }
  return { text: `${abs}%`, cls: 'text-slate-400' }
}

export function fmtPrice(p: number): string {
  if (p >= 100) return p.toFixed(2)
  if (p >= 1)   return p.toFixed(4)
  return p.toPrecision(4)
}

/** Sample ledger data for demo when Flask API is not available */
export const DEMO_LEDGER = [
  { time:'08:01:22', symbol:'BTCUSDT',   profit:'+5.00',  roe:'+100.00%', tot_pnl:'+5.00',   tot_roe:'+100.00%', saldo:'5005.00', growth:'+0.10%' },
  { time:'08:45:11', symbol:'ETHUSDT',   profit:'+5.00',  roe:'+100.00%', tot_pnl:'+10.00',  tot_roe:'+200.00%', saldo:'5010.00', growth:'+0.20%' },
  { time:'09:12:33', symbol:'SOLUSDT',   profit:'+5.00',  roe:'+100.00%', tot_pnl:'+15.00',  tot_roe:'+300.00%', saldo:'5015.00', growth:'+0.30%' },
  { time:'09:58:47', symbol:'PAXGUSDT',  profit:'+5.00',  roe:'+100.00%', tot_pnl:'+20.00',  tot_roe:'+400.00%', saldo:'5020.00', growth:'+0.40%' },
  { time:'10:30:05', symbol:'BNBUSDT',   profit:'-7.50',  roe:'-150.00%', tot_pnl:'+12.50',  tot_roe:'+250.00%', saldo:'5012.50', growth:'+0.25%' },
  { time:'11:05:18', symbol:'ADAUSDT',   profit:'+5.00',  roe:'+100.00%', tot_pnl:'+17.50',  tot_roe:'+350.00%', saldo:'5017.50', growth:'+0.35%' },
  { time:'11:44:29', symbol:'XRPUSDT',   profit:'+5.00',  roe:'+100.00%', tot_pnl:'+22.50',  tot_roe:'+450.00%', saldo:'5022.50', growth:'+0.45%' },
  { time:'12:20:55', symbol:'ALICEUSDT', profit:'+5.00',  roe:'+100.00%', tot_pnl:'+27.50',  tot_roe:'+550.00%', saldo:'5027.50', growth:'+0.55%' },
]
