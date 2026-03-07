import json
import os
from datetime import datetime

class TradingJournal:
    def __init__(self, log_file="data/trading_log.json"):
        self.log_file = log_file
        self.ensure_data_dir()
        self.logs = self.load_logs()
        self.daily_target = 1.0  # 1% target

    def ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def load_logs(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_logs(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.logs, f, indent=4)

    def add_trade(self, symbol, entry_price, exit_price, side, quantity, reason=""):
        """Logs a completed trade and calculates P/L."""
        if side.lower() == "buy":
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else: # sell/short
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            
        trade = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbol": symbol,
            "side": side,
            "entry": entry_price,
            "exit": exit_price,
            "qty": quantity,
            "pnl_pct": pnl_pct,
            "reason": reason
        }
        self.logs.append(trade)
        self.save_logs()
        return trade

    def get_daily_pnl(self, date_str=None):
        """Calculates total P/L for a specific day."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        daily_trades = [t for t in self.logs if t['date'] == date_str]
        total_pnl = sum([t['pnl_pct'] for t in daily_trades])
        return total_pnl

    def get_progress_to_target(self):
        """Returns percentage progress towards the 1% daily goal."""
        daily_pnl = self.get_daily_pnl()
        progress = (daily_pnl / self.daily_target) * 100
        return min(max(progress, 0), 100), daily_pnl

    def get_recent_trades(self, limit=10):
        return sorted(self.logs, key=lambda x: x['timestamp'], reverse=True)[:limit]
