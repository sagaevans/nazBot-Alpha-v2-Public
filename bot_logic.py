import os, math, time, logging, json
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from binance.client import Client

logger = logging.getLogger('bot')

# ══════════════════════════════════════════════════════════════
# PARAMETER nazBot Alpha 2.0 (FIXED TP 50% | NO SL | HYBRID)
# ══════════════════════════════════════════════════════════════
API_KEY    = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')

LEVERAGE      = 25
BASE_MARGIN   = 15.0
TP_TARGET_ROE = 0.50  # 50% ROE Fixed

MAX_VIP       = 6
MAX_ALT       = 8

EMA_CONFIRM   = 9
VOL_MA_LEN    = 6
KLINE_LIMIT   = 150

VIP_SYMBOLS   = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]
VIP_TF        = '15m'
ALT_TFS       = ['5m', '3m', '1m']
TOP_ALT_LIMIT = 50

STATE_FILE    = 'status.txt'
HISTORY_FILE  = 'trades_history.json'

# ══════════════════════════════════════════════════════════════
# PARAMETER FILTER FAKEOUT (TUNABLE)
# ══════════════════════════════════════════════════════════════
BODY_RATIO_MIN   = 0.40   # Candle body harus >= 40% dari total range (high-low)
PROXIMITY_PCT    = 0.005  # Harga entry harus masih dalam 0.5% dari zona S/R
SNR_TOUCH_BUFFER = 0.001  # Buffer 0.1% toleransi sentuhan zona S/R
RSI_OB           = 72     # RSI Overbought — filter SHORT tidak masuk di atas nilai ini
RSI_OS           = 28     # RSI Oversold   — filter LONG tidak masuk di bawah nilai ini
ATR_ZONE_MULT    = 0.5    # Lebar zona S/R minimum = 0.5x ATR (filter zona palsu/sempit)
SNR_WINDOW       = 11     # Lebar jendela swing high/low (5 kiri + 1 tengah + 5 kanan)
SNR_TOUCH_CANDLE = 3      # Jumlah candle terakhir yang diperiksa untuk touch zona

# ══════════════════════════════════════════════════════════════
# CACHE GLOBAL (Mengurangi API call berulang)
# ══════════════════════════════════════════════════════════════
_filters_cache: dict = {}          # {symbol: {qty_step, min_qty, price_tick}}
_top_alts_cache: dict = {          # Cache top alts agar tidak hit API tiap loop
    'symbols': [],
    'last_update': 0
}
TOP_ALTS_TTL = 300  # Refresh top alts setiap 5 menit (detik)

_client = Client(API_KEY, API_SECRET, testnet=True)


# ══════════════════════════════════════════════════════════════
# UTILITY: LOG HISTORY & STATUS
# ══════════════════════════════════════════════════════════════
def log_trade_history(symbol, side, entry_price, tp_price):
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        new_entry = {
            "time":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "side":   side,
            "entry":  entry_price,
            "exit":   tp_price,
            "profit": f"{TP_TARGET_ROE * 100}% ROE"
        }
        history.insert(0, new_entry)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history[:50], f, indent=4)
    except Exception as e:
        logger.error(f"Gagal simpan log: {e}")


def get_bot_status():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return f.read().strip() or 'OFF'
    except:
        pass
    return 'OFF'


def setup_account_environment():
    try:
        _client.futures_change_position_mode(dualSidePosition=True)
    except:
        pass


