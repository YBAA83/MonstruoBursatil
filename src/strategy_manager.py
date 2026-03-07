import json
import os
from datetime import datetime, timedelta

class StrategyManager:
    """Manages the Snowball growth strategy: Compounding + Monthly contributions."""
    def __init__(self, data_file="data/strategy_state.json"):
        self.data_file = data_file
        self.ensure_data_dir()
        self.state = self.load_state()

    def ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

    def load_state(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default state
        return {
            "initial_capital": 100.0,
            "monthly_contribution": 50.0,
            "daily_target_pct": 0.01,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "contributions": [] # List of dates where $50 was added
        }

    def save_state(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def get_projected_balance(self, target_date=None):
        """Calculates what the balance SHOULD be today based on the math."""
        if not target_date:
            target_date = datetime.now()
        
        start_date = datetime.strptime(self.state["start_date"], "%Y-%m-%d")
        delta = (target_date - start_date).days
        
        # Base compounding: Initial * (1 + r)^days
        balance = self.state["initial_capital"] * ((1 + self.state["daily_target_pct"]) ** delta)
        
        # Add monthly contributions (simplified: every 30 days)
        months_passed = delta // 30
        for i in range(1, months_passed + 1):
            contrib_day = i * 30
            # Each contribution also compounds from the day it was added
            remaining_days = delta - contrib_day
            balance += self.state["monthly_contribution"] * ((1 + self.state["daily_target_pct"]) ** remaining_days)
            
        return balance

    def get_strategy_summary(self):
        projected = self.get_projected_balance()
        start_date = datetime.strptime(self.state["start_date"], "%Y-%m-%d")
        days_active = (datetime.now() - start_date).days
        
        return {
            "projected_balance": projected,
            "days_active": days_active,
            "next_contribution_days": 30 - (days_active % 30)
        }
