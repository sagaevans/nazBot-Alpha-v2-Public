# ==========================================
# nazBot Sniper System [BETA v4.0 - ULTRA CONFLUENCE ENGINE]
# FILE: bot_logic.py
# ENGINE: 5-Layer Confluence | Pinbar + Volume Spike | Long DCA | Short SL
# CONSTRAINTS: 50x Leverage | $5 Base Margin | 100% ROE TP | -150% ROE SL (Short only)
# ==========================================

from __future__ import annotations
import math
import os
import time
import logging
import random
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from ta.trend import ema_indicator, sma_indicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger('bot')

API_KEY    = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')

# ────────────────────────────────────────────────────
# CORE CONSTRAINTS (MANDATORY — DO NOT CHANGE)
# ────────────────────────────────────────────────────
TARGET_LEVERAGE  = 50
BASE_MARGIN      = 5.0
TP_TARGET_ROE    = 1.00   # 100% ROE  → immediate LIMIT order
SHORT_SL_ROE     = 1.50   # -150% ROE → STOP_MARKET order (Short only)

# ────────────────────────────────────────────────────
# LAYER 5: VOLUME FILTER
# ────────────────────────────────────────────────────
VOL_MA_PERIOD   = 20
VOL_MULTIPLIER  = 1.5    # signal requires > 1.5× average volume

# ────────────────────────────────────────────────────
# LONG-ONLY: 3-STAGE DYNAMIC DCA
# ────────────────────────────────────────────────────
DCA_1_DROP_PERCENT  = 2.0
DCA_2_DROP_PERCENT  = 3.0
DCA_3_DROP_PERCENT  = 4.0
DCA_1_MARGIN_RATIO  = 0.50
DCA_2_MARGIN_RATIO  = 0.50
DCA_3_MARGIN_RATIO  = 1.00

# ────────────────────────────────────────────────────
# ALLOCATION SLOTS
# ────────────────────────────────────────────────────
MAX_VIP  = 8   # 8 VIP positions
MAX_ALT  = 8   # 4 Aggressive (5m) + 4 Safe (15m)

# ────────────────────────────────────────────────────
# INDICATOR PARAMETERS
# ────────────────────────────────────────────────────
EMA_TREND  = 200
MA_STRUCT  = 99
BB_WINDOW  = 20
ATR_WINDOW = 14
RSI_WINDOW = 14

# Pinbar quality (lower = stricter)
SHADOW_REQ_VIP = 2.0   # VIP needs 2× body shadow
SHADOW_REQ_ALT = 1.2   # Alt needs 1.2× body shadow

# Static S/R lookback (Layer 4)
SR_LOOKBACK    = 50    # candles to scan for swing highs/lows
SR_ZONE_BUFFER = 0.003 # 0.3% proximity to S/R level

# ────────────────────────────────────────────────────
# SYMBOL LISTS
# ────────────────────────────────────────────────────
VIP_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
               "ADAUSDT", "DOTUSDT", "XRPUSDT", "ALICEUSDT"]
VIP_SET     = set(VIP_SYMBOLS)
VIP_TFS     = ['15m', '1h', '4h']

GOLD_PAIRS = ["PAXGUSDT"]   # Single PAXG slot
GOLD_SET   = set(GOLD_PAIRS)
GOLD_TFS   = ['15m', '1h', '4h']

ALT_TFS_FAST = ['5m', '15m', '1h', '4h']   # Aggressive (first 4 alt slots)
ALT_TFS_SAFE = ['15m', '1h', '4h']          # Safe (next 4 alt slots)
ALT_TF_ORDER = ['5m', '15m', '1h', '4h']

TOP_ALT_LIMIT = 50
STATE_FILE    = 'status.txt'
LEDGER_FILE   = 'profit_ledger.txt'

# ────────────────────────────────────────────────────
# GLOBAL SCOREBOARDS
# ────────────────────────────────────────────────────
TOTAL_CLOSED_ROE         = 0.0
TOTAL_CLOSED_ROE_PERCENT = 0.0
TOTAL_SUCCESS_TRADES     = 0
CLOSED_HISTORY: List[dict] = []
_coin_escalation_level: Dict[str, int] = {}

