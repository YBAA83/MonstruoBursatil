import requests
import os
import streamlit as st

class TelegramNotifier:
    def __init__(self):
        # Load credentials from secrets or env
        try:
            self.bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN"))
            self.chat_id = st.secrets.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID"))
        except:
            self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
            
        self.enabled = bool(self.bot_token and self.chat_id)

    def send_signal(self, symbol, signal, price, reasoning):
        """Sends a formatted signal alert to Telegram."""
        if not self.enabled:
            return False

        icon = "🟢" if signal == "Green" else "🔴" if signal == "Red" else "🟡"
        message = f"""
{icon} *MONSTRUO BURSÁTIL ALERT* {icon}
        
*Activo:* {symbol}
*Precio:* ${price:,.2f}
*Señal:* {signal.upper()}
        
*Análisis:*
{reasoning}
        
🚀 _Monstruo Bursátil AI_
        """.strip()

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"DEBUG: Telegram notify failed: {e}")
            return False
