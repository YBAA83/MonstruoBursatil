import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import sys

# Add the project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.business_logic import BusinessLogic

# Load environment variables
load_dotenv()

# Configure Logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"{log_dir}/agent.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MonstruoAgent")

def run_agent():
    logger.info("Starting Monstruo Bursátil Autonomous Agent 24/7...")
    
    try:
        logic = BusinessLogic()
    except Exception as e:
        logger.error(f"Failed to initialize BusinessLogic: {e}")
        return

    # Configuration
    symbols_env = os.getenv("AGENT_SYMBOLS")
    if symbols_env:
        symbols = [s.strip() for s in symbols_env.split(",")]
    else:
        # Default top assets
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT"]
    
    scan_interval = int(os.getenv("AGENT_SCAN_INTERVAL", 900)) # Default 15 minutes (900s)
    
    logger.info(f"Configuration: Symbols={symbols}, Interval={scan_interval}s")

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"--- Starting Analysis Cycle at {current_time} ---")
            
            # get_market_overview internally handles technical analysis, AI generation, and Telegram notification
            assets = logic.get_market_overview(specific_symbols=symbols, source="Binance")
            
            summary = []
            for asset in assets:
                sig = asset.get('signal', 'N/A')
                symbol = asset.get('symbol', 'N/A')
                summary.append(f"{symbol}: {sig}")
            
            logger.info(f"Cycle Complete. Signals: {', '.join(summary)}")
            logger.info(f"Sleeping for {scan_interval} seconds...")
            
        except Exception as e:
            logger.error(f"An error occurred during analysis cycle: {e}")
            # Wait a bit before retrying if there's an error
            time.sleep(60)
            continue
            
        time.sleep(scan_interval)

if __name__ == "__main__":
    run_agent()
