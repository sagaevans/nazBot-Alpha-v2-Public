"""
bot_logic.py — nazBot Alpha 2.0 (LONG ONLY, 50x Auto-Lev, DCA Berlapis + 4th Wall S/R)
OPTIMIZED VERSION (FIXED SIGNAL) - Preserved original signal logic, added caching/rate limiting.
- Mode: LONG ONLY (VIP & ALT)
- Leverage: 50x (Auto turun ke batas maksimal jika ditolak)
- Base Margin: $5
- TP Target: 100% ROE
- DCA Trigger: Tahap 1 (-100% = $3), Tahap 2 (-150% = $3), Tahap 3 (-300% = $10)
- Entry Logic: 3 Tembok Dinamis (EMA/SMA/BB) ATAU 1 Tembok Statis (Historical Support)
- Stop Loss: DISABLED (No SL / Mode HODL)
"""

from __future__ import annotations
import math
import os
import time
import logging
import random
from typing import Optional, Dict, List, Any

import pandas as pd
from ta.trend import ema_indicator, sma_indicator
from ta.volatility import BollingerBands
from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests.exceptions

logger = logging.getLogger('bot')

API_KEY = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')

# --- PENGATURAN MUTLAK BOT ---
LEVERAGE = 50
BASE_MARGIN = 5.0
TP_TARGET_ROE = 1.00

DCA_1_TRIGGER = -1.00
DCA_1_AMOUNT = 3.0
DCA_2_TRIGGER = -1.50
DCA_2_AMOUNT = 3.0
DCA_3_TRIGGER = -3.00
DCA_3_AMOUNT = 10.0

MAX_VIP = 6
MAX_ALT = 8

EMA_TREND = 200
MA_STRUCT = 99
BB_WINDOW = 20
VOL_LOOKBACK = 5

VIP_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]
VIP_SET = set(VIP_SYMBOLS)
VIP_TF = '15m'
ALT_TFS = ['1m', '3m', '5m', '15m', '1h', '4h']
TOP_ALT_LIMIT = 50

STATE_FILE = 'status.txt'
PROXIMITY_PCT = 0.003

_client = Client(API_KEY, API_SECRET, testnet=True)

# ---------- CACHING ----------
_exchange_filter_cache: Dict[str, dict] = {}
_ticker_cache: Dict[str, Any] = {"data": None, "timestamp": 0}
_TICKER_CACHE_TTL = 5.0  # seconds

# ---------- RATE LIMITER ----------
_RATE_LIMIT_CALLS = 20
_RATE_LIMIT_PERIOD = 1.0
_last_call_time = 0.0

def _rate_limit():
    global _last_call_time
    now = time.monotonic()
    elapsed = now - _last_call_time
    if elapsed < _RATE_LIMIT_PERIOD / _RATE_LIMIT_CALLS:
        sleep_time = (_RATE_LIMIT_PERIOD / _RATE_LIMIT_CALLS) - elapsed
        time.sleep(sleep_time)
    _last_call_time = time.monotonic()

# ---------- ENHANCED API CALL WITH EXPONENTIAL BACKOFF ----------
def _api_call(fn, *args, max_retries: int = 5, **kwargs):
    for attempt in range(max_retries):
        _rate_limit()
        try:
            return fn(*args, **kwargs)
        except BinanceAPIException as e:
            if e.code in (-4028, -2011, -2021):
                raise
            if e.code == -1003 or "Too many requests" in e.message:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"Rate limit hit, retrying in {wait:.2f}s")
                time.sleep(wait)
                continue
            wait = 2 ** attempt + random.uniform(0, 0.5)
            logger.warning(f"API Retry {attempt+1}/{max_retries} [{e.code}]: {e.message}")
            time.sleep(wait)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait = 2 ** attempt + random.uniform(0, 0.5)
            logger.warning(f"Network error: {e}, retry in {wait:.2f}s")
            time.sleep(wait)
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"Unexpected error: {e}, retry in {wait:.2f}s")
            time.sleep(wait)
    raise RuntimeError(f"API call failed after {max_retries} attempts: {fn.__name__}")

def _get_exchange_filters(symbol: str) -> dict:
    if symbol not in _exchange_filter_cache:
        info = _api_call(_client.futures_exchange_info)
        for s in info['symbols']:
            _exchange_filter_cache[s['symbol']] = {x['filterType']: x for x in s['filters']}
    return _exchange_filter_cache[symbol]

def _get_cached_ticker() -> List[dict]:
    global _ticker_cache
    now = time.time()
    if _ticker_cache["data"] is None or (now - _ticker_cache["timestamp"]) > _TICKER_CACHE_TTL:
        _ticker_cache["data"] = _api_call(_client.futures_ticker)
        _ticker_cache["timestamp"] = now
    return _ticker_cache["data"]

def _read_status() -> str:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return f.read().strip() or 'OFF'
    except OSError:
        pass
    return 'OFF'

