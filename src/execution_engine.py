import os
import logging
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

class ExecutionEngine:
    """Handles order execution and risk management on Binance."""
    def __init__(self, mode="simulation"):
        self.mode = mode # 'simulation' or 'real'
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY")
        self.logger = logging.getLogger("ExecutionEngine")
        self.active_trades = {} # Track open positions for trailing stops/partials
        
        try:
            if self.api_key and self.api_secret:
                self.client = Client(self.api_key, self.api_secret)
                self.ready = True
            else:
                self.client = None
                self.ready = False
                self.logger.warning("No API keys found. Execution limited to simulation.")
        except Exception as e:
            self.logger.error(f"Failed to init Binance client: {e}")
            self.client = None
            self.ready = False

    def calculate_position_size(self, symbol, balance_usdt, risk_pct=0.01):
        """Calculates quantity based on a risk percentage of total balance."""
        # For simplicity, 100% of current risk_pct of balance
        amount_to_risk = balance_usdt * risk_pct
        return amount_to_risk

    def place_order(self, symbol, side, price, quantity, sl=None, tp=None):
        """Places an order on Binance (handles simulation vs real)."""
        order_info = {
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "mode": self.mode
        }

        if "order_id" in order_info or order_info.get("status") == "SUCCESS":
            # Track for trailing stops and partials
            self.active_trades[symbol] = {
                "side": side,
                "entry_price": price,
                "quantity": quantity,
                "highest_price": price if side == "BUY" else price,
                "lowest_price": price if side == "SELL" else price,
                "partial_exited": False,
                "trailing_stop_active": True,
                "trailing_dist_pct": 0.02 # Default 2%
            }
        
        return order_info

    def manage_active_trades(self, current_prices):
        """
        Updates trailing stops and handles partial exits for active trades.
        current_prices: dict {symbol: price}
        """
        closed_trades = []
        for symbol, trade in self.active_trades.items():
            if symbol not in current_prices: continue
            
            price = current_prices[symbol]
            side = trade["side"]
            
            # --- 1. PARTIAL EXIT (at 1% profit) ---
            if not trade["partial_exited"]:
                entry = float(trade["entry_price"])
                profit_pct = ((price - entry) / entry) * 100 if side == "BUY" else ((entry - price) / entry) * 100
                if profit_pct >= 1.0:
                    self.logger.info(f"🚀 PARTIAL EXIT: {symbol} at {price} (1% profit reached)")
                    trade["partial_exited"] = True
                    trade["quantity"] = float(trade["quantity"]) / 2
            
            # --- 2. TRAILING STOP ---
            dist = float(trade["trailing_dist_pct"])
            if side == "BUY":
                if price > float(trade["highest_price"]):
                    trade["highest_price"] = price
                
                stop_level = float(trade["highest_price"]) * (1 - dist)
                if price <= stop_level:
                    self.logger.info(f"🛑 TRAILING STOP HIT (BUY): {symbol} at {price}")
                    closed_trades.append((symbol, "TRAILING_STOP_HIT"))
            else: # SELL/SHORT
                if price < float(trade["lowest_price"]):
                    trade["lowest_price"] = price
                
                stop_level = float(trade["lowest_price"]) * (1 + dist)
                if price >= stop_level:
                    self.logger.info(f"🛑 TRAILING STOP HIT (SELL): {symbol} at {price}")
                    closed_trades.append((symbol, "TRAILING_STOP_HIT"))

        # Cleanup closed trades
        for symbol, reason in closed_trades:
            del self.active_trades[symbol]
            
        return closed_trades

    def set_mode(self, mode):
        if mode in ["simulation", "real"]:
            self.mode = mode
            self.logger.info(f"Execution Mode set to: {mode}")