# ══════════════════════════════════════════════════════════════
# CACHE: GET FILTERS (Fetch sekali, simpan selamanya per simbol)
# ══════════════════════════════════════════════════════════════
def get_filters(symbol: str) -> dict | None:
    """
    Ambil LOT_SIZE & PRICE_FILTER dari exchange info.
    Di-cache per simbol agar tidak hit API berulang kali.
    """
    if symbol in _filters_cache:
        return _filters_cache[symbol]
    try:
        info = _client.futures_exchange_info()
        for s in info['symbols']:
            sym = s['symbol']
            f = {x['filterType']: x for x in s['filters']}
            if 'LOT_SIZE' in f and 'PRICE_FILTER' in f:
                _filters_cache[sym] = {
                    'qty_step':   float(f['LOT_SIZE']['stepSize']),
                    'min_qty':    float(f['LOT_SIZE']['minQty']),
                    'price_tick': float(f['PRICE_FILTER']['tickSize'])
                }
        return _filters_cache.get(symbol)
    except Exception as e:
        logger.error(f"Gagal ambil filters [{symbol}]: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# CACHE: GET TOP VOLUME ALTS (Refresh setiap 5 menit)
# ══════════════════════════════════════════════════════════════
def get_top_volume_alts(exclude_list: list, limit: int = 50) -> list:
    """
    Ambil top N altcoin berdasarkan volume 24 jam.
    Di-cache 5 menit untuk mengurangi API call.
    """
    now = time.time()
    if _top_alts_cache['symbols'] and (now - _top_alts_cache['last_update']) < TOP_ALTS_TTL:
        # Kembalikan dari cache, filter exclude_list
        return [s for s in _top_alts_cache['symbols'] if s not in exclude_list]
    try:
        tickers = _client.futures_ticker()
        alts = [
            t for t in tickers
            if t['symbol'].endswith('USDT') and t['symbol'] not in exclude_list
        ]
        alts.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        symbols = [t['symbol'] for t in alts[:limit]]
        _top_alts_cache['symbols'] = symbols
        _top_alts_cache['last_update'] = now
        logger.info(f"🔄 Top Alts cache diperbarui ({len(symbols)} simbol)")
        return symbols
    except Exception as e:
        logger.error(f"Gagal tarik Top Volume: {e}")
        return _top_alts_cache.get('symbols', [])


# ══════════════════════════════════════════════════════════════
# CORE: DETEKSI S/R + SINYAL ENTRY — VECTORIZED & ANTI-FAKEOUT
# ══════════════════════════════════════════════════════════════
def get_snr_signal(symbol: str, tf: str) -> str | None:
    """
    Mendeteksi sinyal LONG/SHORT berdasarkan:
    1. Swing High/Low vectorized (tanpa loop per candle)
    2. Konfirmasi touch zona S/R (dengan buffer toleransi)
    3. Filter fakeout: body ratio, proximity, RSI, ATR zone width
    4. Konfirmasi EMA9 cross + volume spike

    Return: 'LONG' | 'SHORT' | None
    """
    try:
        # ── Ambil data kline ──────────────────────────────────
        bars = _client.futures_klines(symbol=symbol, interval=tf, limit=KLINE_LIMIT)
        df = pd.DataFrame(bars, columns=[
            'time','open','high','low','close','volume',
            'ct','qv','tr','tb','tq','i'
        ])
        df = df[['open','high','low','close','volume']].astype(float).reset_index(drop=True)

        if len(df) < SNR_WINDOW + 10:
            return None

        # ── Kalkulasi Indikator (Vectorized) ─────────────────
        df['vol_ma'] = df['volume'].rolling(window=VOL_MA_LEN, min_periods=1).mean()
        df['ema9']   = ta.trend.ema_indicator(df['close'], window=EMA_CONFIRM)
        df['rsi']    = ta.momentum.rsi(df['close'], window=14)
        df['atr']    = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)

        # Isi NaN di awal data dengan backfill
        df.bfill(inplace=True)

        # ── Deteksi Swing High/Low — VECTORIZED ──────────────
        # Swing Low: titik Low yang merupakan minimum dalam jendela SNR_WINDOW
        half = SNR_WINDOW // 2  # = 5
        roll_min = df['low'].rolling(window=SNR_WINDOW, center=True).min()
        roll_max = df['high'].rolling(window=SNR_WINDOW, center=True).max()

        # Swing Low valid: low == rolling min DAN volume > vol_ma di titik tersebut
        swing_low_mask  = (df['low']  == roll_min) & (df['volume'] > df['vol_ma'])
        # Swing High valid: high == rolling max DAN volume > vol_ma di titik tersebut
        swing_high_mask = (df['high'] == roll_max) & (df['volume'] > df['vol_ma'])

        # Ambil hanya swing yang sudah "terkonfirmasi" (bukan 5 candle terakhir)
        # agar jendela kanan sudah terbentuk sempurna
        confirmed_range = df.index[:-half]

        swing_lows  = df[swing_low_mask  & df.index.isin(confirmed_range)]
        swing_highs = df[swing_high_mask & df.index.isin(confirmed_range)]

        if swing_lows.empty or swing_highs.empty:
            return None

        # ── Ambil S/R Terdekat ke Harga Saat Ini ─────────────
        current_close = df['close'].iloc[-1]
        current_atr   = df['atr'].iloc[-1]

        # Support: swing low terdekat DI BAWAH harga sekarang
        supports = swing_lows[swing_lows['low'] < current_close]
        # Resistance: swing high terdekat DI ATAS harga sekarang
        resistances = swing_highs[swing_highs['high'] > current_close]

        if supports.empty or resistances.empty:
            return None

        # Ambil yang paling dekat
        nearest_supp_idx = (current_close - supports['low']).idxmin()
        nearest_res_idx  = (resistances['high'] - current_close).idxmin()

        supp_row = df.loc[nearest_supp_idx]
        res_row  = df.loc[nearest_res_idx]

        # ── Filter ATR: Zona S/R harus cukup lebar ───────────
        # Mencegah bot masuk di zona noise / zona terlalu sempit
        supp_zone_width = abs(supp_row['close'] - supp_row['open'])
        res_zone_width  = abs(res_row['close']  - res_row['open'])

        if supp_zone_width < (current_atr * ATR_ZONE_MULT):
            supp_row = None  # Zona support terlalu sempit, tidak valid
        if res_zone_width < (current_atr * ATR_ZONE_MULT):
            res_row = None   # Zona resistance terlalu sempit, tidak valid

        # Definisi zona (body candle sebagai zona inti)
        recent_supp = {
            'bottom': supp_row['low'],
            'top':    min(supp_row['open'], supp_row['close'])
        } if supp_row is not None else None

        recent_res = {
            'top':    res_row['high'],
            'bottom': max(res_row['open'], res_row['close'])
        } if res_row is not None else None

        if not recent_supp or not recent_res:
            return None

        # ── Data Candle untuk Konfirmasi Entry ────────────────
        prev = df.iloc[-2]   # Candle konfirmasi (sudah close)
        prev_body  = abs(prev['close'] - prev['open'])
        prev_range = prev['high'] - prev['low']

        # ── FILTER FAKEOUT #1: Body Ratio ─────────────────────
        # Tolak candle dengan sumbu/shadow panjang (body kecil = sinyal lemah)
        if prev_range > 0 and (prev_body / prev_range) < BODY_RATIO_MIN:
            return None

        # ── FILTER FAKEOUT #2: Proximity Filter ───────────────
        # Entry hanya valid jika harga MASIH DEKAT dengan zona S/R
        # Mencegah entry telat setelah harga sudah terlalu jauh bouncing
        supp_proximity = abs(prev['close'] - recent_supp['top']) / recent_supp['top']
        res_proximity  = abs(prev['close'] - recent_res['bottom']) / recent_res['bottom']

        # ── Konfirmasi Touch Zona (dengan buffer toleransi) ───
        touch_buffer_supp = recent_supp['top'] * (1 + SNR_TOUCH_BUFFER)
        touch_buffer_res  = recent_res['bottom'] * (1 - SNR_TOUCH_BUFFER)

        touched_supp = any(df['low'].iloc[-(SNR_TOUCH_CANDLE+1):-1] <= touch_buffer_supp)
        touched_res  = any(df['high'].iloc[-(SNR_TOUCH_CANDLE+1):-1] >= touch_buffer_res)

        # ── SINYAL LONG ───────────────────────────────────────
        if (
            touched_supp
            and supp_proximity <= PROXIMITY_PCT        # Harga masih dekat Support
            and prev['close'] > prev['open']           # Candle bullish
            and prev['close'] > prev['ema9']           # Close di atas EMA9
            and prev['volume'] > (prev['vol_ma'] * 0.8)  # Volume cukup
            and prev['rsi'] > RSI_OS                   # RSI tidak terlalu oversold ekstrim
            and prev['rsi'] < 60                       # RSI belum overbought
        ):
            logger.debug(f"✅ LONG Signal [{symbol} {tf}] | RSI: {prev['rsi']:.1f} | ATR: {current_atr:.4f}")
            return 'LONG'

        # ── SINYAL SHORT ──────────────────────────────────────
        if (
            touched_res
            and res_proximity <= PROXIMITY_PCT         # Harga masih dekat Resistance
            and prev['close'] < prev['open']           # Candle bearish
            and prev['close'] < prev['ema9']           # Close di bawah EMA9
            and prev['volume'] > (prev['vol_ma'] * 0.8)  # Volume cukup
            and prev['rsi'] < RSI_OB                   # RSI tidak terlalu overbought ekstrim
            and prev['rsi'] > 40                       # RSI belum oversold
        ):
            logger.debug(f"✅ SHORT Signal [{symbol} {tf}] | RSI: {prev['rsi']:.1f} | ATR: {current_atr:.4f}")
            return 'SHORT'

        return None

    except Exception as e:
        logger.error(f"get_snr_signal error [{symbol} {tf}]: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# EKSEKUSI ORDER: ENTRY + PASANG TP OTOMATIS (TANPA SL)
# ══════════════════════════════════════════════════════════════
def execute_snr_order(symbol: str, side: str, position_side: str) -> bool:
    """
    Buka posisi MARKET + pasang TAKE_PROFIT_MARKET otomatis.
    TP = Fixed 50% ROE (harga bergerak 2% dari entry di lev 25x).
    """
    try:
        f = get_filters(symbol)
        if not f:
            logger.warning(f"Filter tidak ditemukan untuk {symbol}, skip.")
            return False

        # Set leverage & margin type (error diabaikan jika sudah ter-set)
        try:
            _client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
        except:
            pass
        try:
            _client.futures_change_margin_type(symbol=symbol, marginType='CROSSED')
        except:
            pass

        curr_price = float(_client.futures_symbol_ticker(symbol=symbol)['price'])

        # ── Hitung TP 50% ROE ─────────────────────────────────
        price_move = TP_TARGET_ROE / LEVERAGE  # = 0.02 (2%)
        tp_price = curr_price * (1 + price_move) if side == 'BUY' else curr_price * (1 - price_move)

        # ── Hitung Quantity ───────────────────────────────────
        raw_qty = (BASE_MARGIN * LEVERAGE) / curr_price
        qty = max(
            f['min_qty'],
            round(math.floor(raw_qty / f['qty_step']) * f['qty_step'], 8)
        )

        # ── Buka Posisi MARKET ────────────────────────────────
        _client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=qty,
            positionSide=position_side
        )

        # ── Pasang Take Profit LIMIT ──────────────────────────
        tick      = f['price_tick']
        precision = max(0, -int(math.floor(math.log10(tick))))
        tp_final  = round(round(tp_price / tick) * tick, precision)

        close_side = 'SELL' if side == 'BUY' else 'BUY'
        _client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type='TAKE_PROFIT_MARKET',
            stopPrice=tp_final,
            closePosition=True,
            positionSide=position_side,
            timeInForce='GTE_GTC',
            workingType='MARK_PRICE'
        )

        log_trade_history(symbol, position_side, curr_price, tp_final)
        logger.info(
            f"🎯 ENTRY [{symbol} {position_side}] "
            f"| Entry: {curr_price} | TP 50% ROE: {tp_final} "
            f"| Qty: {qty} | Margin: ${BASE_MARGIN}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Order Gagal [{symbol} {position_side}]: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# HELPER: AMBIL POSISI AKTIF
# ══════════════════════════════════════════════════════════════
def get_active_positions() -> list:
    """Return list key posisi aktif: ['BTCUSDT_LONG', 'ETHUSDT_SHORT', ...]"""
    try:
        positions = _client.futures_position_information(recvWindow=5000)
        return [
            f"{p['symbol']}_{p['positionSide']}"
            for p in positions
            if float(p['positionAmt']) != 0
        ]
    except:
        return []


# ══════════════════════════════════════════════════════════════
# MAIN BOT LOOP
# ══════════════════════════════════════════════════════════════
def run_bot():
    setup_account_environment()
    logger.info(
        "🔥 nazBot Alpha 2.0 AKTIF | TP 50% FIXED | NO SL (DCA Ready) "
        f"| Slot: {MAX_VIP} VIP + {MAX_ALT} ALTS "
        f"| Filter: Body>{BODY_RATIO_MIN*100:.0f}% | Prox<{PROXIMITY_PCT*100:.1f}% "
        f"| RSI OS:{RSI_OS}/OB:{RSI_OB} | ATR Zone x{ATR_ZONE_MULT}"
    )

    while True:
        try:
            # ── Cek Status ON/OFF ─────────────────────────────
            if get_bot_status() != "ON":
                time.sleep(10)
                continue

            active_keys = get_active_positions()
            vip_count   = sum(1 for k in active_keys if k.split('_')[0] in VIP_SYMBOLS)
            alt_count   = len(active_keys) - vip_count

            # ── 1. VIP SQUAD: Scan 6 koin konstan di TF 15m ──
            if vip_count < MAX_VIP:
                logger.info(f"👑 VIP Scan | Slot tersisa: {MAX_VIP - vip_count}")
                for symbol in VIP_SYMBOLS:
                    if vip_count >= MAX_VIP:
                        break
                    # Skip jika sudah ada posisi aktif di simbol ini
                    if f"{symbol}_LONG" in active_keys or f"{symbol}_SHORT" in active_keys:
                        continue

                    signal = get_snr_signal(symbol, VIP_TF)
                    if signal:
                        side = 'BUY' if signal == 'LONG' else 'SELL'
                        if execute_snr_order(symbol, side, signal):
                            vip_count += 1
                            active_keys.append(f"{symbol}_{signal}")
                    time.sleep(0.2)  # Jeda kecil antar request

            # ── 2. HUNTER SQUAD: Cascading TF Altcoin ────────
            if alt_count < MAX_ALT:
                top_alts = get_top_volume_alts(VIP_SYMBOLS, limit=TOP_ALT_LIMIT)
                logger.info(
                    f"🐺 Hunter Scan | Slot tersisa: {MAX_ALT - alt_count} "
                    f"| Pool: {len(top_alts)} alts"
                )

                for tf in ALT_TFS:
                    if alt_count >= MAX_ALT:
                        break

                    found_in_this_tf = 0

                    for alt in top_alts:
                        if alt_count >= MAX_ALT:
                            break
                        if f"{alt}_LONG" in active_keys or f"{alt}_SHORT" in active_keys:
                            continue

                        signal = get_snr_signal(alt, tf)
                        if signal:
                            logger.info(f"🔎 Sinyal [{tf}] ditemukan: {alt} {signal}")
                            side = 'BUY' if signal == 'LONG' else 'SELL'
                            if execute_snr_order(alt, side, signal):
                                alt_count += 1
                                active_keys.append(f"{alt}_{signal}")
                                found_in_this_tf += 1
                        time.sleep(0.2)

                    # Turun ke TF lebih kecil hanya jika TF ini tidak menghasilkan
                    # sinyal SAMA SEKALI (bukan setelah 1 sinyal saja)
                    if found_in_this_tf > 0:
                        logger.info(
                            f"✅ {found_in_this_tf} sinyal ditemukan di TF {tf}, "
                            f"tidak turun ke TF lebih kecil."
                        )
                        break

            time.sleep(15)  # Jeda utama antar siklus scan

        except Exception as e:
            logger.error(f"Loop Error: {e}", exc_info=True)
            time.sleep(10)
