import os
import sys

# CRITICAL: Fix for "ModuleNotFoundError: No module named 'src'"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

import streamlit as st
import traceback

def main():
    try:
        # 1. Page Config MUST be the absolute first thing
        st.set_page_config(
            page_title="El Monstruo Bursátil",
            page_icon="💹",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        run_dashboard()
    except Exception as e:
        # Show error even if config failed
        try:
            st.error("🔥 **ERROR DE ARRANQUE**")
            st.markdown(f"**Error:** `{type(e).__name__}: {str(e)}`")
            st.code(traceback.format_exc())
            
            with st.expander("🛠️ Diagnóstico"):
                st.write(f"CWD: {os.getcwd()}")
                st.write(f"Python: {sys.version}")
                st.write(f"Path: {sys.path}")
                st.write(f"Executable: {sys.executable}")
        except:
            # Fallback for truly early crashes
            print(f"CRITICAL CRASH: {e}")
            traceback.print_exc()

def run_dashboard():
    # 2. Lazy imports inside protected scope
    import time
    import requests
    import pandas as pd
    import plotly.graph_objects as go
    import textwrap
    from src.business_logic import BusinessLogic
    from src.data_ingestion import BinanceDataIngestor
    from src.stats_persistence import load_stats, save_stats
    from streamlit_autorefresh import st_autorefresh
    # Config moved to main()

    # Custom CSS for "Glassmorphism"
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .glass-card {
            background: rgba(30, 30, 35, 0.7);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 24px;
            color: white;
            margin-bottom: 25px;
            transition: transform 0.3s ease;
        }

        @keyframes scroll {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        .ticker-wrap {
            width: 100%;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.5);
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 20px;
        }
        .ticker {
            display: inline-block;
            white-space: nowrap;
            padding-right: 100%;
            animation: scroll 30s linear infinite;
        }
        .ticker-item {
            display: inline-block;
            padding: 0 40px;
            font-weight: 900;
            font-size: 1.1em;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize Logic
    @st.cache_resource
    def get_logic(): return BusinessLogic()
    logic = get_logic()

    # Historical Stats Persistence
    stats_data = load_stats()

    # Initialize session state (Hybrid: Persistent + Session)
    if 'hits' not in st.session_state: st.session_state.hits = stats_data['hits']
    if 'misses' not in st.session_state: st.session_state.misses = stats_data['misses']
    if 'total_input' not in st.session_state: st.session_state.total_input = stats_data['total_input']
    if 'total_output' not in st.session_state: st.session_state.total_output = stats_data['total_output']

    # UI State
    if 'market_overview' not in st.session_state: st.session_state.market_overview = None
    if 'ticker_data' not in st.session_state: st.session_state.ticker_data = []
    if 'prediction_history' not in st.session_state: st.session_state.prediction_history = {}
    if 'last_selected_assets' not in st.session_state: 
        st.session_state.last_selected_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT"]

    # Sidebar
    st.sidebar.title("🚀 Monstruo Bursátil")
    st.sidebar.markdown("---")
    
    # --- MARKET SELECTOR ---
    market_source = st.sidebar.radio("📚 Seleccionar Mercado", ["Binance", "Nasdaq", "Forex", "SP500"], horizontal=True)
    st.sidebar.markdown("---")

    # Stats Sections
    st.sidebar.subheader("📊 Marcador Histórico")
    col_h, col_m = st.sidebar.columns(2)
    col_h.metric("Aciertos ✅", st.session_state.hits)
    col_m.metric("Fallos ❌", st.session_state.misses)

    total_hist = st.session_state.hits + st.session_state.misses
    if total_hist > 0:
        winrate_hist = (st.session_state.hits / total_hist) * 100
        st.sidebar.progress(winrate_hist / 100)
        st.sidebar.caption(f"Tasa de Acierto: {winrate_hist:.1f}%")

    st.sidebar.markdown("---")
    st.sidebar.subheader("💎 Consumo de API")
    total_tokens = st.session_state.total_input + st.session_state.total_output
    cost_usd = (st.session_state.total_input / 1_000_000 * 0.10) + (st.session_state.total_output / 1_000_000 * 0.30)
    cost_eur = cost_usd * 0.94

    st.sidebar.metric("Tokens", f"{total_tokens:,}")
    st.sidebar.write(f"💵 ${cost_usd:,.4f} USD")
    st.sidebar.write(f"💶 {cost_eur:,.4f} EUR")

    # Report Section
    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Reportes")
    if st.session_state.market_overview:
        excel_data = logic.generate_excel_report(st.session_state.market_overview)
        if excel_data:
            st.sidebar.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"reporte_monstruo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.sidebar.caption("Analiza activos para habilitar reportes.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Calculadora P/L")
    investment_size = st.sidebar.number_input("Inversión (USDT)", min_value=10.0, value=1000.0, step=100.0)

    if st.sidebar.button("🗑️ Reset Stats"):
        st.session_state.hits = 0
        st.session_state.misses = 0
        st.session_state.total_input = 0
        st.session_state.total_output = 0
        save_stats(0, 0, 0, 0)
        st.rerun()

    # --- CORRELATION RADAR ---
    if st.session_state.market_overview:
        avg_corr = logic.get_market_correlation(st.session_state.market_overview)
        corr_color = "#00ff7f" if avg_corr > 0.7 else "#ffaa00" if avg_corr > 0.4 else "#ff4444"
        st.sidebar.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; border-left: 5px solid {corr_color}; margin-top:10px;">
                <div style="font-size:0.8em; color:#888;">RADAR DE CORRELACIÓN</div>
                <div style="font-size:1.2em; font-weight:bold; color:{corr_color};">{avg_corr:.2f}</div>
                <div style="font-size:0.7em; color:#666;">{'Mercado en Sincronía' if avg_corr > 0.7 else 'Movimiento Independiente'}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    auto_refresh = st.sidebar.checkbox("Auto-Actualizar 🔄", value=True)
    refresh_rate = st.sidebar.slider("Intervalo (segundos)", 30, 300, 60, step=10)
    
    # Track Last Update for the UI
    if 'last_update_ts' not in st.session_state:
        st.session_state.last_update_ts = "Nunca"

    if auto_refresh:
        refresh_count = st_autorefresh(interval=refresh_rate * 1000, key="data_refresh_v2")
        if 'prev_refresh_count' not in st.session_state: 
            st.session_state.prev_refresh_count = 0
        
        if refresh_count > st.session_state.prev_refresh_count:
            st.session_state.market_overview = None # Force reload
            st.session_state.prev_refresh_count = refresh_count

    st.sidebar.caption(f"⏱️ Actualización: cada {refresh_rate}s")
    st.sidebar.markdown(f"📅 **Último Carga:** `{st.session_state.last_update_ts}`")
    st.sidebar.markdown("Status: **Live** 🟢")

    # Helper for icons
    def get_asset_icon(symbol):
        icons = {
            "BTC": "₿", "ETH": "Ξ", "SOL": "◎", "BNB": "BNB",
            "EURUSD=X": "🇪🇺🇺🇸", "GBPUSD=X": "🇬🇧🇺🇸", "USDJPY=X": "🇺🇸🇯🇵",
            "AAPL": "🍎", "NVDA": "🔌", "TSLA": "🚗", "AMZN": "📦", "MSFT": "💻", "GOOGL": "🔍",
            "QQQ": "📊", "SPY": "🏦"
        }
        clean_symbol = symbol.replace("USDT", "")
        return icons.get(clean_symbol, "💰")

    # Function for Ticker
    def render_ticker(ticker_data):
        if not ticker_data: return
        
        ticker_html = '<div class="ticker-wrap"><div class="ticker">'
        for asset in ticker_data:
            symbol = asset['symbol'].replace("USDT", "")
            price = asset['price']
            change = asset['change']
            color = "#00ff7f" if change > 0 else "#ff4444"
            arrow = "▲" if change > 0 else "▼"
            ticker_html += f'<span class="ticker-item">{get_asset_icon(asset["symbol"])} {symbol}: <span style="color:white">${price:,.2f}</span> <span style="color:{color}">{arrow} {abs(change):.2f}%</span></span>'
        ticker_html += '</div></div>'
        st.html(ticker_html)

    # Main Content
    st.title("🚀 Monstruo Bursátil Dashboard")
    st.caption("AI-Powered Trading Signals | Real-Time Financial Indicators")

    # Connection Health Check
    if not logic.is_healthy():
        st.warning("⚠️ **Conexión con Binance Restringida**")
        with st.expander("🛠️ Panel de Diagnóstico"):
            tld_val = getattr(logic.ingestor, 'tld', 'N/A')
            sdk_val = getattr(logic.ingestor, 'sdk_ready', False)
            st.write(f"**Región (TLD):** `{tld_val}`")
            st.write(f"**SDK Binance:** `{'🟢 Conectado' if sdk_val else '🔴 Bloqueado'}`")
            
            # Test General Internet
            try:
                res = requests.get("https://www.google.com", timeout=3)
                st.write(f"**Internet General:** `🟢 OK` (Status: {res.status_code})")
            except Exception as e:
                st.write(f"**Internet General:** `🔴 FALLO` ({e})")

            if 'last_binance_error' in st.session_state:
                st.error(f"**Error Técnico Binance:** {st.session_state['last_binance_error']}")
            
            st.info("""
            **Guía de Solución:**
            1. Si el SDK está 🔴, es normal en la nube.
            2. Si el error es `HTTP 451`, Binance bloquea esta IP por ley.
            3. Prueba cambiar `BINANCE_TLD = "us"` por `"com"` (o viceversa) en los Secrets.
            """)
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 Re-conectar"):
                    st.session_state.market_overview = None
                    st.rerun()
            with col_b:
                if st.button("🧹 Limpiar Caché"):
                    st.cache_resource.clear()
                    st.rerun()

    # Render Ticker
    if st.session_state.ticker_data:
        render_ticker(st.session_state.ticker_data)

    # Static columns removed in favor of dynamic grid

    # Function to render asset card
    def render_asset_card(column, asset_data):
        with column:
            symbol = asset_data['symbol']
            price = float(asset_data['price'])
            change = float(asset_data['change_24h'])
            signal = asset_data.get("signal", "Yellow")
            
            # Style Signal
            signal_map = {
                "Green": ("🟢 COMPRAR", "#00ff7f", "rgba(0, 255, 127, 0.15)"),
                "Red": ("🔴 VENDER", "#ff4444", "rgba(255, 68, 68, 0.15)"),
                "Yellow": ("🟡 MANTENER", "#ffcc00", "rgba(255, 204, 0, 0.15)")
            }
            signal_text, signal_color, signal_bg = signal_map.get(signal, ("⚪...", "#aaa", "rgba(255,255,255,0.1)"))

            # Performance logic
            performance_html = ""
            if 'prediction_history' in st.session_state and symbol in st.session_state.prediction_history:
                prev = st.session_state.prediction_history[symbol]
                p_diff = ((price - prev['price']) / prev['price']) * 100
                hit = (prev['signal'] == "Green" and p_diff > 0.02) or (prev['signal'] == "Red" and p_diff < -0.02) or (prev['signal'] == "Yellow" and abs(p_diff) <= 0.02)
                
                perf_color = "#00ff7f" if hit else "#ff4444"
                pl_amount = (p_diff / 100) * investment_size
                
                performance_html = f"""
                    <div style="border: 1px solid {perf_color}55; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 15px; margin-top: 20px;">
                        <div style="font-size: 0.7em; color: #aaa;">RESULTADO PREVIO ({prev['signal']})</div>
                        <div style="display: flex; justify-content: space-between; margin-top: 5px; color: {perf_color}; font-weight: 700;">
                            <span>{p_diff:+.2f}%</span>
                            <span>P/L: {pl_amount:+.2f} USDT</span>
                        </div>
                    </div>
                """

            # Whale and MTF info
            whale_html = ""
            if asset_data.get('whale_alert'):
                whale_html = f"""
                    <div style="background: linear-gradient(90deg, #ff4b1f, #ff9068); color: white; padding: 5px 15px; border-radius: 10px; font-weight: 900; font-size: 0.8em; margin-bottom: 15px; text-align: center; border: 1px solid white;">
                        🚨 WHALE ACTIVITY: {asset_data.get('vol_anomaly', 0):.1f}x Vol!
                    </div>
                """
            
            # Order Book Walls
            wall_html = ""
            walls = asset_data.get('walls')
            if walls:
                if walls.get('buy_wall'):
                    wall_html += f'<div style="font-size:0.7em; color:#00ff7f; background:rgba(0,255,127,0.1); padding:2px 8px; border-radius:5px; margin-top:5px;">🛡️ BUY WALL: ${walls["buy_wall"]:,.2f}</div>'
                if walls.get('sell_wall'):
                    wall_html += f'<div style="font-size:0.7em; color:#ff4444; background:rgba(255,68,68,0.1); padding:2px 8px; border-radius:5px; margin-top:5px;">🚧 SELL WALL: ${walls["sell_wall"]:,.2f}</div>'

            mtf_html = ""
            if asset_data.get('mtf_summary'):
                mtf_badges = "".join([f'<span style="background:rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 5px; margin-right: 5px; font-size: 0.7em;">{tf}</span>' for tf in asset_data['mtf_summary']])
                mtf_html = f'<div style="margin-top: 10px;">{mtf_badges}</div>'

            # Performance logic
            card_html = textwrap.dedent(f"""
                <div class="glass-card">
                    {whale_html}
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 900; font-size: 1.5em;">{get_asset_icon(symbol)} {symbol.replace("USDT","")}</span>
                        <span style="color: {signal_color}; font-weight: 900;">{signal_text}</span>
                    </div>
                    <div style="font-size: 2.2em; font-weight: 900; margin: 10px 0;">${price:,.2f}</div>
                    <div style="color: {'#00ff7f' if change > 0 else '#ff4444'}; font-weight: 700;">{change:+.2f}% (24h)</div>
                    {mtf_html}
                    {wall_html}
                    {performance_html}
                    <div style="margin-top: 20px; font-size: 0.85em; color: #ddd;">"{asset_data['reasoning']}"</div>
                    <div style="margin-top: 10px; font-size: 0.8em; color: #888;">🎯 NIVELES: {asset_data['levels']}</div>
                </div>
            """).strip()
            st.html(card_html)
            
            # Interactive Timeframe Selection
            tf_key = f"tf_{symbol}"
            if tf_key not in st.session_state: st.session_state[tf_key] = "1h"
            
            selected_tf = st.radio(
                f"Timeframe {symbol}", 
                ["15m", "1h", "4h"], 
                index=["15m", "1h", "4h"].index(st.session_state[tf_key]),
                horizontal=True,
                key=f"radio_{symbol}",
                label_visibility="collapsed"
            )
            st.session_state[tf_key] = selected_tf

            # Display selected timeframe chart
            df = asset_data.get('mtf_data', {}).get(selected_tf, asset_data['history'])
            if not df.empty:
                fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
                fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{symbol}_{selected_tf}")

    # Asset Selection Constants
    default_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

    def load_data(symbols=None, source="Binance"):
        if not symbols: return []
        symbols = list(set(symbols))
        
        # Fetch Expanded Ticker Data (Fast, no AI) - Only for Binance
        if source == "Binance":
            st.session_state.ticker_data = logic.get_ticker_data(limit=15)
        
        if st.session_state.market_overview and source == "Binance":
            for asset in st.session_state.market_overview:
                symbol = asset.get('symbol')
                if not symbol: continue
                try:
                    new_price = float(asset['price'])
                    if symbol in st.session_state.prediction_history:
                        prev = st.session_state.prediction_history[symbol]
                        diff = ((new_price - prev['price']) / prev['price']) * 100
                        hit = (prev['signal'] == "Green" and diff > 0.05) or (prev['signal'] == "Red" and diff < -0.05) or (prev['signal'] == "Yellow" and abs(diff) <= 0.05)
                        if hit: st.session_state.hits += 1
                        else: st.session_state.misses += 1
                    st.session_state.prediction_history[symbol] = {"price": new_price, "signal": asset['signal']}
                except: pass

        try:
            with st.spinner(f"Analizando {len(symbols)} activos en {source}..."):
                new_data = logic.get_market_overview(specific_symbols=symbols, source=source)
                for asset in new_data:
                    usage = asset.get('usage', {})
                    if usage:
                        st.session_state.total_input += usage.get('prompt_tokens', 0)
                        st.session_state.total_output += usage.get('candidates_tokens', 0)
                
                # Update timestamp
                from datetime import datetime
                st.session_state.last_update_ts = datetime.now().strftime("%H:%M:%S")
                
                save_stats(st.session_state.hits, st.session_state.misses, st.session_state.total_input, st.session_state.total_output)
                return new_data
        except Exception as e:
            st.error(f"Error: {e}")
            return []

    # Initialize assets and selection based on market
    if market_source == "Binance":
        available_options = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT", "SHIBUSDT", "LTCUSDT", "NEARUSDT"]
        default_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT"]
    elif market_source == "Nasdaq":
        available_options = ["QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "AMD", "NFLX", "GOOG", "INTC", "PYPL", "CSCO"]
        default_assets = ["QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META"]
    elif market_source == "Forex":
        available_options = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X", "BTCUSD=X"]
        default_assets = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
    else: # SP500
        available_options = ["SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "JNJ", "V", "XOM", "TSM"]
        default_assets = ["SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

    selected_assets = st.sidebar.multiselect("Activos (Max 12)", available_options, default=default_assets[:8])
    if len(selected_assets) > 12: selected_assets = selected_assets[:12]

    # Handle source change or asset change
    if 'current_market_source' not in st.session_state: 
        st.session_state.current_market_source = market_source

    should_reload = False
    if market_source != st.session_state.current_market_source:
        st.session_state.current_market_source = market_source
        should_reload = True
    
    if selected_assets != st.session_state.last_selected_assets:
        st.session_state.last_selected_assets = selected_assets
        should_reload = True

    if st.session_state.market_overview is None or should_reload:
        st.session_state.market_overview = load_data(selected_assets, source=market_source)
        st.rerun()

    if st.button("Actualizar Análisis"):
        st.session_state.market_overview = load_data(selected_assets, source=market_source)
        st.rerun()

    # Render Cards in Dynamic Grid (3 columns per row)
    if st.session_state.market_overview:
        assets_to_render = st.session_state.market_overview[:12]
        for i in range(0, len(assets_to_render), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(assets_to_render):
                    render_asset_card(cols[j], assets_to_render[i+j])

    # News Section (Adaptive Grid)
    st.markdown("---")
    st.subheader("🗞️ Últimas Noticias de Impacto")
    if st.session_state.market_overview:
        assets_with_news = [a for a in st.session_state.market_overview if isinstance(a, dict) and a.get('news')]
        if assets_with_news:
            for i in range(0, len(assets_with_news), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i + j < len(assets_with_news):
                        row_asset = assets_with_news[i+j]
                        with cols[j]:
                            symbol_display = str(row_asset.get('symbol', '???')).replace('USDT','')
                            with st.expander(f"Noticias {symbol_display}", expanded=False):
                                asset_news = row_asset.get('news', [])
                                for n in asset_news:
                                    if not isinstance(n, dict): continue
                                    n_title = n.get('title', 'Sin título')
                                    n_url = n.get('url', '#')
                                    n_sentiment = n.get('sentiment', 'Neutral')
                                    st.markdown(f"🔹 **{n_title}**")
                                    st.caption(f"Sentiment: {n_sentiment} | [Link]({n_url})")
        else:
            st.write("No hay noticias recientes para los activos seleccionados.")
    
    # Footer
    st.markdown("---")
    st.markdown("Developed with ❤️ by Monstruo Bursátil Team using Google Gemini AI")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        st.error("🚨 Error Crítico")
        st.write("Hubo un fallo al iniciar la aplicación. Prueba reiniciar el servidor.")
        with st.expander("Ver detalles técnicos"):
            st.code(traceback.format_exc())