# Testnet flag — set testnet=False for live account
_client = Client(API_KEY, API_SECRET, testnet=True)

# ────────────────────────────────────────────────────
# CACHING & RATE LIMITING
# ────────────────────────────────────────────────────
_exchange_filter_cache: Dict[str, dict]  = {}
_ticker_cache: Dict[str, Any]            = {"data": None, "timestamp": 0}
_TICKER_CACHE_TTL                        = 5.0
_RATE_LIMIT_CALLS, _RATE_LIMIT_PERIOD   = 20, 1.0
_last_call_time                          = 0.0
_rate_limit_lock                         = threading.Lock()


def _rate_limit() -> None:
    global _last_call_time
    with _rate_limit_lock:
        now     = time.monotonic()
        elapsed = now - _last_call_time
        min_iv  = _RATE_LIMIT_PERIOD / _RATE_LIMIT_CALLS
        if elapsed < min_iv:
            time.sleep(min_iv - elapsed)
        _last_call_time = time.monotonic()


def _api_call(fn, *args, max_retries: int = 5, **kwargs):
    for attempt in range(max_retries):
        _rate_limit()
        try:
            return fn(*args, **kwargs)
        except BinanceAPIException as e:
            if e.code != -1121:
                logger.warning(f"⚠️  Binance Error [{fn.__name__}]: {e.message}")
            if e.code in (-1121, -4028, -2011, -2021, -2019):
                raise
            time.sleep(2 ** attempt + random.uniform(0, 1))
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"API Error: {fn.__name__}")


# ══════════════════════════════════════════════════════
# LEDGER & BALANCE UTILITIES
# ══════════════════════════════════════════════════════

def get_binance_balance() -> float:
    try:
        info = _api_call(_client.futures_account)
        for a in info.get('assets', []):
            if a['asset'] == 'USDT':
                return float(a['walletBalance'])
    except Exception:
        pass
    return 0.0


def get_initial_balance() -> float:
    is_new = not os.path.exists(LEDGER_FILE) or os.path.getsize(LEDGER_FILE) == 0
    if is_new:
        bal = get_binance_balance() or 5000.0
        with open('start_balance.txt', 'w') as f:
            f.write(str(bal))
        return bal
    if os.path.exists('start_balance.txt'):
        try:
            with open('start_balance.txt') as f:
                return float(f.read().strip())
        except Exception:
            pass
    return 5000.0


def get_last_ledger_data() -> Tuple[float, float]:
    if not os.path.exists(LEDGER_FILE) or os.path.getsize(LEDGER_FILE) == 0:
        return 0.0, 0.0
    try:
        with open(LEDGER_FILE) as f:
            lines = [l for l in f if '|' in l and 'TIME' not in l and '---' not in l]
        if not lines:
            return 0.0, 0.0
        parts = [p.strip() for p in lines[-1].split('|')]
        if len(parts) >= 8:
            return (
                float(parts[4].replace('$', '').replace('+', '')),
                float(parts[5].replace('%', '').replace('+', ''))
            )
    except Exception:
        pass
    return 0.0, 0.0


def _fetch_realized_pnl(symbol: str) -> float:
    try:
        data = _api_call(_client.futures_income_history,
                         symbol=symbol, incomeType="REALIZED_PNL", limit=1)
        if data:
            return float(data[0]['income'])
    except Exception:
        pass
    return BASE_MARGIN * TP_TARGET_ROE


def catat_transaksi_v2(symbol: str, pnl_usd: float, roe_percent: float) -> None:
    prev_tot_pnl, prev_tot_roe = get_last_ledger_data()
    new_tot_pnl = prev_tot_pnl + pnl_usd
    new_tot_roe = prev_tot_roe + roe_percent

    current_balance = get_binance_balance()
    start_balance   = get_initial_balance()
    growth_pct = ((current_balance - start_balance) / start_balance * 100
                  if start_balance > 0 else 0.0)

    now      = datetime.now().strftime("%H:%M:%S")
    log_line = (f"{now} | {symbol} | {pnl_usd:+.2f} | {roe_percent:+.2f}% | "
                f"{new_tot_pnl:+.2f} | {new_tot_roe:+.2f}% | "
                f"{current_balance:.2f} | {growth_pct:+.2f}%\n")

    is_new = not os.path.exists(LEDGER_FILE) or os.path.getsize(LEDGER_FILE) == 0
    with open(LEDGER_FILE, 'a') as f:
        if is_new:
            f.write("TIME | PAIR | PROFIT $ | ROE % | TOTAL PNL $ | TOTAL ROE % | SALDO BINANCE | GROWTH %\n")
            f.write("-" * 110 + "\n")
        f.write(log_line)

    logger.info(f"💾 [LEDGER] {symbol} | PNL: {pnl_usd:+.2f} | "
                f"Saldo: ${current_balance:.2f} | Growth: {growth_pct:+.2f}%")


