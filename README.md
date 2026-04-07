# nazBot Sniper — BETA v4.0

Binance Futures Trading Bot + Web Dashboard  
**50× Leverage · $5 Base Margin · 100% ROE TP · -150% ROE SL (Short)**

---

## Architecture

```
nazbot/
├── main.py            ← Entry point: starts Flask + Bot Engine
├── app.py             ← Flask API server (dashboard endpoints)
├── bot_logic.py       ← Trading engine (5-layer confluence)
├── templates/
│   └── index.html     ← Web dashboard (dark theme, 8-col ledger, Chart.js)
├── requirements.txt   ← Python dependencies
├── profit_ledger.txt  ← 8-column trade ledger (auto-created)
├── status.txt         ← Bot ON/OFF state
└── start_balance.txt  ← Baseline balance for growth% calculation
```

---

## Quick Start (Replit / Linux Server)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables (Replit Secrets / .env)
```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

### 3. Choose Testnet or Live
In **bot_logic.py** and **app.py**, change:
```python
# Testnet (safe):
_client = Client(API_KEY, API_SECRET, testnet=True)

# Live account:
_client = Client(API_KEY, API_SECRET, testnet=False)
```

### 4. Run
```bash
python main.py
```
Dashboard opens at: **http://localhost:8080**

---

## Core Bot Rules

| Rule | Value |
|------|-------|
| Leverage | 50× (hard-coded) |
| Base Margin | $5 per entry |
| Take Profit | 100% ROE — instant LIMIT order |
| Long Stop Loss | None — 3-Stage DCA handles drawdown |
| Short Stop Loss | -150% ROE — STOP_MARKET |
| Gold Slot | 1 × PAXGUSDT |
| VIP Slots | 8 × (BTC ETH SOL BNB ADA DOT XRP ALICE) |
| Alt Slots | 8 × (4 Aggressive 5m + 4 Safe 15m) |

---

## 5-Layer Confluence Engine (v4.0)

| Layer | Indicator | Purpose |
|-------|-----------|---------|
| 1 | EMA 200 (15m) | Macro trend alignment |
| 2 | MA 99 + Bollinger Bands | Dynamic walls (support/resistance) |
| 3 | Volume MA × 1.5 | Volume spike confirmation |
| 4 | Static Swing S/R (50 bars) | Key price level proximity |
| 5 | Pinbar / Rejection Candle | Price action quality filter |

**LONG** = Bullish pinbar bouncing off support + volume spike  
**SHORT** = Bearish pinbar rejected from resistance + volume spike

---

## Profit Ledger Format

```
TIME | PAIR | PROFIT $ | ROE % | TOTAL PNL $ | TOTAL ROE % | SALDO BINANCE | GROWTH %
```

---

## Dashboard Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Web dashboard |
| `/api/data` | GET | Positions + ledger + balances |
| `/api/ledger_chart` | GET | Time-series for growth chart |
| `/api/toggle` | POST | Start / Stop bot |
| `/api/close_all` | POST | Emergency panic close |
| `/api/status` | GET | Bot ON/OFF state |
