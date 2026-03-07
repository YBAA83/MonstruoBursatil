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

        if self.mode == "simulation":
            self.logger.info(f"[SIMULATION] Order Placed: {side} {quantity} {symbol} @ {price}")
            order_info["status"] = "FILLED"
            order_info["order_id"] = "SIM_12345"
            return order_info

        if not self.ready:
            return {"error": "Execution Engine not ready (No API Keys)"}

        try:
            # Placeholder for actual Binance API call
            # order = self.client.create_order(
            #     symbol=symbol,
            #     side=side,
            #     type='LIMIT',
            #     timeInForce='GTC',
            #     quantity=quantity,
            #     price=str(price)
            # )
            # return order
            self.logger.info(f"[REAL] Placing Order: {side} {quantity} {symbol} @ {price}")
            return {"status": "SUCCESS", "msg": "Real execution currently in sandbox mode"}
        except Exception as e:
            self.logger.error(f"Order placement failed: {e}")
            return {"error": str(e)}

    def set_mode(self, mode):
        if mode in ["simulation", "real"]:
            self.mode = mode
            self.logger.info(f"Execution Mode set to: {mode}")