def _active_keys(positions: List[dict]) -> List[str]:
    return [f"{p['symbol']}_{p['positionSide']}" for p in positions if float(p['positionAmt']) != 0]

def setup_account_environment() -> None:
    try:
        _client.futures_change_position_mode(dualSidePosition=True)
    except Exception:
        pass

# ---------- AUTO-LEVERAGE (PRESERVED ORIGINAL LOGIC) ----------
def _set_safe_leverage(symbol: str, target_lev: int) -> int:
    try:
        _client.futures_change_leverage(symbol=symbol, leverage=target_lev)
        return target_lev
    except BinanceAPIException as e:
        if e.code == -4028:
            try:
                brackets = _client.futures_leverage_bracket(symbol=symbol)
                max_lev = int(brackets[0]['brackets'][0]['initialLeverage'])
                _client.futures_change_leverage(symbol=symbol, leverage=max_lev)
                logger.info(f"⚠️ Leverage {target_lev}x ditolak untuk {symbol}. Otomatis pakai mentok: {max_lev}x")
                return max_lev
            except Exception:
                return target_lev
        return target_lev
    except Exception:
        return target_lev

# ========== SIGNAL LOGIC – EXACTLY AS ORIGINAL (NO CHANGES) ==========
def get_adaptive_signal(symbol: str, tf: str, is_vip: bool) -> Optional[dict]:
    try:
        bars = _api_call(_client.futures_klines, symbol=symbol, interval=tf, limit=300)
        df = pd.DataFrame(bars, columns=['time','open','high','low','close','volume','ct','qv','tr','tb','tq','i'])[['open','high','low','close','volume']].astype(float)

        if len(df) < EMA_TREND + 1:
            return None

        close = df['close']
        ema200 = ema_indicator(close, window=EMA_TREND)
        ma99 = sma_indicator(close, window=MA_STRUCT)
        bb = BollingerBands(close=close, window=BB_WINDOW, window_dev=2)

        df['vol_ma'] = df['volume'].shift(1).rolling(window=VOL_LOOKBACK).mean()
        df.bfill(inplace=True)

        idx_curr = len(df) - 1
        idx_prev = len(df) - 2
        c_close = close.iat[idx_curr]
        c_low = df['low'].iat[idx_curr]
        c_ema200 = ema200.iat[idx_curr]
        c_ma99 = ma99.iat[idx_curr]
        c_bb_dn = bb.bollinger_lband().iat[idx_curr]
        p_open = df['open'].iat[idx_prev]
        p_close = close.iat[idx_prev]
        p_low = df['low'].iat[idx_prev]

        is_vol_exhausted = df['volume'].iat[idx_prev] < df['vol_ma'].iat[idx_prev]    
        shadow_req = 2.0 if is_vip else 0.8

        # Tembok 1, 2, 3 (Dinamis: EMA, SMA, BB)
        dynamic_floors = [t for t in [c_ema200, c_ma99, c_bb_dn] if t < c_close]
        closest_dynamic = max(dynamic_floors) if dynamic_floors else 0
        hit_dynamic = closest_dynamic > 0 and (abs(c_low - closest_dynamic) / closest_dynamic) <= PROXIMITY_PCT

        # Tembok 4 (Statis/Historis)
        static_support = df['low'].iloc[-100:-5].min()
        hit_static = static_support > 0 and (abs(c_low - static_support) / static_support) <= PROXIMITY_PCT

        if hit_dynamic or hit_static:
            if is_vol_exhausted and p_close > p_open:
                body = abs(p_close - p_open) or 0.00000001
                if ((min(p_open, p_close) - p_low) / body) >= shadow_req:
                    reason = "Tembok Dinamis (EMA/SMA/BB)" if hit_dynamic else "Tembok Statis (Historical Support)"
                    return {'side': 'LONG', 'reason': reason}
        return None
    except Exception:
        return None

# ---------- EXECUTION (UNCHANGED) ----------
def execute_order(symbol: str, side: str, position_side: str, margin_to_use: float, is_dca: bool = False) -> bool:
    try:
        f = _get_exchange_filters(symbol)
        qty_step = float(f['LOT_SIZE']['stepSize'])
        min_qty = float(f['LOT_SIZE']['minQty'])
        max_qty = float(f.get('MARKET_LOT_SIZE', f['LOT_SIZE'])['maxQty'])
        tick = float(f['PRICE_FILTER']['tickSize'])

        actual_lev = _set_safe_leverage(symbol, LEVERAGE)
        curr_price = float(_api_call(_client.futures_symbol_ticker, symbol=symbol)['price'])

        raw_qty = (margin_to_use * actual_lev) / curr_price
        qty = round(math.floor(raw_qty / qty_step) * qty_step, 8)
        qty = min(max_qty, max(min_qty, qty))
        qty_str = f"{qty:.8f}".rstrip('0').rstrip('.')

        _api_call(_client.futures_create_order, symbol=symbol, side=side, type='MARKET', quantity=qty_str, positionSide=position_side)

        if not is_dca:
            price_move = TP_TARGET_ROE / actual_lev
            tp_raw = curr_price * (1 + price_move)
            price_precision = max(0, -int(math.floor(math.log10(tick))))
            tp_str = f"{round(round(tp_raw / tick) * tick, price_precision):.{price_precision}f}"
            try:
                _api_call(_client.futures_create_order, symbol=symbol, side='SELL',
                          type='TAKE_PROFIT_MARKET', stopPrice=tp_str, closePosition=True,
                          positionSide=position_side, timeInForce='GTE_GTC', workingType='MARK_PRICE')
            except BinanceAPIException as tp_err:
                _api_call(_client.futures_create_order, symbol=symbol, side='SELL',
                          type='LIMIT', price=tp_str, quantity=qty_str, positionSide=position_side, timeInForce='GTC')

        logger.info(f"🚀 {'DCA' if is_dca else 'ENTRY'} [{symbol} {position_side}] Margin: ${margin_to_use} | Lev: {actual_lev}x | Harga: {curr_price}")
        return True
    except Exception as e:
        logger.error(f"Order Fail [{symbol}]: {e}")
        return False

