from src.data_ingestion import BinanceDataIngestor
from src.ai_analyst import AIAnalyst
from src.news_scraper import NewsScraper
from src.notifier import TelegramNotifier
from src.backtester import Backtester
from src.trading_journal import TradingJournal
from src.execution_engine import ExecutionEngine
import pandas as pd
import time
import io

class BusinessLogic:
    def __init__(self):
        self.ingestor = BinanceDataIngestor()
        self.ai = AIAnalyst()
        self.news = NewsScraper()
        self.notifier = TelegramNotifier()
        self.backtester = Backtester(self.ai, self.ingestor)
        self.execution = ExecutionEngine(mode="simulation") # Default to simulation
        self.cache = {}
        self.last_update = 0
        self.update_interval = 60
        self.timeframes = ["15m", "1h", "4h"]
        self.notified_signals = {} # Track last notified signal per symbol
        self.journal = TradingJournal() # Phase 13: 1% Goal & Journal
        self.debug_v = "14.0" # Updated version

    def run_backtest(self, symbol, interval="1h", days=7):
        """Bridge to run backtest simulation."""
        self.backtester.ingestor = self.ingestor
        return self.backtester.run_simulation(symbol, interval=interval, days=days)
        
    def is_healthy(self):
        """Checks if any data connection (Binance or Fallback) is alive."""
        binance_ok = self.ingestor and self.ingestor.sdk_ready
        fallback_ok = self.ingestor and self.ingestor.fallback and self.ingestor.fallback.yf is not None
        return binance_ok or fallback_ok

    def get_market_overview(self, specific_symbols=None, image_bytes=None):
        """
        Orchestrates the data flow:
        1. Fetch top movers OR specific symbols (Binance only).
        2. For selected assets, fetch news and historical data.
        3. Run AI analysis.
        4. Return structured data for Dashboard.
        """
        print(f"DEBUG: Executing get_market_overview...")

        # Original Binance Logic
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
            
            # Order Book Walls
            walls = self.process_depth_walls(symbol)
            wall_context = ""
            if walls:
                if walls['buy_wall']: wall_context += f" | BUY WALL found at {walls['buy_wall']}"
                if walls['sell_wall']: wall_context += f" | SELL WALL found at {walls['sell_wall']}"
            
            full_context = f"MTF Trends ({', '.join(mtf_summary)}) | {news_context}{whale_context}{wall_context}"

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
            ai_result = self.ai.analyze_asset(symbol, history, full_context + kpi_context, image_bytes=image_bytes)
            
            asset_obj = {
                "symbol": symbol,
                "price": row['lastPrice'],
                "change_24h": price_change,
                "volume": vol_24h,
                "whale_alert": whale_alert,
                "vol_anomaly": vol_anomaly_score,
                "mtf_summary": mtf_summary,
                "signal": ai_result["signal"],
                "confidence": ai_result.get("confidence", 5),
                "reasoning": ai_result["reasoning"],
                "levels": ai_result["levels"],
                "usage": ai_result.get("usage", {}),
                "history": history,
                "mtf_data": mtf_data,
                "kpis": kpis,
                "news": news_items,
                "walls": walls
            }
            analyzed_assets.append(asset_obj)
            
            # Send Notification if Signal is High Conviction and changed
            if asset_obj['signal'] in ["Green", "Red"]:
                last_sig = self.notified_signals.get(symbol)
                confidence = asset_obj.get('confidence', 5)
                
                if last_sig != asset_obj['signal'] and confidence >= 8:
                    print(f"DEBUG: High Confidence Signal ({confidence}/10) for {symbol}. Notifying...")
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

    def log_manual_trade(self, symbol, entry_price, exit_price, side, quantity, reason=""):
        """Bridge to log a trade into the persistent journal."""
        return self.journal.add_trade(symbol, entry_price, exit_price, side, quantity, reason)

    def trigger_automated_trade(self, asset_obj):
        """
        Executes a trade based on AI analysis.
        Only triggers if signal is Green/Red and confidence >= 9.
        """
        symbol = asset_obj['symbol']
        signal = asset_obj['signal']
        confidence = asset_obj.get('confidence', 0)
        price = asset_obj['price']
        
        if confidence < 9 or signal not in ["Green", "Red"]:
            return False

        # Calculate position size (1% risk of balance)
        # Mocking balance for now. In real mode, it would fetch from Binance.
        balance = 1000.0 
        qty_usd = self.execution.calculate_position_size(symbol, balance, risk_pct=0.01)
        qty = qty_usd / price

        side = "BUY" if signal == "Green" else "SELL"
        
        # Execute
        result = self.execution.place_order(symbol, side, price, qty)
        
        if "order_id" in result or result.get("status") == "SUCCESS":
            # Log in Journal automatically
            self.log_manual_trade(
                symbol=symbol,
                entry_price=price,
                exit_price=0, # Active trade
                side=side,
                quantity=qty,
                reason=f"AI Bot ({confidence}/10): {asset_obj['reasoning'][:50]}..."
            )
            # Notify Telegram
            self.notifier.send_message(f"🤖 **BOT EJECUTÓ TRADE**: {side} {symbol} @ {price}\nConfianza: {confidence}/10")
            return True
        return False

    def get_ticker_data(self, limit=20):
        """Lightweight fetch for ticker prices (Binance only)."""
        try:
            df = self.ingestor.get_all_tickers()
            if df.empty:
                tickers = self.ingestor._fetch_rest("/api/v3/ticker/24hr")
                if not tickers: return []
                df = pd.DataFrame(tickers)
            
            df = df[df['symbol'].str.endswith('USDT')]
            price_col = 'price' if 'price' in df.columns else 'lastPrice'
            change_col = 'priceChangePercent' if 'priceChangePercent' in df.columns else None
            
            if 'quoteVolume' in df.columns:
                df['quoteVolume'] = pd.to_numeric(df['quoteVolume'], errors='coerce')
                top_df = df.sort_values(by='quoteVolume', ascending=False).head(limit)
            else:
                top_df = df.head(limit)
                
            ticker_list = []
            for _, row in top_df.iterrows():
                ticker_list.append({
                    "symbol": row['symbol'],
                    "price": float(row[price_col]),
                    "change": float(row[change_col]) if change_col else 0.0
                })
            return ticker_list
        except Exception as e:
            print(f"DEBUG: Ticker fetch failed: {e}")
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

        return output.getvalue()



    def get_market_correlation(self, analyzed_assets):
        """Calculates correlation of assets vs prime asset (BTC or SPY)."""
        if len(analyzed_assets) < 2: return 0.0
        
        try:
            # Create a dataframe with close prices
            price_series = {}
            for asset in analyzed_assets:
                if not asset['history'].empty:
                    # Use last 50 candles
                    price_series[asset['symbol']] = asset['history']['close'].tail(50).values
            
            if not price_series: return 0.0
            
            df = pd.DataFrame(price_series)
            corr_matrix = df.corr()
            
            # Simple average correlation coefficient
            avg_corr = corr_matrix.mean().mean()
            return avg_corr
        except:
            return 0.0

    def process_depth_walls(self, symbol):
        """Analyzes order book for significant buy/sell walls."""
        try:
            depth = self.ingestor.get_order_book(symbol)
            if not depth: return None
            
            bids = pd.DataFrame(depth['bids'], columns=['price', 'qty'], dtype=float)
            asks = pd.DataFrame(depth['asks'], columns=['price', 'qty'], dtype=float)
            
            avg_bid = bids['qty'].mean()
            avg_ask = asks['qty'].mean()
            
            # Find walls (3x average qty)
            bid_wall = bids[bids['qty'] > avg_bid * 5].head(1)
            ask_wall = asks[asks['qty'] > avg_ask * 5].head(1)
            
            result = {
                "buy_wall": bid_wall['price'].iloc[0] if not bid_wall.empty else None,
                "sell_wall": ask_wall['price'].iloc[0] if not ask_wall.empty else None
            }
            return result
        except:
            return None
