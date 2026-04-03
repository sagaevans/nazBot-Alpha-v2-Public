import threading
import time
import os
import logging
import sys

# Setup logging ke console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('main')

def _jalankan_trading():
    """Wrapper untuk run_bot dengan penanganan error level atas."""
    try:
        from bot_logic import run_bot
        run_bot()
    except Exception as e:
        logger.critical(f"Trading thread crash: {e}", exc_info=True)

def main():
    logger.info("🚀 Memulai Sistem nazBot Alpha 2.0 - S/R Sniper...")

    # File status untuk tombol ON/OFF
    if not os.path.exists('status.txt'):
        with open('status.txt', 'w') as f: f.write('OFF')

    # ── Jalankan trading thread ───────────────────────────────
    trading_thread = threading.Thread(target=_jalankan_trading, name='TradingThread', daemon=True)
    trading_thread.start()
    logger.info("✅ Trading Thread Aktif")

    # ── Watchdog: restart trading thread jika mati ────────────
    def watchdog():
        nonlocal trading_thread
        while True:
            time.sleep(30)
            if not trading_thread.is_alive():
                logger.warning("⚠️ Trading thread mati — restart dalam 10 detik...")
                time.sleep(10)
                trading_thread = threading.Thread(target=_jalankan_trading, name='TradingThread', daemon=True)
                trading_thread.start()
                logger.info("✅ Trading Thread berhasil direstart")

    watchdog_thread = threading.Thread(target=watchdog, name='Watchdog', daemon=True)
    watchdog_thread.start()
    logger.info("🛡️ Watchdog Thread Aktif")

    # ── Flask dashboard di main thread ───────────────────────
    logger.info("🌐 Web Dashboard aktif di port 8080")
    from app import run_web
    run_web()

if __name__ == '__main__':
    main()
