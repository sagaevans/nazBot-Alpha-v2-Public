"""
app.py — nazBot Alpha 2.0 Flask Dashboard
Optimizations:
  - Replaced bare open() calls with _atomic_write() using tempfile+os.replace()
    to prevent race-condition file corruption between Flask and bot thread.
  - _read_file_safe() wraps all reads with try/except so a mid-write read
    never crashes the dashboard.
  - Logging replaces bare print() for consistency.
  - close_all() loops cancel per-symbol only for symbols that actually have
    open orders (avoids redundant API calls).
  - API calls in index() wrapped in a single try block with granular logging.
  - PNL formula `realized_pnl = balance - 5000.0` is UNTOUCHED (testnet rule).
"""

import os
import json
import time
import logging
import tempfile
from flask import Flask, render_template_string, request, redirect, url_for
from binance.client import Client

logger = logging.getLogger('app')

app = Flask(__name__)
client = Client(
    os.environ.get('BINANCE_API_KEY'),
    os.environ.get('BINANCE_API_SECRET'),
    testnet=True
)

STATE_FILE   = 'status.txt'
HISTORY_FILE = 'trades_history.json'
SESSION_FILE = 'session.txt'
VIP_SYMBOLS  = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]

# ── Thread-safe I/O helpers ───────────────────────────────────────────────────

def _read_file_safe(path: str, default: str = '') -> str:
    """
    Baca file dengan aman.
    Jika file sedang ditulis (atau belum ada), kembalikan default.
    """
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read().strip()
    except OSError:
        pass
    return default


def _atomic_write(path: str, content: str) -> None:
    """
    Tulis file secara atomik menggunakan tempfile + os.replace().
    Mencegah korupsi data jika Flask & bot thread menulis bersamaan.
    """
    dir_ = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