# ══════════════════════════════════════════════════════
# EXCHANGE UTILITIES
# ══════════════════════════════════════════════════════

def _get_exchange_filters(symbol: str) -> dict:
    if symbol not in _exchange_filter_cache:
        info = _api_call(_client.futures_exchange_info)
        for s in info['symbols']:
            _exchange_filter_cache[s['symbol']] = {
                x['filterType']: x for x in s['filters']
            }
    return _exchange_filter_cache[symbol]


def _get_cached_ticker() -> List[dict]:
    global _ticker_cache
    now = time.time()
    if (_ticker_cache["data"] is None or
            now - _ticker_cache["timestamp"] > _TICKER_CACHE_TTL):
        _ticker_cache["data"]      = _api_call(_client.futures_ticker)
        _ticker_cache["timestamp"] = now
    return _ticker_cache["data"]


def _read_status() -> str:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return f.read().strip() or 'OFF'
    except Exception:
        pass
    return 'OFF'


def setup_account_environment() -> None:
    try:
        _client.futures_change_position_mode(dualSidePosition=True)
    except Exception:
        pass


def _get_dynamic_leverage_and_margin(symbol: str,
                                     target_margin: float) -> Tuple[int, float]:
    target_notional = target_margin * TARGET_LEVERAGE
    try:
        _client.futures_change_leverage(symbol=symbol, leverage=TARGET_LEVERAGE)
        return TARGET_LEVERAGE, target_margin
    except BinanceAPIException as e:
        if e.code == -4028:
            try:
                brackets = _client.futures_leverage_bracket(symbol=symbol)
                max_lev  = int(brackets[0]['brackets'][0]['initialLeverage'])
                _client.futures_change_leverage(symbol=symbol, leverage=max_lev)
                return max_lev, target_notional / max_lev
            except Exception:
                pass
        return TARGET_LEVERAGE, target_margin
    except Exception:
        return TARGET_LEVERAGE, target_margin


# ══════════════════════════════════════════════════════
# LAYER 1: TREND ALIGNMENT  (EMA 200 on 15m)
# ══════════════════════════════════════════════════════

def _is_trend_aligned(symbol: str, side: str) -> bool:
    """Layer 1 — Price must be above EMA 200 for LONG, below for SHORT."""
    try:
        bars = _api_call(_client.futures_klines,
                         symbol=symbol, interval='15m', limit=210)
        df    = pd.DataFrame(bars,
                              columns=['time','open','high','low','close','volume',
                                       'ct','qv','tr','tb','tq','i'])
        close   = df['close'].astype(float)
        ema200  = float(ema_indicator(close, window=200).iloc[-1])
        current = float(close.iloc[-1])
        if side == 'LONG':  return current > ema200
        if side == 'SHORT': return current < ema200
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════
# LAYER 4: STATIC SUPPORT / RESISTANCE
# ══════════════════════════════════════════════════════

def _find_static_levels(high: pd.Series, low: pd.Series,
                        close: pd.Series) -> Tuple[List[float], List[float]]:
    """
    Layer 4 — Identify swing highs (resistance) and swing lows (support)
    using a simple peak/trough detector over SR_LOOKBACK candles.
    """
    supports:    List[float] = []
    resistances: List[float] = []
    n = SR_LOOKBACK

    for i in range(2, n - 2):
        idx = len(low) - n + i
        if idx < 2 or idx >= len(low) - 2:
            continue
        # Swing Low
        if (low.iat[idx] < low.iat[idx - 1] and
                low.iat[idx] < low.iat[idx - 2] and
                low.iat[idx] < low.iat[idx + 1] and
                low.iat[idx] < low.iat[idx + 2]):
            supports.append(float(low.iat[idx]))
        # Swing High
        if (high.iat[idx] > high.iat[idx - 1] and
                high.iat[idx] > high.iat[idx - 2] and
                high.iat[idx] > high.iat[idx + 1] and
                high.iat[idx] > high.iat[idx + 2]):
            resistances.append(float(high.iat[idx]))

    return supports, resistances