# ---------- DCA MONITOR (EXACTLY AS ORIGINAL) ----------
def _monitor_positions(positions: List[dict]):
    for p in positions:
        amt = float(p['positionAmt'])
        if amt == 0:
            continue

        symbol = p['symbol']
        unrealized = float(p['unRealizedProfit'])
        mark_price = float(p['markPrice'])
        actual_lev = float(p.get('leverage', LEVERAGE))

        current_margin = (abs(amt) * mark_price) / actual_lev
        roe = (unrealized / current_margin) if current_margin > 0 else 0

        if roe <= DCA_1_TRIGGER and current_margin < (BASE_MARGIN + 2.0):
            logger.info(f"💉 DCA TAHAP 1 (-100% ROE) untuk {symbol}. Nembak ${DCA_1_AMOUNT}!")
            execute_order(symbol, 'BUY', 'LONG', DCA_1_AMOUNT, is_dca=True)

        elif roe <= DCA_2_TRIGGER and current_margin < (BASE_MARGIN + DCA_1_AMOUNT + 2.0):
            logger.info(f"💉 DCA TAHAP 2 (-150% ROE) untuk {symbol}. Nembak ${DCA_2_AMOUNT}!")
            execute_order(symbol, 'BUY', 'LONG', DCA_2_AMOUNT, is_dca=True)

        elif roe <= DCA_3_TRIGGER and current_margin < (BASE_MARGIN + DCA_1_AMOUNT + DCA_2_AMOUNT + 2.0):
            logger.info(f"🔥 DCA TAHAP 3 TERAKHIR (-300% ROE) untuk {symbol}. Nembak ${DCA_3_AMOUNT}!")
            execute_order(symbol, 'BUY', 'LONG', DCA_3_AMOUNT, is_dca=True)

# ---------- MAIN BOT LOOP ----------
def run_bot() -> None:
    setup_account_environment()
    while True:
        try:
            if _read_status() != 'ON':
                time.sleep(10)
                continue

            pos = _api_call(_client.futures_position_information)
            _monitor_positions(pos)

            active_keys = _active_keys(pos)
            vip_count = sum(1 for k in active_keys if k.split('_')[0] in VIP_SET)
            alt_count = sum(1 for k in active_keys if k.split('_')[0] not in VIP_SET)

            # VIP SCAN
            for symbol in VIP_SYMBOLS:
                if vip_count >= MAX_VIP:
                    break
                if f"{symbol}_LONG" not in active_keys:
                    sig = get_adaptive_signal(symbol, VIP_TF, is_vip=True)
                    if sig:
                        logger.info(f"🎯 Sinyal Ditemukan [{symbol}] via {sig['reason']}")
                        if execute_order(symbol, 'BUY', 'LONG', BASE_MARGIN):
                            vip_count += 1
                            active_keys.append(f"{symbol}_LONG")

            # ALT SCAN (using cached ticker)
            tickers = _get_cached_ticker()
            alts = [t['symbol'] for t in sorted(tickers, key=lambda x: float(x['quoteVolume']), reverse=True)
                    if t['symbol'].endswith('USDT') and t['symbol'] not in VIP_SET][:TOP_ALT_LIMIT]

            for symbol in alts:
                if alt_count >= MAX_ALT:
                    break
                if f"{symbol}_LONG" in active_keys:
                    continue

                for tf in ALT_TFS:
                    sig = get_adaptive_signal(symbol, tf, is_vip=False)
                    if sig:
                        logger.info(f"🎯 Sinyal Ditemukan [{symbol} di TF {tf}] via {sig['reason']}")
                        if execute_order(symbol, 'BUY', 'LONG', BASE_MARGIN):
                            alt_count += 1
                            active_keys.append(f"{symbol}_LONG")
                        break
                    time.sleep(0.2)

            time.sleep(15)
        except Exception as e:
            logger.error(f"Loop Error: {e}", exc_info=True)
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
