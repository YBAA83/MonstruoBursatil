import os
import sys

# CRITICAL: Fix for "ModuleNotFoundError: No module named 'src'"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

import streamlit as st
import time
import pandas as pd
import plotly.graph_objects as go
from src.business_logic import BusinessLogic
from src.data_ingestion import BinanceDataIngestor
from src.stats_persistence import load_stats, save_stats

# Page Config
st.set_page_config(
    page_title="El Monstruo Bursátil",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
if 'last_selected_assets' not in st.session_state: st.session_state.last_selected_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

# Sidebar
st.sidebar.title("🚀 Monstruo Bursátil")
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

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto-Actualizar 🔄", value=True)
refresh_rate = st.sidebar.slider("Intervalo (segundos)", 30, 600, 180, step=30)

st.sidebar.markdown(f"Próxima actualización en: `{refresh_rate}`s")
st.sidebar.markdown("Status: **Live** 🟢")

# Helper for icons
def get_crypto_icon(symbol):
    icons = {"BTC": "₿", "ETH": "Ξ", "SOL": "◎", "BNB": "BNB"}
    return icons.get(symbol.replace("USDT", ""), "💰")

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
        ticker_html += f'<span class="ticker-item">{get_crypto_icon(asset["symbol"])} {symbol}: <span style="color:white">${price:,.2f}</span> <span style="color:{color}">{arrow} {abs(change):.2f}%</span></span>'
    ticker_html += '</div></div>'
    st.html(ticker_html)

# Main Content
st.title("🚀 Monstruo Bursátil Dashboard")
st.caption("AI-Powered Trading Signals | Real-Time Financial Indicators")

# Connection Health Check
if not logic.is_healthy():
    st.warning("⚠️ **Conexión con Binance Restringida**")
    st.info("""
    Parece que los servidores de Streamlit (USA) no pueden conectar con Binance Global. 
    **Para solucionarlo:**
    1. Ve a **'Manage app'** -> **'Settings'** -> **'Secrets'** en Streamlit Cloud.
    2. Añade esta línea: `BINANCE_TLD = "us"`
    3. Dale a **Save** y la app se reiniciará automáticamente.
    """)

# Render Ticker
if st.session_state.ticker_data:
    render_ticker(st.session_state.ticker_data)

col1, col2, col3, col4 = st.columns(4)

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

        import textwrap
        card_html = textwrap.dedent(f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: 900; font-size: 1.5em;">{get_crypto_icon(symbol)} {symbol.replace("USDT","")}</span>
                    <span style="color: {signal_color}; font-weight: 900;">{signal_text}</span>
                </div>
                <div style="font-size: 2.2em; font-weight: 900; margin: 10px 0;">${price:,.2f}</div>
                <div style="color: {'#00ff7f' if change > 0 else '#ff4444'}; font-weight: 700;">{change:+.2f}% (24h)</div>
                {performance_html}
                <div style="margin-top: 20px; font-size: 0.85em; color: #ddd;">"{asset_data['reasoning']}"</div>
                <div style="margin-top: 10px; font-size: 0.8em; color: #888;">🎯 NIVELES: {asset_data['levels']}</div>
            </div>
        """).strip()
        st.html(card_html)
        
        if 'history' in asset_data and not asset_data['history'].empty:
            df = asset_data['history']
            fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{symbol}_{int(time.time())}")

# Asset Selection Constants
default_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

def load_data(symbols=None):
    if not symbols: return []
    symbols = list(set(symbols))
    
    # Fetch Expanded Ticker Data (Fast, no AI)
    st.session_state.ticker_data = logic.get_ticker_data(limit=15)
    if st.session_state.market_overview:
        for asset in st.session_state.market_overview:
            symbol = asset['symbol']
            new_price = float(asset['price'])
            if symbol in st.session_state.prediction_history:
                prev = st.session_state.prediction_history[symbol]
                diff = ((new_price - prev['price']) / prev['price']) * 100
                hit = (prev['signal'] == "Green" and diff > 0.05) or (prev['signal'] == "Red" and diff < -0.05) or (prev['signal'] == "Yellow" and abs(diff) <= 0.05)
                if hit: st.session_state.hits += 1
                else: st.session_state.misses += 1
            st.session_state.prediction_history[symbol] = {"price": new_price, "signal": asset['signal']}
    try:
        with st.spinner(f"Analizando {len(symbols)} activos..."):
            new_data = logic.get_market_overview(specific_symbols=symbols)
            for asset in new_data:
                usage = asset.get('usage', {})
                if usage:
                    st.session_state.total_input += usage.get('prompt_tokens', 0)
                    st.session_state.total_output += usage.get('candidates_tokens', 0)
            save_stats(st.session_state.hits, st.session_state.misses, st.session_state.total_input, st.session_state.total_output)
            return new_data
    except Exception as e:
        st.error(f"Error: {e}")
        return []

# Initialize assets and selection
default_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
selected_assets = st.sidebar.multiselect("Activos (Max 4)", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"], default=default_assets)
if len(selected_assets) > 4: selected_assets = selected_assets[:4]

if selected_assets != st.session_state.last_selected_assets:
    st.session_state.market_overview = load_data(selected_assets)
    st.session_state.last_selected_assets = selected_assets
    st.rerun()

if st.session_state.market_overview is None:
    st.session_state.market_overview = load_data(selected_assets)

if st.button("Actualizar Análisis"):
    st.session_state.market_overview = load_data(selected_assets)
    st.rerun()

# Render Unique Cards
if st.session_state.market_overview:
    cols = [col1, col2, col3, col4]
    seen = set()
    rendered_count = 0
    for asset in st.session_state.market_overview:
        if asset['symbol'] not in seen and rendered_count < 4:
            render_asset_card(cols[rendered_count], asset)
            seen.add(asset['symbol'])
            rendered_count += 1

# News Section
st.markdown("---")
st.subheader("🗞️ Últimas Noticias de Impacto")
if st.session_state.market_overview:
    news_cols = st.columns(len(st.session_state.market_overview))
    for i, asset in enumerate(st.session_state.market_overview):
        if not isinstance(asset, dict): continue
        with news_cols[i]:
            symbol_display = asset.get('symbol', '???').replace('USDT','')
            with st.expander(f"Noticias {symbol_display}", expanded=True):
                news_list = asset.get('news', [])
                if news_list and isinstance(news_list, list):
                    for n in news_list:
                        if not isinstance(n, dict): continue
                        title = n.get('title', 'Sin título')
                        url = n.get('url', '#')
                        sentiment = n.get('sentiment', 'Neutral')
                        st.markdown(f"🔹 **{title}**")
                        st.caption(f"Sentiment: {sentiment} | [Link]({url})")
                else:
                    st.write("No hay noticias recientes para este activo.")

# Footer
st.markdown("---")
st.markdown("Developed with ❤️ by Monstruo Bursátil Team using Google Gemini AI")

# Auto-Refresh Logic
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
