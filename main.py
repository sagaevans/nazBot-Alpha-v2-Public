# ==========================================
# nazBot Sniper System [BETA v4.0]
# FILE: main.py
# ROLE: Entry point — starts Flask + Bot Engine in parallel threads
# COMPATIBLE: Replit, Railway, Blink, any Linux server
# ==========================================

import threading
import logging
import os
import sys

from app import app          # Flask instance
from bot_logic import run_bot, shutdown_bot

# ── Logging Configuration ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nazbot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('main')


def initialize_system() -> None:
    """
    Safe startup routine:
    - Resets bot status to OFF so it never auto-starts on reboot
    - Creates empty ledger file with header if it doesn't exist
    """
    try:
        with open('status.txt', 'w') as f:
            f.write('OFF')
        logger.info("✅ Bot status reset → OFF (Standby Mode).")
    except Exception as e:
        logger.error(f"Failed to reset status.txt: {e}")

    # Pre-create ledger with header if missing
    ledger_path = 'profit_ledger.txt'
    if not os.path.exists(ledger_path) or os.path.getsize(ledger_path) == 0:
        try:
            with open(ledger_path, 'w') as f:
                f.write(
                    "TIME | PAIR | PROFIT $ | ROE % | "
                    "TOTAL PNL $ | TOTAL ROE % | SALDO BINANCE | GROWTH %\n"
                )
                f.write("-" * 110 + "\n")
            logger.info(f"📄 Created empty {ledger_path} with header.")
        except Exception as e:
            logger.error(f"Failed to create {ledger_path}: {e}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  nazBot Sniper System [BETA v4.0] — Starting Up")
    logger.info("=" * 60)

    # 1. Safe initialization
    initialize_system()

    # 2. Bot engine runs in a daemon thread
    shutdown_event = threading.Event()
    bot_thread     = threading.Thread(
        target=run_bot,
        args=(shutdown_event,),
        name="BotEngine",
        daemon=True   # Automatically killed when Flask exits
    )
    bot_thread.start()
    logger.info("⚙️  Bot Engine started in background thread.")

    # 3. Flask dashboard runs in the main thread (blocks until KeyboardInterrupt)
    try:
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"🌐 Web Dashboard starting on http://0.0.0.0:{port}")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False   # CRITICAL: prevents double bot_thread startup
        )

    except KeyboardInterrupt:
        logger.info("🛑 KeyboardInterrupt received — shutting down.")

    finally:
        logger.info("🔴 Sending shutdown signal to Bot Engine...")
        shutdown_event.set()
        shutdown_bot()
        bot_thread.join(timeout=10)
        logger.info("✅ nazBot shut down cleanly. Goodbye, Boss!")
