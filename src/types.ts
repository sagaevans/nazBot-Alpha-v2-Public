export interface Position {
  symbol: string
  side: 'LONG' | 'SHORT'
  leverage: number
  margin: number
  entry_price: number
  mark_price: number
  roe: number
  unrealized: number
}

export interface LedgerRow {
  time: string
  symbol: string
  profit: string
  roe: string
  tot_pnl: string
  tot_roe: string
  saldo: string
  growth: string
}

export interface DashboardData {
  status: string
  bot_status: 'ON' | 'OFF'
  wallet_balance: number
  equity: number
  net_profit: string
  net_roe: string
  total_unrealized: number
  total_active_roe: number
  total_margin: number
  gold_positions: Position[]
  vip_positions: Position[]
  alt_positions: Position[]
  ledger: LedgerRow[]
}

export interface ChartData {
  labels: string[]
  saldo: number[]
  growth: number[]
  tot_pnl: number[]
}