def _near_static_level(price: float, levels: List[float]) -> bool:
    """True if price is within SR_ZONE_BUFFER of any S/R level."""
    for lvl in levels:
        if abs(price - lvl) / lvl <= SR_ZONE_BUFFER:
            return True
    return False


# ══════════════════════════════════════════════════════
# CORE SIGNAL ENGINE — 5-LAYER CONFLUENCE (v4.0)
# ══════════════════════════════════════════════════════

def get_adaptive_signal(symbol: str, tf: str, is_vip: bool) -> Optional[dict]:
    """
    5-Layer Confluence Signal Engine:

    Layer 1 — EMA 200 Trend Filter (checked separately via _is_trend_aligned)
    Layer 2 — MA 99 + Bollinger Bands (Dynamic Walls)
    Layer 3 — Volume MA Filter  (current vol > VOL_MULTIPLIER × average)
    Layer 4 — Static S/R Zones  (swing highs / lows)
    Layer 5 — Price Action       (Pinbar / Rejection Candle with large shadow)

    LONG  → Bullish pinbar bouncing off a dynamic/static SUPPORT  zone
    SHORT → Bearish pinbar rejected from a dynamic/static RESISTANCE zone

    Returns dict with 'side' and 'reason', or None if no confluence.
    """
    try:
        bars = _api_call(_client.futures_klines,
                         symbol=symbol, interval=tf, limit=300)
        df = pd.DataFrame(
            bars,
            columns=['time','open','high','low','close','volume',
                     'ct','qv','tr','tb','tq','i']
        )[['open','high','low','close','volume']].astype(float)

        if len(df) < EMA_TREND + 1:
            return None

        close  = df['close']
        high   = df['high']
        low    = df['low']
        open_  = df['open']
        volume = df['volume']

        # ── Indicators ──────────────────────────────────────────
        ema200 = ema_indicator(close, window=EMA_TREND)
        ma99   = sma_indicator(close, window=MA_STRUCT)
        bb     = BollingerBands(close=close, window=BB_WINDOW, window_dev=2)
        atr    = AverageTrueRange(high, low, close, window=ATR_WINDOW)
        rsi    = RSIIndicator(close, window=RSI_WINDOW)

        # Layer 3 — Volume MA (shift(1) to avoid look-ahead)
        vol_ma = volume.shift(1).rolling(window=VOL_MA_PERIOD).mean()
        df['vol_ma'] = vol_ma
        df.bfill(inplace=True)

        # ── Index pointers ───────────────────────────────────────
        i_curr = len(df) - 1
        i_prev = len(df) - 2

        c_close  = close.iat[i_curr]
        c_low    = low.iat[i_curr]
        c_high   = high.iat[i_curr]
        c_atr    = atr.average_true_range().iat[i_curr]
        c_rsi    = rsi.rsi().iat[i_curr]

        p_open   = open_.iat[i_prev]
        p_close  = close.iat[i_prev]
        p_low    = low.iat[i_prev]
        p_high   = high.iat[i_prev]
        p_vol    = volume.iat[i_prev]
        p_vol_ma = df['vol_ma'].iat[i_prev]

        c_ema200 = ema200.iat[i_curr]
        c_ma99   = ma99.iat[i_curr]
        c_bb_dn  = bb.bollinger_lband().iat[i_curr]
        c_bb_up  = bb.bollinger_hband().iat[i_curr]

        # ── Layer 3: Volume Spike Check ──────────────────────────
        if p_vol_ma <= 0 or p_vol < (p_vol_ma * VOL_MULTIPLIER):
            return None   # volume too thin — abort

        # ── Layer 4: Static S/R levels ───────────────────────────
        supports, resistances = _find_static_levels(high, low, close)

        # ── Dynamic proximity threshold ──────────────────────────
        dynamic_proximity = c_atr * 0.20
        shadow_req        = SHADOW_REQ_VIP if is_vip else SHADOW_REQ_ALT

        layers_hit_long  = 0
        layers_hit_short = 0
        reason_parts_l   = []
        reason_parts_s   = []

        # ── Layer 5 + 2: LONG — Bullish Pinbar at Support ────────
        # Pinbar: close > open (green candle), long lower shadow
        if p_close > p_open:
            body = abs(p_close - p_open) or 1e-10
            lower_shadow = min(p_open, p_close) - p_low
            if (lower_shadow / body) >= shadow_req:
                # Layer 2 — Dynamic wall below current price
                dynamic_floors = [t for t in [c_ema200, c_ma99, c_bb_dn] if t < c_close]
                if dynamic_floors:
                    closest_dyn = max(dynamic_floors)
                    if abs(c_low - closest_dyn) <= dynamic_proximity:
                        layers_hit_long += 1
                        reason_parts_l.append('DynSupport')

                # Layer 4 — Static support nearby
                if _near_static_level(c_low, supports):
                    layers_hit_long += 1
                    reason_parts_l.append('StaticS/R')

                # RSI oversold bonus
                if c_rsi < 45:
                    layers_hit_long += 1
                    reason_parts_l.append(f'RSI{c_rsi:.0f}')

                # Minimum confluence: at least 1 price level + volume (already passed)
                if layers_hit_long >= 1:
                    return {
                        'side': 'LONG',
                        'reason': 'Pinbar+Vol+' + '+'.join(reason_parts_l)
                    }

        # ── Layer 5 + 2: SHORT — Bearish Pinbar at Resistance ────
        # Pinbar: close < open (red candle), long upper shadow
        if p_close < p_open:
            body = abs(p_open - p_close) or 1e-10
            upper_shadow = p_high - max(p_open, p_close)
            if (upper_shadow / body) >= shadow_req:
                # Layer 2 — Dynamic wall above current price
                dynamic_ceilings = [t for t in [c_ema200, c_ma99, c_bb_up] if t > c_close]
                if dynamic_ceilings:
                    closest_dyn = min(dynamic_ceilings)
                    if abs(c_high - closest_dyn) <= dynamic_proximity:
                        layers_hit_short += 1
                        reason_parts_s.append('DynResist')

                # Layer 4 — Static resistance nearby
                if _near_static_level(c_high, resistances):
                    layers_hit_short += 1
                    reason_parts_s.append('StaticS/R')

                # RSI overbought bonus
                if c_rsi > 55:
                    layers_hit_short += 1
                    reason_parts_s.append(f'RSI{c_rsi:.0f}')

                if layers_hit_short >= 1:
                    return {
                        'side': 'SHORT',
                        'reason': 'Pinbar+Vol+' + '+'.join(reason_parts_s)
                    }

        return None

    except Exception as e:
        logger.debug(f"Signal error [{symbol}@{tf}]: {e}")
        return None


