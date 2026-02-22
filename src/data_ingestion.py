import os
from binance.client import Client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class BinanceDataIngestor:
    def __init__(self):
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_SECRET_KEY")
        
        if not api_key or not api_secret:
            print("Warning: BINANCE_API_KEY or BINANCE_SECRET_KEY not found in environment variables. Functionality may be limited.")
            self.client = Client() # Public endpoints still work without keys
        else:
            self.client = Client(api_key, api_secret)

    def get_all_tickers(self):
        """Fetches all ticker prices."""
        try:
            tickers = self.client.get_all_tickers()
            return pd.DataFrame(tickers)
        except Exception as e:
            print(f"Error fetching tickers: {e}")
            return pd.DataFrame()

    def get_top_movers(self, limit=10):
        """
        Identifies assets with highest volatility/movement.
        Filters for USDT pairs to avoid redundancy.
        """
        try:
            # Get 24hr ticker data
            tickers = self.client.get_ticker()
            df = pd.DataFrame(tickers)
            
            # Filter for USDT pairs
            df = df[df['symbol'].str.endswith('USDT')]
            
            # Convert columns to numeric
            cols = ['priceChangePercent', 'quoteVolume', 'lastPrice']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            
            # Sort by absolute price change percent (high volatility)
            df['absPriceChange'] = df['priceChangePercent'].abs()
            top_movers = df.sort_values(by='absPriceChange', ascending=False).head(limit)
            
            return top_movers[['symbol', 'priceChangePercent', 'quoteVolume', 'lastPrice']]
        except Exception as e:
            print(f"Error fetching top movers: {e}")
            return pd.DataFrame()

    def get_historical_data(self, symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=200):
        """Fetches OHLCV data for a specific symbol."""
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Convert numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    # Test execution
    ingestor = BinanceDataIngestor()
    print("Top Movers (USDT):")
    print(ingestor.get_top_movers().head())
