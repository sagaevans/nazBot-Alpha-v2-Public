# ==========================================
# nazBot Sniper System [BETA v4.0] - FLASK DASHBOARD API
# FILE: app.py
# ENDPOINTS: /  /api/data  /api/toggle  /api/close_all  /api/ledger_chart
# ==========================================

import os
import logging
from flask import Flask, render_template, jsonify, request
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Suppress noisy werkzeug access logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

API_KEY    = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')

# Change testnet=False for a real Binance Futures account
client = Client(API_KEY, API_SECRET, testnet=True)

STATE_FILE  = 'status.txt'
LEDGER_FILE = 'profit_ledger.txt'

VIP_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "ADAUSDT", "DOTUSDT", "XRPUSDT", "ALICEUSDT"
}
GOLD_PAIRS = {"PAXGUSDT"}


# ──────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────

def read_bot_status() -> str:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return f.read().strip() or 'OFF'
    except Exception:
        pass
    return 'OFF'


def write_bot_status(status: str) -> None:
    with open(STATE_FILE, 'w') as f:
        f.write(status)


def parse_ledger(limit: int = 20) -> list:
    """
    Reads profit_ledger.txt and returns a list of dicts, each representing
    one closed trade row (8 columns).
    """
    history = []
    if not os.path.exists(LEDGER_FILE) or os.path.getsize(LEDGER_FILE) == 0:
        return history
    with open(LEDGER_FILE) as f:
        lines = [
            l for l in f.readlines()
            if '|' in l and 'TIME' not in l and '---' not in l
        ]
    for line in reversed(lines[-limit:]):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 8:
            history.append({
                'time':    parts[0],
                'symbol':  parts[1],
                'profit':  parts[2],
                'roe':     parts[3],
                'tot_pnl': parts[4],
                'tot_roe': parts[5],
                'saldo':   parts[6],
                'growth':  parts[7].rstrip()
            })
    return history


def parse_ledger_for_chart() -> dict:
    """
    Returns arrays suitable for Chart.js:
    labels (time), saldo (wallet balance float), growth (float)
    """
    all_lines = []
    if os.path.exists(LEDGER_FILE) and os.path.getsize(LEDGER_FILE) > 0:
        with open(LEDGER_FILE) as f:
            all_lines = [
                l for l in f.readlines()
                if '|' in l and 'TIME' not in l and '---' not in l
            ]

    labels  = []
    saldo   = []
    growth  = []
    tot_pnl = []

    for line in all_lines[-100:]:   # up to last 100 data points
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 8:
            labels.append(parts[0])
            try:
                saldo.append(float(parts[6]))
            except Exception:
                saldo.append(0.0)
            try:
                g = parts[7].replace('%', '').replace('+', '').rstrip()
                growth.append(float(g))
            except Exception:
                growth.append(0.0)
            try:
                p = parts[4].replace('$', '').replace('+', '')
                tot_pnl.append(float(p))
            except Exception:
                tot_pnl.append(0.0)

    return {
        'labels':  labels,
        'saldo':   saldo,
        'growth':  growth,
        'tot_pnl': tot_pnl
    }


