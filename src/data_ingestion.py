import os
import requests
import streamlit as st
from binance.client import Client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class BinanceDataIngestor:
    def __init__(self):
        # Prefer st.secrets in Streamlit Cloud
        try:
            api_key = st.secrets.get("BINANCE_API_KEY", os.getenv("BINANCE_API_KEY"))
            api_secret = st.secrets.get("BINANCE_SECRET_KEY", os.getenv("BINANCE_SECRET_KEY"))
            self.tld = st.secrets.get("BINANCE_TLD", os.getenv("BINANCE_TLD", "com"))
        except:
            api_key = os.getenv("BINANCE_API_KEY")
            api_secret = os.getenv("BINANCE_SECRET_KEY")
            self.tld = os.getenv("BINANCE_TLD", "com")

        self.base_url = f"https://api.binance.{self.tld}"
        requests_params = {'timeout': 10}
        
        try:
            if not api_key or not api_secret:
                self.client = Client(tld=self.tld, requests_params=requests_params)
            else:
                self.client = Client(api_key, api_secret, tld=self.tld, requests_params=requests_params)
            
            # Ping test (silent failure)
            try:
                self.client.ping()
                self.sdk_ready = True
            except:
                self.sdk_ready = False
        except Exception as e:
            print(f"DEBUG: Binance Client Init failed: {e}")
            self.client = None
            self.sdk_ready = False

    def _fetch_rest(self, endpoint, params=None):
        """Fallback to direct REST API calls if SDK is blocked."""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"DEBUG: REST fallback failed for {endpoint}: {e}")
        return None

    def get_all_tickers(self):
        """Fetches all ticker prices with fallback."""
        if self.sdk_ready:
            try:
                tickers = self.client.get_all_tickers()
                return pd.DataFrame(tickers)
            except: pass
        
        data = self._fetch_rest("/api/v3/ticker/price")
        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_top_movers(self, limit=10):
        """Identifies assets with highest movement."""
        data = None
        if self.sdk_ready:
            try:
                data = self.client.get_ticker()
            except: pass
        
        if not data:
            data = self._fetch_rest("/api/v3/ticker/24hr")
            
        if not data: return pd.DataFrame()
        
        try:
            df = pd.DataFrame(data)
            df = df[df['symbol'].str.endswith('USDT')]
            cols = ['priceChangePercent', 'quoteVolume', 'lastPrice']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            df['absPriceChange'] = df['priceChangePercent'].abs()
            top_movers = df.sort_values(by='absPriceChange', ascending=False).head(limit)
            return top_movers[['symbol', 'priceChangePercent', 'quoteVolume', 'lastPrice']]
        except:
            return pd.DataFrame()

    def get_historical_data(self, symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=200):
        """Fetches OHLCV data with fallback."""
        data = None
        if self.sdk_ready:
            try:
                data = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            except: pass
        
        if not data:
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            data = self._fetch_rest("/api/v3/klines", params=params)

        if not data: return pd.DataFrame()
        
        try:
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except:
            return pd.DataFrame()

if __name__ == "__main__":
    ingestor = BinanceDataIngestor()
    print("Top Movers (USDT):")
    print(ingestor.get_top_movers().head())