# ══════════════════════════════════════════════════════
# ORDER EXECUTION ENGINE
# ══════════════════════════════════════════════════════

def execute_order(symbol: str, order_side: str, position_side: str,
                  margin_to_use: float, is_dca: bool = False) -> bool:
    try:
        f         = _get_exchange_filters(symbol)
        qty_step  = float(f['LOT_SIZE']['stepSize'])
        min_qty   = float(f['LOT_SIZE']['minQty'])
        max_qty   = float(f.get('MARKET_LOT_SIZE', f['LOT_SIZE'])['maxQty'])
        tick      = float(f['PRICE_FILTER']['tickSize'])
        curr_p    = float(_api_call(_client.futures_symbol_ticker, symbol=symbol)['price'])

        actual_lev, adj_margin = _get_dynamic_leverage_and_margin(symbol, margin_to_use)

        raw_qty = (adj_margin * actual_lev) / curr_p
        qty     = round(round(raw_qty / qty_step) * qty_step, 8)
        qty     = min(max_qty, max(min_qty, qty))
        qty_str = f"{qty:.8f}".rstrip('0').rstrip('.')

        # ── 1. Market Entry ──────────────────────────────────────
        _api_call(_client.futures_create_order,
                  symbol=symbol, side=order_side, type='MARKET',
                  quantity=qty_str, positionSide=position_side)

        # ── 2. TP / SL Orders ────────────────────────────────────
        if not is_dca:
            price_prec = max(0, -int(math.floor(math.log10(tick))))

            if position_side == 'LONG':
                # TAKE PROFIT: Limit Sell (100% ROE)
                tp_raw = curr_p * (1 + TP_TARGET_ROE / actual_lev)
                tp_str = f"{round(round(tp_raw / tick) * tick, price_prec):.{price_prec}f}"
                try:
                    _api_call(_client.futures_create_order,
                              symbol=symbol, side='SELL', type='LIMIT',
                              price=tp_str, quantity=qty_str,
                              positionSide=position_side, timeInForce='GTC')
                except Exception as e:
                    logger.warning(f"Gagal TP LONG [{symbol}]: {e}")
                # NOTE: No Stop Loss for LONG — DCA handles drawdown.

            elif position_side == 'SHORT':
                # TAKE PROFIT: Limit Buy (100% ROE, below entry)
                tp_raw = curr_p * (1 - TP_TARGET_ROE / actual_lev)
                # STOP LOSS: Stop Market Buy (-150% ROE, above entry)
                sl_raw = curr_p * (1 + SHORT_SL_ROE / actual_lev)

                tp_str = f"{round(round(tp_raw / tick) * tick, price_prec):.{price_prec}f}"
                sl_str = f"{round(round(sl_raw / tick) * tick, price_prec):.{price_prec}f}"
                try:
                    _api_call(_client.futures_create_order,
                              symbol=symbol, side='BUY', type='LIMIT',
                              price=tp_str, quantity=qty_str,
                              positionSide=position_side, timeInForce='GTC')
                    _api_call(_client.futures_create_order,
                              symbol=symbol, side='BUY', type='STOP_MARKET',
                              stopPrice=sl_str, closePosition=True,
                              positionSide=position_side, timeInForce='GTC',
                              workingType='MARK_PRICE')
                except Exception as e:
                    logger.warning(f"Gagal TP/SL SHORT [{symbol}]: {e}")

        logger.info(f"🚀 {'DCA' if is_dca else 'ENTRY'} [{position_side}] {symbol} | "
                    f"Margin: ${adj_margin:.2f} | Lev: {actual_lev}x | "
                    f"Price: {curr_p:.4f}")
        return True

    except Exception as e:
        logger.error(f"❌ Order Gagal [{symbol}]: {e}")
        return False