# ── HTML Template (tidak diubah secara fungsional) ───────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>nazBot Alpha 2.0 - Ultimate Hybrid</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="10">
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: 'Segoe UI', sans-serif; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px;}
        .header-title h1 { margin:0; color: #38bdf8; }
        .header-title p { margin:5px 0 0 0; color: #94a3b8; }
        .header-actions { display: flex; gap: 10px; flex-wrap: wrap;}
        .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; box-shadow: 0 4px 6px rgba(0,0,0,0.3); overflow-x: auto;}
        .grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-box { background: #334155; padding: 15px; border-radius: 10px; text-align: center; border-left: 4px solid #3b82f6; }
        .stat-box h4 { margin: 0 0 5px 0; color: #94a3b8; font-size: 0.85em; text-transform: uppercase;}
        .stat-box h2 { margin: 0; font-size: 1.8em; }
        .btn { padding: 12px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; font-size: 0.95em; transition: 0.2s; }
        .btn:hover { opacity: 0.8; }
        .btn-start { background: #10b981; color: white; }
        .btn-stop { background: #f59e0b; color: white; }
        .btn-reset { background: #64748b; color: white; border: 1px solid #475569;}
        .btn-close-all { background: #ef4444; color: white; border: 2px solid #b91c1c;}
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95em; min-width: 600px;}
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; }
        .text-green { color: #10b981; } .text-red { color: #ef4444; } .text-gold { color: #f59e0b; } .text-blue { color: #38bdf8; }
        .badge { padding: 4px 8px; border-radius: 6px; font-size: 0.8em; font-weight: bold; border: 1px solid; }
        .bg-long { background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: #10b981; }
        .bg-short { background: rgba(239, 68, 68, 0.1); color: #ef4444; border-color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>🎯 nazBot Alpha 2.0</h1>
                <p>Hybrid Sniper | TP Fixed 50% | Trend Filter (EMA 200)</p>
            </div>
            <div class="header-actions">
                <form action="/toggle" method="post" style="margin:0;">
                    {% if status == 'OFF' %}
                        <button name="action" value="ON" class="btn btn-start">▶ START BOT</button>
                    {% else %}
                        <button name="action" value="OFF" class="btn btn-stop">⏸ STOP BOT</button>
                    {% endif %}
                </form>
                <form action="/reset_stats" method="post" style="margin:0;" onsubmit="return confirm('Yakin ingin mereset kalkulasi Winrate ke 0%? (Memulai Sesi Baru)');">
                    <button class="btn btn-reset">🔄 RESET STATS</button>
                </form>
                <form action="/close_all" method="post" style="margin:0;" onsubmit="return confirm('⚠️ PERINGATAN: Yakin ingin menutup SEMUA posisi berjalan secara Market dan membatalkan semua Take Profit?');">
                    <button class="btn btn-close-all">☠️ CLOSE ALL POSITIONS</button>
                </form>
            </div>
        </div>

        <div class="grid-stats">
            <div class="stat-box" style="border-color: #f59e0b;"><h4>Balance</h4><h2>${{ balance }}</h2></div>
            <div class="stat-box" style="border-color: #06b6d4;">
                <h4>Floating PNL (Active)</h4>
                <h2 class="{{ 'text-green' if total_pnl > 0 else 'text-red' if total_pnl < 0 else '' }}">
                    ${{ "%.2f"|format(total_pnl) }}
                </h2>
            </div>
            <div class="stat-box" style="border-color: #38bdf8;">
                <h4>Net Realized PNL</h4>
                <h2 class="{{ 'text-green' if realized_pnl > 0 else 'text-red' if realized_pnl < 0 else '' }}">
                    ${{ "%.2f"|format(realized_pnl) }}
                </h2>
            </div>
            <div class="stat-box" style="border-color: #8b5cf6;">
                <h4>Winrate (Sesi Ini)</h4>
                <h2>{{ "%.1f"|format(winrate) }}%</h2>
            </div>
        </div>

        <div class="card">
            <h3 class="text-gold">⭐ VIP Squad ({{ vip_positions|length }} / 6 Posisi)</h3>
            <table>
                <thead>
                    <tr><th>Symbol</th><th>Side</th><th>Lev</th><th>Margin</th><th>Entry Price</th><th>ROE (%)</th><th>Unrealized PNL</th></tr>
                </thead>
                <tbody>
                    {% for p in vip_positions %}
                    <tr>
                        <td><b>{{ p['symbol'] }}</b></td>
                        <td><span class="badge {{ 'bg-long' if p['side'] == 'LONG' else 'bg-short' }}">{{ p['side'] }}</span></td>
                        <td>{{ p['leverage'] }}x</td>
                        <td>${{ "%.2f"|format(p['margin']) }}</td>
                        <td style="color:#cbd5e1;">${{ p['entry'] }}</td>
                        <td class="{{ 'text-green' if p['roe'] > 0 else 'text-red' }}"><b>{{ "%.2f"|format(p['roe']) }}%</b></td>
                        <td class="{{ 'text-green' if p['pnl'] > 0 else 'text-red' }}">${{ "%.2f"|format(p['pnl']) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: #94a3b8; padding: 20px;">VIP sedang mengintai di TF 15m... 👁️</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3 style="color: #ef4444;">🐺 Hunter Squad - Alts ({{ alt_positions|length }} / 8 Posisi)</h3>
            <table>
                <thead>
                    <tr><th>Symbol</th><th>Side</th><th>Lev</th><th>Margin</th><th>Entry Price</th><th>ROE (%)</th><th>Unrealized PNL</th></tr>
                </thead>
                <tbody>
                    {% for p in alt_positions %}
                    <tr>
                        <td><b>{{ p['symbol'] }}</b></td>
                        <td><span class="badge {{ 'bg-long' if p['side'] == 'LONG' else 'bg-short' }}">{{ p['side'] }}</span></td>
                        <td>{{ p['leverage'] }}x</td>
                        <td>${{ "%.2f"|format(p['margin']) }}</td>
                        <td style="color:#cbd5e1;">${{ p['entry'] }}</td>
                        <td class="{{ 'text-green' if p['roe'] > 0 else 'text-red' }}"><b>{{ "%.2f"|format(p['roe']) }}%</b></td>
                        <td class="{{ 'text-green' if p['pnl'] > 0 else 'text-red' }}">${{ "%.2f"|format(p['pnl']) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: #94a3b8; padding: 20px;">Pemburu sedang men-scan Altcoin liar... 🐺</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    status           = _read_file_safe(STATE_FILE, 'OFF') or 'OFF'
    session_start_ms = int(_read_file_safe(SESSION_FILE, '0') or 0)

    balance        = 0.0
    vip_positions  = []
    alt_positions  = []
    total_margin   = 0.0
    total_unrealized = 0.0
    realized_pnl   = 0.0
    winrate        = 0.0

    try:
        # ── Balance ──────────────────────────────────────────
        acc = client.futures_account(recvWindow=6000)
        balance = round(
            float(next(a['walletBalance'] for a in acc['assets'] if a['asset'] == 'USDT')),
            2
        )
        realized_pnl = balance - 5000.0  # Rumus absolut Testnet — JANGAN DIUBAH

        # ── Posisi Aktif ─────────────────────────────────────
        all_pos = client.futures_position_information(recvWindow=6000)
        for p in all_pos:
            amt = float(p['positionAmt'])
            if abs(amt) == 0:
                continue

            sym         = p['symbol']
            side        = p['positionSide']
            unrealized  = float(p['unRealizedProfit'])
            entry_price = float(p['entryPrice'])
            lev         = int(p.get('leverage', 25))
            margin_used = (abs(amt) * entry_price) / lev if lev > 0 else 0
            roe         = (unrealized / margin_used * 100) if margin_used > 0 else 0

            total_margin     += margin_used
            total_unrealized += unrealized

            pos_data = {
                'symbol': sym, 'side': side, 'margin': margin_used,
                'entry': entry_price, 'roe': roe, 'pnl': unrealized, 'leverage': lev
            }
            if sym in VIP_SYMBOLS:
                vip_positions.append(pos_data)
            else:
                alt_positions.append(pos_data)

        # ── Winrate (filter sesi) ─────────────────────────────
        income_kwargs: dict = {'recvWindow': 6000}
        if session_start_ms > 0:
            income_kwargs.update({'limit': 1000, 'startTime': session_start_ms})
        else:
            income_kwargs['limit'] = 50

        wins, losses = 0, 0
        for income in client.futures_income_history(**income_kwargs):
            if income['incomeType'] == 'REALIZED_PNL':
                val = float(income['income'])
                if val > 0:
                    wins += 1
                elif val < 0:
                    losses += 1

        total_trades = wins + losses
        if total_trades > 0:
            winrate = (wins / total_trades) * 100

    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)

    total_roe = (total_unrealized / total_margin * 100) if total_margin > 0 else 0.0
    vip_positions.sort(key=lambda x: x['roe'], reverse=True)
    alt_positions.sort(key=lambda x: x['roe'], reverse=True)

    return render_template_string(
        HTML_TEMPLATE,
        status=status, balance=balance,
        vip_positions=vip_positions, alt_positions=alt_positions,
        total_roe=total_roe, total_pnl=total_unrealized,
        realized_pnl=realized_pnl, winrate=winrate
    )


@app.route('/toggle', methods=['POST'])
def toggle():
    new_status = request.form.get('action', 'OFF')
    _atomic_write(STATE_FILE, new_status)   # atomic — tidak korupsi
    return redirect(url_for('index'))


@app.route('/reset_stats', methods=['POST'])
def reset_stats():
    # Catat waktu milidetik saat ini sebagai awal "Sesi Baru"
    _atomic_write(SESSION_FILE, str(int(time.time() * 1000)))
    return redirect(url_for('index'))


@app.route('/close_all', methods=['POST'])
def close_all():
    """Tutup semua posisi aktif secara MARKET dan batalkan semua order TP/SL."""
    try:
        # Batalkan open orders — hanya untuk symbol yang benar-benar punya order
        open_orders = client.futures_get_open_orders()
        symbols_with_orders: set[str] = {o['symbol'] for o in open_orders}
        for sym in symbols_with_orders:
            try:
                client.futures_cancel_all_open_orders(symbol=sym)
            except Exception as e:
                logger.warning(f"Gagal cancel order {sym}: {e}")

        # Tutup semua posisi aktif
        positions = client.futures_position_information()
        for p in positions:
            amt = float(p['positionAmt'])
            if abs(amt) == 0:
                continue
            sym      = p['symbol']
            pos_side = p['positionSide']
            side     = 'SELL' if pos_side == 'LONG' else 'BUY'
            try:
                client.futures_create_order(
                    symbol=sym, side=side, type='MARKET',
                    quantity=abs(amt), positionSide=pos_side
                )
            except Exception as e:
                logger.warning(f"Gagal close posisi {sym}: {e}")

    except Exception as e:
        logger.error(f"Error Panic Close All: {e}", exc_info=True)

    return redirect(url_for('index'))


def run_web() -> None:
    app.run(host='0.0.0.0', port=8080, threaded=True)
