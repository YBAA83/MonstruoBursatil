from src.data_ingestion import BinanceDataIngestor
from src.ai_analyst import AIAnalyst
from src.news_scraper import NewsScraper
import pandas as pd
import time

class BusinessLogic:
    def __init__(self):
        self.ingestor = BinanceDataIngestor()
        self.ai = AIAnalyst()
        self.news = NewsScraper()
        self.cache = {}
        self.last_update = 0
        self.update_interval = 60
        self.timeframes = ["15m", "1h", "4h"]
        
    def is_healthy(self):
        """Checks if the data connection is alive."""
        return self.ingestor and self.ingestor.client is not None

    def get_market_overview(self, specific_symbols=None):
        """
        Orchestrates the data flow:
        1. Fetch top movers OR specific symbols.
        2. For selected assets, fetch news and historical data.
        3. Run AI analysis.
        4. Return structured data for Dashboard.
        """
        print("DEBUG: Executing get_market_overview...")
        
        if specific_symbols:
            print(f"DEBUG: Processing specific symbols: {specific_symbols}")
            try:
                # Use robust method instead of raw client
                df_24h = self.ingestor.get_all_tickers()
                if df_24h.empty:
                    # Fallback to second robust method if first is too light
                    tickers = self.ingestor._fetch_rest("/api/v3/ticker/24hr")
                    if tickers: df_24h = pd.DataFrame(tickers)
                
                if df_24h.empty: return []

                # Filter for requested symbols
                # Handle both 'price' (ticker/price) and 'lastPrice' (ticker/24hr)
                top_movers = df_24h[df_24h['symbol'].isin(specific_symbols)].copy()
                
                # Ensure numeric and standard names
                if 'lastPrice' not in top_movers.columns and 'price' in top_movers.columns:
                    top_movers['lastPrice'] = top_movers['price']
                
                cols = ['priceChangePercent', 'quoteVolume', 'lastPrice']
                for c in cols:
                    if c in top_movers.columns:
                        top_movers[c] = pd.to_numeric(top_movers[c], errors='coerce')
                    else:
                        top_movers[c] = 0.0
            except Exception as e:
                print(f"DEBUG: Error fetching specific symbols: {e}")
                return []
        else:
            current_time = time.time()
            # Simple caching for top movers to avoid rate limits
            if current_time - self.last_update < self.update_interval and "top_movers" in self.cache:
                top_movers = self.cache["top_movers"]
            else:
                top_movers = self.ingestor.get_top_movers(limit=4)
                self.cache["top_movers"] = top_movers
                self.last_update = current_time

        analyzed_assets = []

        for index, row in top_movers.iterrows():
            symbol = row['symbol']
            price_change = row['priceChangePercent']
            vol_24h = row['quoteVolume']
            print(f"DEBUG: Processing {symbol}...")
            
            # Fetch MTF Context
            mtf_data = {}
            for tf in self.timeframes:
                try:
                    # Map common strings to binance intervals if needed
                    interval = tf
                    limit = 100 if tf == "15m" else 200
                    history = self.ingestor.get_historical_data(symbol, interval=interval, limit=limit)
                    mtf_data[tf] = history
                except Exception as e:
                    print(f"DEBUG: {tf} fetch failed for {symbol}: {e}")
                    mtf_data[tf] = pd.DataFrame()

            # Main history (1h default for back compatibility)
            history = mtf_data.get("1h", pd.DataFrame())
            
            # Whale Watcher (Volume Anomaly Detection)
            whale_alert = False
            vol_anomaly_score = 0
            if not mtf_data["1h"].empty:
                avg_vol = mtf_data["1h"]['volume'].tail(24).mean()
                last_vol = mtf_data["1h"]['volume'].iloc[-1]
                if last_vol > avg_vol * 3: # 300% spike
                    whale_alert = True
                    vol_anomaly_score = (last_vol / avg_vol)

            try:
                news_items = self.news.get_news_for_asset(symbol)
            except Exception as e:
                print(f"DEBUG: News fetch failed for {symbol}: {e}")
                news_items = []
            
            # MTF & Whale Context for AI
            mtf_summary = []
            for tf, df in mtf_data.items():
                if not df.empty:
                    last_c = df['close'].iloc[-1]
                    prev_c = df['close'].iloc[-2] if len(df) > 1 else last_c
                    tf_change = ((last_c - prev_c) / prev_c) * 100
                    mtf_summary.append(f"{tf}: {tf_change:+.2f}%")
            
            news_context = f"Latest {len(news_items)} news headlines: " + "; ".join([n['title'] for n in news_items]) if news_items else "No recent news."
            whale_context = f" | WHALE ALERT: Volume spike {vol_anomaly_score:.1f}x average!" if whale_alert else ""
            full_context = f"MTF Trends ({', '.join(mtf_summary)}) | {news_context}{whale_context}"

            # AI Analysis
            print(f"DEBUG: Analyzing {symbol} with AI...")
            ai_result = self.ai.analyze_asset(symbol, history, full_context)
            
            # Technical Analysis (KPIs)
            kpis = {"RSI": None, "SMA_20": None, "EMA_50": None}
            if not history.empty and len(history) > 50:
                try:
                    history['SMA_20'] = history['close'].rolling(window=20).mean()
                    history['EMA_50'] = history['close'].ewm(span=50, adjust=False).mean()
                    delta = history['close'].diff()
                    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                    rs = gain / loss
                    history['RSI_14'] = 100 - (100 / (1 + rs))
                    
                    kpis["RSI"] = history['RSI_14'].iloc[-1]
                    kpis["SMA_20"] = history['SMA_20'].iloc[-1]
                    kpis["EMA_50"] = history['EMA_50'].iloc[-1]
                except Exception as e:
                    print(f"DEBUG: Error calculating KPIs for {symbol}: {e}")

            analyzed_assets.append({
                "symbol": symbol,
                "price": row['lastPrice'],
                "change_24h": price_change,
                "volume": vol_24h,
                "whale_alert": whale_alert,
                "vol_anomaly": vol_anomaly_score,
                "mtf_summary": mtf_summary,
                "signal": ai_result["signal"],
                "reasoning": ai_result["reasoning"],
                "levels": ai_result["levels"],
                "usage": ai_result.get("usage", {}),
                "history": history,
                "mtf_data": mtf_data, # Store all timeframes for chart switching
                "kpis": kpis,
                "news": news_items
            })
            
        # Sort by volume descending
        analyzed_assets.sort(key=lambda x: x.get('volume', 0), reverse=True)
            
        print(f"DEBUG: Returning {len(analyzed_assets)} analyzed assets.")
        return analyzed_assets

    def get_ticker_data(self, limit=20):
        """Lightweight fetch for ticker prices with fallback."""
        try:
            df = self.ingestor.get_all_tickers()
            if df.empty:
                # Direct try in case ingestor fails
                tickers = self.ingestor._fetch_rest("/api/v3/ticker/24hr")
                if not tickers: return []
                df = pd.DataFrame(tickers)
            
            df = df[df['symbol'].str.endswith('USDT')]
            if 'quoteVolume' in df.columns:
                df['quoteVolume'] = pd.to_numeric(df['quoteVolume'], errors='coerce')
                top_df = df.sort_values(by='quoteVolume', ascending=False).head(limit)
            else:
                top_df = df.head(limit)
            
            ticker_list = []
            price_col = 'price' if 'price' in top_df.columns else 'lastPrice'
            change_col = 'priceChangePercent' if 'priceChangePercent' in top_df.columns else None
            
            for _, row in top_df.iterrows():
                ticker_list.append({
                    "symbol": row['symbol'],
                    "price": float(row[price_col]),
                    "change": float(row[change_col]) if change_col else 0.0
                })
            return ticker_list
        except Exception as e:
            print(f"DEBUG: Ticker fetch logic failed: {e}")
            return []

if __name__ == "__main__":
    logic = BusinessLogic()
    print(logic.get_market_overview())