# ══════════════════════════════════════════════════════
# DCA MONITOR (LONG POSITIONS ONLY)
# ══════════════════════════════════════════════════════

def _monitor_positions(positions: List[dict]) -> None:
    for p in positions:
        amt = float(p['positionAmt'])
        if amt <= 0:
            continue   # Skip SHORT (amt<0) and empty

        symbol      = p['symbol']
        unrealized  = float(p['unRealizedProfit'])
        mark_price  = float(p['markPrice'])
        actual_lev  = float(p.get('leverage', TARGET_LEVERAGE))
        curr_margin = (abs(amt) * mark_price) / actual_lev
        roe_pct     = (unrealized / curr_margin * 100) if curr_margin > 0 else 0

        _, base_adj = _get_dynamic_leverage_and_margin(symbol, BASE_MARGIN)

        dca1_trg  = -(DCA_1_DROP_PERCENT * actual_lev)
        dca2_trg  = -(DCA_2_DROP_PERCENT * actual_lev)
        dca3_trg  = -(DCA_3_DROP_PERCENT * actual_lev)
        dca1_amt  = base_adj * DCA_1_MARGIN_RATIO
        dca2_amt  = base_adj * DCA_2_MARGIN_RATIO
        dca3_amt  = base_adj * DCA_3_MARGIN_RATIO

        if roe_pct <= dca3_trg and curr_margin < (base_adj + dca1_amt + dca2_amt + 2.0):
            logger.info(f"🔥 DCA 3 [{symbol}] ROE: {roe_pct:.1f}% | +${dca3_amt:.2f}")
            execute_order(symbol, 'BUY', 'LONG', dca3_amt, is_dca=True)
        elif roe_pct <= dca2_trg and curr_margin < (base_adj + dca1_amt + 2.0):
            logger.info(f"💉 DCA 2 [{symbol}] ROE: {roe_pct:.1f}% | +${dca2_amt:.2f}")
            execute_order(symbol, 'BUY', 'LONG', dca2_amt, is_dca=True)
        elif roe_pct <= dca1_trg and curr_margin < (base_adj + 2.0):
            logger.info(f"💉 DCA 1 [{symbol}] ROE: {roe_pct:.1f}% | +${dca1_amt:.2f}")
            execute_order(symbol, 'BUY', 'LONG', dca1_amt, is_dca=True)


