import pandas as pd
import time
from datetime import datetime

class Backtester:
    def __init__(self, ai_analyst, data_ingestor):
        self.ai = ai_analyst
        self.ingestor = data_ingestor
        self.results = []
        self.equity_curve = []

    def run_simulation(self, symbol, interval="1h", days=7, initial_capital=1000, step=4):
        """
        Runs a backtesting simulation.
        Step: Analyze every N candles to save tokens.
        """
        df = self.ingestor.get_long_history(symbol, interval, days)
        if df.empty:
            return {"error": "No data available for the period."}

        capital = initial_capital
        position = 0 # 0 for neutral, >0 for long
        entry_price = 0
        trades = []
        
        # We need at least 50 candles for indicators context
        start_idx = 50
        
        for i in range(start_idx, len(df), step):
            # Window of data up to current point
            window = df.iloc[i-50:i]
            current_row = df.iloc[i]
            current_price = current_row['close']
            
            # Get AI signal
            # Optimization: could pass simpler context for backtest
            analysis = self.ai.analyze_asset(symbol, window, context="BACKTESTING MODE")
            signal = analysis['signal']
            
            # Logic for Long Only simulation (simplification)
            if signal == "Green" and position == 0:
                # Buy
                position = capital / current_price
                entry_price = current_price
                trades.append({
                    "time": current_row['timestamp'],
                    "type": "BUY",
                    "price": current_price,
                    "reason": analysis['reasoning']
                })
            elif signal == "Red" and position > 0:
                # Sell
                capital = position * current_price
                trades.append({
                    "time": current_row['timestamp'],
                    "type": "SELL",
                    "price": current_price,
                    "profit": ((current_price - entry_price) / entry_price) * 100,
                    "reason": analysis['reasoning']
                })
                position = 0
                entry_price = 0
            
            # Track equity
            current_equity = capital if position == 0 else position * current_price
            self.equity_curve.append({
                "time": current_row['timestamp'],
                "equity": current_equity
            })

        # Close final position if open
        if position > 0:
            last_price = df.iloc[-1]['close']
            capital = position * last_price
            trades.append({
                "time": df.iloc[-1]['timestamp'],
                "type": "SELL (Auto-close)",
                "price": last_price,
                "profit": ((last_price - entry_price) / entry_price) * 100,
                "reason": "End of backtest"
            })

        final_profit = ((capital - initial_capital) / initial_capital) * 100
        win_rate = 0
        if trades:
            sales = [t for t in trades if "SELL" in t['type']]
            if sales:
                winners = [s for s in sales if s['profit'] > 0]
                win_rate = (len(winners) / len(sales)) * 100

        return {
            "initial_capital": initial_capital,
            "final_capital": capital,
            "profit_pct": final_profit,
            "win_rate": win_rate,
            "total_trades": len(trades),
            "trades": trades,
            "equity_curve": self.equity_curve
        }
