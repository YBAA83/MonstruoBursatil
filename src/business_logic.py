from src.data_ingestion import BinanceDataIngestor
from src.ai_analyst import AIAnalyst
from src.news_scraper import NewsScraper
from src.notifier import TelegramNotifier
import pandas as pd
import time
import io

class BusinessLogic:
    def __init__(self):
        self.ingestor = BinanceDataIngestor()
        self.ai = AIAnalyst()
        self.news = NewsScraper()
        self.notifier = TelegramNotifier()
        self.cache = {}
        self.last_update = 0
        self.update_interval = 60
        self.timeframes = ["15m", "1h", "4h"]
        self.notified_signals = {} # Track last notified signal per symbol
        
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

            # Technical Analysis (KPIs) - Moved BEFORE AI to provide context
            kpis = {"RSI": None, "SMA_20": None, "EMA_50": None, "MACD": None, "BB_Upper": None, "BB_Lower": None}
            if not history.empty and len(history) > 50:
                try:
                    history['SMA_20'] = history['close'].rolling(window=20).mean()
                    history['EMA_50'] = history['close'].ewm(span=50, adjust=False).mean()
                    
                    # RSI
                    delta = history['close'].diff()
                    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                    rs = gain / loss
                    history['RSI_14'] = 100 - (100 / (1 + rs))
                    
                    # MACD
                    history['EMA_12'] = history['close'].ewm(span=12, adjust=False).mean()
                    history['EMA_26'] = history['close'].ewm(span=26, adjust=False).mean()
                    history['MACD'] = history['EMA_12'] - history['EMA_26']
                    history['MACD_Signal'] = history['MACD'].ewm(span=9, adjust=False).mean()
                    
                    # Bollinger Bands
                    history['STD_20'] = history['close'].rolling(window=20).std()
                    history['BB_Upper'] = history['SMA_20'] + (history['STD_20'] * 2)
                    history['BB_Lower'] = history['SMA_20'] - (history['STD_20'] * 2)
                    
                    kpis["RSI"] = history['RSI_14'].iloc[-1]
                    kpis["SMA_20"] = history['SMA_20'].iloc[-1]
                    kpis["EMA_50"] = history['EMA_50'].iloc[-1]
                    kpis["MACD"] = history['MACD'].iloc[-1]
                    kpis["BB_Upper"] = history['BB_Upper'].iloc[-1]
                    kpis["BB_Lower"] = history['BB_Lower'].iloc[-1]
                except Exception as e:
                    print(f"DEBUG: Error calculating KPIs for {symbol}: {e}")

            # AI Analysis
            print(f"DEBUG: Analyzing {symbol} with AI...")
            kpi_context = f" | RSI: {kpis['RSI']:.1f} | MACD: {kpis['MACD']:.4f} | BB: [{kpis['BB_Lower']:.2f} - {kpis['BB_Upper']:.2f}]" if kpis['RSI'] else ""
            ai_result = self.ai.analyze_asset(symbol, history, full_context + kpi_context)
            
            asset_obj = {
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
                "mtf_data": mtf_data,
                "kpis": kpis,
                "news": news_items
            }
            analyzed_assets.append(asset_obj)
            
            # Send Notification if Signal is High Conviction and changed
            if asset_obj['signal'] in ["Green", "Red"]:
                last_sig = self.notified_signals.get(symbol)
                if last_sig != asset_obj['signal']:
                    self.notifier.send_signal(
                        symbol=symbol,
                        signal=asset_obj['signal'],
                        price=asset_obj['price'],
                        reasoning=asset_obj['reasoning']
                    )
                    self.notified_signals[symbol] = asset_obj['signal']
            elif asset_obj['signal'] == "Yellow":
                # Clear notified status if it goes back to neutral
                self.notified_signals[symbol] = "Yellow"
            
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

    def generate_excel_report(self, analyzed_assets):
        """Genera un reporte en Excel basado en los activos analizados."""
        if not analyzed_assets:
            return None
            
        output = io.BytesIO()
        
        # Prepare data for Excel
        report_data = []
        for asset in analyzed_assets:
            report_data.append({
                "Activo": asset.get('symbol', 'N/A'),
                "Precio Actual": asset.get('price', 0),
                "Cambio 24h (%)": asset.get('change_24h', 0),
                "Señal AI": asset.get('signal', 'N/A'),
                "Razonamiento": asset.get('reasoning', 'N/A'),
                "Soportes/Resistencias": asset.get('levels', 'N/A'),
                "Whale Alert": "🚨 SÍ" if asset.get('whale_alert') else "No",
                "MTF Summary": ", ".join(asset.get('mtf_summary', []))
            })
        
        df = pd.DataFrame(report_data)
        
        # Write to Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Señales Monstruo')
            
            # Simple formatting logic if needed
            # Access workbook/worksheet if we want to bold headers etc.
            
        return output.getvalue()

if __name__ == "__main__":
    logic = BusinessLogic()
    print(logic.get_market_overview())