# ══════════════════════════════════════════════════════
# PARALLEL ALT SCANNER
# ══════════════════════════════════════════════════════

def _scan_single_alt(symbol: str, active_keys: List[str],
                     allowed_tfs: List[str]) -> Optional[Tuple[str, dict]]:
    if (f"{symbol}_LONG" in active_keys or
            f"{symbol}_SHORT" in active_keys):
        return None
    for tf in allowed_tfs:
        sig = get_adaptive_signal(symbol, tf, is_vip=False)
        if sig and _is_trend_aligned(symbol, sig['side']):
            logger.info(f"🎯 ALT Signal [{sig['side']}] {symbol} ({tf}) via {sig['reason']}")
            return (symbol, sig)
    return None


# ══════════════════════════════════════════════════════
# MAIN BOT LOOP
# ══════════════════════════════════════════════════════

_stop_event: Optional[threading.Event] = None


def shutdown_bot() -> None:
    global _stop_event
    if _stop_event:
        _stop_event.set()


def run_bot(stop_event: threading.Event) -> None:
    global (_stop_event, TOTAL_CLOSED_ROE, TOTAL_CLOSED_ROE_PERCENT,
            TOTAL_SUCCESS_TRADES, CLOSED_HISTORY, _coin_escalation_level)
    _stop_event = stop_event

    setup_account_environment()
    get_initial_balance()

    executor                = ThreadPoolExecutor(max_workers=5)
    _previous_active_keys   = set()
    first_run               = True
    _last_heartbeat         = 0.0

    try:
        while not _stop_event.is_set():
            try:
                if _read_status() != 'ON':
                    time.sleep(10)
                    continue

                # ── DCA Check ─────────────────────────────────────
                pos = _api_call(_client.futures_position_information)
                _monitor_positions(pos)

                active_keys       = [f"{p['symbol']}_{p['positionSide']}"
                                     for p in pos if float(p['positionAmt']) != 0]
                current_active    = set(active_keys)

                # ── Closed Position Detection ─────────────────────
                if not first_run:
                    for k in _previous_active_keys - current_active:
                        sym        = k.split('_')[0]
                        pnl_usd    = _fetch_realized_pnl(sym)
                        roe_pct    = (pnl_usd / BASE_MARGIN) * 100

                        catat_transaksi_v2(sym, pnl_usd, roe_pct)

                        TOTAL_CLOSED_ROE         += roe_pct
                        TOTAL_CLOSED_ROE_PERCENT += roe_pct
                        TOTAL_SUCCESS_TRADES     += 1

                        if sym not in VIP_SET and sym not in GOLD_SET:
                            _coin_escalation_level[sym] = (
                                _coin_escalation_level.get(sym, 0) + 1)

                        now_str = datetime.now().strftime("%H:%M:%S")
                        CLOSED_HISTORY.insert(0, {
                            'time':   now_str,
                            'symbol': sym,
                            'roe':    f"{pnl_usd:+.2f}$ ({roe_pct:+.2f}%)"
                        })
                        if len(CLOSED_HISTORY) > 20:
                            CLOSED_HISTORY.pop()

                _previous_active_keys = current_active
                first_run = False

                # ── Slot Counters ─────────────────────────────────
                vip_count        = sum(1 for k in active_keys if k.split('_')[0] in VIP_SET)
                alt_count        = sum(1 for k in active_keys
                                       if k.split('_')[0] not in VIP_SET
                                       and k.split('_')[0] not in GOLD_SET)
                gold_active_count = sum(1 for k in active_keys if k.split('_')[0] in GOLD_SET)

                # ── GOLD RADAR ────────────────────────────────────
                if gold_active_count == 0 and not _stop_event.is_set():
                    for sym in GOLD_PAIRS:
                        if (f"{sym}_LONG" not in active_keys and
                                f"{sym}_SHORT" not in active_keys):
                            for tf in GOLD_TFS:
                                sig = get_adaptive_signal(sym, tf, is_vip=True)
                                if sig:
                                    ps    = sig['side']
                                    os    = 'BUY' if ps == 'LONG' else 'SELL'
                                    logger.info(f"🏆 GOLD [{ps}] {sym} ({tf}) via {sig['reason']}")
                                    if execute_order(sym, os, ps, BASE_MARGIN):
                                        active_keys.append(f"{sym}_{ps}")
                                        current_active.add(f"{sym}_{ps}")
                                        _previous_active_keys = current_active
                                        gold_active_count += 1
                                        break
                        if gold_active_count > 0:
                            break

                # ── VIP SCANNER ───────────────────────────────────
                for sym in VIP_SYMBOLS:
                    if _stop_event.is_set() or vip_count >= MAX_VIP:
                        break
                    if (f"{sym}_LONG" not in active_keys and
                            f"{sym}_SHORT" not in active_keys):
                        for tf in VIP_TFS:
                            sig = get_adaptive_signal(sym, tf, is_vip=True)
                            if sig and _is_trend_aligned(sym, sig['side']):
                                ps = sig['side']
                                os = 'BUY' if ps == 'LONG' else 'SELL'
                                logger.info(f"👑 VIP [{ps}] {sym} ({tf}) via {sig['reason']}")
                                if execute_order(sym, os, ps, BASE_MARGIN):
                                    vip_count += 1
                                    active_keys.append(f"{sym}_{ps}")
                                    current_active.add(f"{sym}_{ps}")
                                    _previous_active_keys = current_active
                                    break

                # ── ALT PARALLEL SCANNER ─────────────────────────
                if alt_count < MAX_ALT and not _stop_event.is_set():
                    tickers = _get_cached_ticker()
                    alts = [
                        t['symbol']
                        for t in sorted(tickers,
                                        key=lambda x: float(x['quoteVolume']),
                                        reverse=True)
                        if (t['symbol'].endswith('USDT') and
                            t['symbol'] not in VIP_SET and
                            t['symbol'] not in GOLD_SET)
                    ][:TOP_ALT_LIMIT]

                    futs = []
                    for s in alts:
                        # First 4 slots use aggressive (5m+), next 4 use safe (15m+)
                        base_tfs  = ALT_TFS_FAST if alt_count < 4 else ALT_TFS_SAFE
                        esc       = _coin_escalation_level.get(s, 0)
                        valid_tfs = [tf for tf in base_tfs
                                     if ALT_TF_ORDER.index(tf) >= esc]
                        if not valid_tfs:
                            continue
                        futs.append(executor.submit(
                            _scan_single_alt, s, list(active_keys), valid_tfs))

                    for fut in as_completed(futs):
                        if _stop_event.is_set():
                            break
                        res = fut.result()
                        if res and alt_count < MAX_ALT:
                            sym, sig = res
                            ps = sig['side']
                            os = 'BUY' if ps == 'LONG' else 'SELL'
                            if execute_order(sym, os, ps, BASE_MARGIN):
                                alt_count += 1
                                active_keys.append(f"{sym}_{ps}")
                                current_active.add(f"{sym}_{ps}")
                                _previous_active_keys = current_active

                # ── Heartbeat ─────────────────────────────────────
                now = time.time()
                if now - _last_heartbeat >= 60.0:
                    logger.info(
                        f"👀 nazBot v4.0 | "
                        f"GOLD: {gold_active_count}/1 | "
                        f"VIP: {vip_count}/{MAX_VIP} | "
                        f"ALT: {alt_count}/{MAX_ALT}"
                    )
                    _last_heartbeat = now

                for _ in range(15):
                    if _stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(10)
    finally:
        executor.shutdown(wait=True)
        logger.info("nazBot engine stopped cleanly.")


if __name__ == "__main__":
    shutdown_event = threading.Event()
    run_bot(shutdown_event)