# ──────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    """
    Main dashboard data endpoint.
    Returns: wallet_balance, equity, floating PNL, positions (gold/vip/alt),
             ledger history, and bot status.
    """
    try:
        # ── 1. Wallet Balance ──────────────────────────────────
        account_info   = client.futures_account()
        wallet_balance = 0.0
        for asset in account_info.get('assets', []):
            if asset['asset'] == 'USDT':
                wallet_balance = float(asset['walletBalance'])
                break

        # ── 2. Active Positions ────────────────────────────────
        positions         = client.futures_position_information()
        gold_positions    = []
        vip_positions     = []
        alt_positions     = []
        total_unrealized  = 0.0
        total_margin      = 0.0

        for p in positions:
            amt = float(p['positionAmt'])
            if amt == 0:
                continue

            symbol      = p['symbol']
            unrealized  = float(p['unRealizedProfit'])
            mark_price  = float(p['markPrice'])
            entry_price = float(p['entryPrice'])
            leverage    = float(p.get('leverage', 50))
            pos_side    = p['positionSide']

            actual_side = (pos_side if pos_side != 'BOTH'
                           else ('LONG' if amt > 0 else 'SHORT'))

            margin  = (abs(amt) * mark_price) / leverage
            roe_pct = (unrealized / margin * 100) if margin > 0 else 0.0

            total_unrealized += unrealized
            total_margin     += margin

            row = {
                'symbol':      symbol,
                'side':        actual_side,
                'leverage':    int(leverage),
                'margin':      round(margin, 4),
                'entry_price': entry_price,
                'mark_price':  mark_price,
                'roe':         round(roe_pct, 2),
                'unrealized':  round(unrealized, 4)
            }

            if symbol in GOLD_PAIRS:
                gold_positions.append(row)
            elif symbol in VIP_SYMBOLS:
                vip_positions.append(row)
            else:
                alt_positions.append(row)

        equity          = wallet_balance + total_unrealized
        total_active_roe = (total_unrealized / total_margin * 100
                            if total_margin > 0 else 0.0)

        # ── 3. Ledger (last 20 trades) ─────────────────────────
        ledger_data = parse_ledger(limit=20)
        net_profit  = ledger_data[0]['tot_pnl'] if ledger_data else "+0.00"
        net_roe     = ledger_data[0]['tot_roe'] if ledger_data else "+0.00%"

        return jsonify({
            'status':           'success',
            'bot_status':       read_bot_status(),
            'wallet_balance':   wallet_balance,
            'equity':           equity,
            'net_profit':       net_profit,
            'net_roe':          net_roe,
            'total_unrealized': total_unrealized,
            'total_active_roe': total_active_roe,
            'total_margin':     total_margin,
            'gold_positions':   gold_positions,
            'vip_positions':    vip_positions,
            'alt_positions':    alt_positions,
            'ledger':           ledger_data
        })

    except BinanceAPIException as e:
        return jsonify({'status': 'error', 'message': f"Binance API: {e.message}"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/ledger_chart')
def get_ledger_chart():
    """Returns time-series data for Chart.js growth visualization."""
    try:
        return jsonify({'status': 'success', 'chart': parse_ledger_for_chart()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/toggle', methods=['POST'])
def toggle_bot():
    """Toggles the bot ON / OFF via status.txt."""
    current = read_bot_status()
    new     = 'ON' if current == 'OFF' else 'OFF'
    write_bot_status(new)
    return jsonify({'status': 'success', 'bot_status': new})


@app.route('/api/close_all', methods=['POST'])
def close_all():
    """
    Emergency Panic Close:
    1. Stops the bot (writes OFF to status.txt)
    2. Cancels all open orders for each symbol
    3. Closes every active position at market price
    """
    try:
        write_bot_status('OFF')   # Halt bot first

        positions = client.futures_position_information()
        closed    = 0
        errors    = []

        for p in positions:
            amt = float(p['positionAmt'])
            if amt == 0:
                continue

            symbol   = p['symbol']
            pos_side = p['positionSide']

            # Cancel pending limit/stop orders
            try:
                client.futures_cancel_all_open_orders(symbol=symbol)
            except Exception as e:
                errors.append(f"CancelOrders {symbol}: {e}")

            # Close position at market
            action_side = 'SELL' if amt > 0 else 'BUY'
            try:
                client.futures_create_order(
                    symbol=symbol,
                    side=action_side,
                    type='MARKET',
                    quantity=abs(amt),
                    positionSide=pos_side
                )
                closed += 1
            except Exception as e:
                errors.append(f"Close {symbol}: {e}")

        msg = f"{closed} position(s) closed."
        if errors:
            msg += f" Errors: {'; '.join(errors)}"

        return jsonify({'status': 'success', 'message': msg})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/status')
def bot_status():
    """Lightweight endpoint to poll bot ON/OFF state."""
    return jsonify({'status': 'success', 'bot_status': read_bot_status()})


if __name__ == '__main__':
    write_bot_status('OFF')
    app.run(host='0.0.0.0', port=8080, debug=False)
