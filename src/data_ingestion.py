import os
import requests
import streamlit as st
from binance.client import Client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class YFinanceDataIngestor:
    """Fallback ingestor for crypto prices using yfinance (Bypass 451 Restricted)."""
    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
        except: self.yf = None

    def get_historical_data(self, symbol, interval="1h", limit=200):
        if not self.yf: return pd.DataFrame()
        # Map symbol: BTCUSDT -> BTC-USD
        yf_symbol = symbol.replace("USDT", "-USD")
        
        # Map intervals
        yf_interval = "1h"
        if interval == "15m": yf_interval = "15m"
        elif interval == "4h": yf_interval = "1h"
        
        period = "5d" if limit <= 120 else "1mo"
        
        try:
            ticker = self.yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=yf_interval)
            if df.empty: return pd.DataFrame()
            
            df = df.reset_index()
            df = df.rename(columns={df.columns[0]: 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(limit)
        except: return pd.DataFrame()

    def get_ticker_info(self, symbol):
        if not self.yf: return None
        yf_symbol = symbol.replace("USDT", "-USD")
        try:
            ticker = self.yf.Ticker(yf_symbol)
            curr = ticker.fast_info['lastPrice']
            prev = ticker.fast_info['previousClose']
            return {
                "symbol": symbol,
                "price": curr,
                "change": ((curr - prev) / prev) * 100
            }
        except: return None

class BinanceDataIngestor:
    def __init__(self):
        self.fallback = YFinanceDataIngestor()
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
        """Try multiple Binance endpoints (api1, api2, api3) to bypass IP bans."""
        suffixes = ["", "1", "2", "3"]
        last_error = ""
        for s in suffixes:
            try:
                url = f"https://api{s}.binance.{self.tld}{endpoint}"
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    return response.json()
                last_error = f"HTTP {response.status_code}"
            except Exception as e:
                last_error = str(e)
        
        st.session_state['last_binance_error'] = last_error
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
            
        if not data:
            # Plan B: Try yfinance for top assets
            top_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
            fallback_data = []
            for s in top_assets:
                info = self.fallback.get_ticker_info(s)
                if info:
                    fallback_data.append({
                        "symbol": info['symbol'],
                        "priceChangePercent": info['change'],
                        "lastPrice": info['price'],
                        "quoteVolume": 0
                    })
            if fallback_data: return pd.DataFrame(fallback_data)
            return pd.DataFrame()
        
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

        if not data:
            # Plan B Fallback
            return self.fallback.get_historical_data(symbol, interval, limit)
        
        try:
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except:
            return pd.DataFrame()

    def get_long_history(self, symbol, interval="1h", days=30):
        """Fetches longer history for backtesting with caching."""
        cache_file = f"cache_{symbol}_{interval}_{days}d.csv"
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df

        limit = 1000 # Max for rest api often
        if days > 30: limit = 1000 # Need more logic for extremely long history
        
        df = self.get_historical_data(symbol, interval=interval, limit=limit)
        if not df.empty:
            df.to_csv(cache_file, index=False)
        return df

    def get_order_book(self, symbol, limit=100):
        """Fetches order book depth."""
        data = None
        if self.sdk_ready:
            try:
                data = self.client.get_order_book(symbol=symbol, limit=limit)
            except: pass
        
        if not data:
            params = {"symbol": symbol, "limit": limit}
            data = self._fetch_rest("/api/v3/depth", params=params)
            
        return data

if __name__ == "__main__":
    ingestor = BinanceDataIngestor()
    print("Top Movers (USDT):")
    print(ingestor.get_top_movers().head())
