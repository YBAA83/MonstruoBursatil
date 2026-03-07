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

    # Enhanced Futuristic glassmorphism CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&family=Inter:wght@300;400;700;900&display=swap');
        
        :root {
            --neon-green: #00ffbd;
            --neon-red: #ff3e3e;
            --neon-yellow: #ffcc00;
            --glass-bg: rgba(15, 15, 20, 0.7);
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        html, body { font-family: 'Inter', sans-serif; }
        h1, h2, h3, .stHeader, [data-testid="stHeader"] { font-family: 'Outfit', sans-serif !important; font-weight: 900; }
        
        /* Specific text targeting to avoid breaking icons */
        .stMarkdown p, .stText, .stCaption, label, [data-testid="stWidgetLabel"] p {
            font-family: 'Inter', sans-serif !important;
        }

        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 28px;
            color: white;
            margin-bottom: 25px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            position: relative;
            overflow: hidden;
        }
        .glass-card:hover {
            transform: translateY(-8px) scale(1.01);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }

        /* Signal Glows */
        .signal-green { box-shadow: 0 0 20px rgba(0, 255, 189, 0.15); border-left: 6px solid var(--neon-green); }
        .signal-red { box-shadow: 0 0 20px rgba(255, 62, 62, 0.15); border-left: 6px solid var(--neon-red); }
        .signal-yellow { box-shadow: 0 0 20px rgba(255, 204, 0, 0.1); border-left: 6px solid var(--neon-yellow); }

        /* Animations */
        @keyframes pulse-whale {
            0% { box-shadow: 0 0 0 0 rgba(255, 75, 31, 0.7); }
            70% { box-shadow: 0 0 0 15px rgba(255, 75, 31, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 75, 31, 0); }
        }
        .whale-badge {
            animation: pulse-whale 2s infinite;
            background: linear-gradient(90deg, #ff4b1f, #ff9068);
            color: white;
            padding: 6px 15px;
            border-radius: 12px;
            font-weight: 900;
            font-size: 0.75em;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        @keyframes slide-up {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-in { animation: slide-up 0.6s ease-out forwards; }

        /* Ticker refinement */
        .ticker-wrap {
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--glass-border);
            padding: 12px 0;
            margin-top: -30px;
        }

        /* Sidebar Expander Styling - NO FONT OVERRIDE ON SUMMARY */
        .stExpander {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 12px !important;
            margin-bottom: 15px !important;
        }
        
        /* High-end animation for cards */
        .animate-in {
            animation: slide-up 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize Logic
    # @st.cache_resource
    def get_logic(): return BusinessLogic()
    logic = get_logic()

    # CRITICAL: Ensure active_trades exists (Fix for AttributeError on reload)
    if not hasattr(logic.execution, "active_trades"):
        logic.execution.active_trades = {}

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
    
    # --- MARKET SELECTOR (Hardcoded to Binance) ---
    market_source = "Binance"
    # market_source = st.sidebar.radio("📚 Seleccionar Mercado", ["Binance", "Nasdaq", "Forex", "SP500"], horizontal=True)

    # --- VISION UPLOAD ---
    with st.sidebar.expander("ANALISTA VISUAL", expanded=False):
        st.markdown("<div style='font-size:0.8em; color:#888; margin-bottom:10px;'>Carga un gráfico para detección de patrones IA.</div>", unsafe_allow_html=True)
        uploaded_chart = st.file_uploader("Subir imagen", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        if uploaded_chart:
            st.image(uploaded_chart, caption="Gráfico Cargado", use_container_width=True)
            image_bytes = uploaded_chart.getvalue()
        else:
            image_bytes = None
    # --- 1% DAILY GOAL (Phase 13) ---
    st.sidebar.subheader("🎯 Meta Diaria (1%)")
    progress_val, current_pnl = logic.journal.get_progress_to_target()
    
    # Progress Bar with Neon Styling
    st.sidebar.markdown(f"""
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="font-size:0.8em; color:#888;">Progreso</span>
            <span style="font-weight:700; color:{'var(--neon-green)' if current_pnl >= 0 else 'var(--neon-red)'};">
                {current_pnl:+.2f}%
            </span>
        </div>
    """, unsafe_allow_html=True)
    st.sidebar.progress(progress_val / 100)
    
    if current_pnl >= 1.0:
        st.sidebar.success("🔥 ¡META CUMPLIDA!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 Configuración del Bot")
    
    bot_mode = st.sidebar.radio(
        "Modo de Ejecución",
        ["Simulación", "Cuenta Real"],
        index=0 if logic.execution.mode == "simulation" else 1,
        help="¡CUIDADO! La cuenta real ejecutará trades automáticamente si el Bot está activo."
    )
    
    # Update logic mode
    new_mode = "real" if bot_mode == "Cuenta Real" else "simulation"
    if new_mode != logic.execution.mode:
        logic.execution.set_mode(new_mode)
        st.sidebar.success(f"Modo: {new_mode.upper()}")

    st.session_state.bot_active = st.sidebar.toggle(
        "🔥 Activar Trading Autónomo",
        value=st.session_state.get('bot_active', False),
        help="Si se activa, el Monstruo ejecutará trades de alta confianza automáticamente."
    )
    
    if st.session_state.bot_active:
        st.sidebar.info("El Monstruo está AL ACECHO 🦖")
    else:
        st.sidebar.warning("Bot en modo PASIVO 💤")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡ Ejecución de Élite")
    
    trailing_dist = st.sidebar.slider(
        "Trailing Stop (%)",
        0.5, 5.0, 2.0, 0.5,
        help="Distancia que el Stop seguirá al precio. Recomendado: 2%."
    )
    
    partial_exit_enabled = st.sidebar.toggle(
        "Cierre Parcial (50% al 1%)",
        value=True,
        help="Vende la mitad de la posición automáticamente al alcanzar 1% de profit."
    )
    
    # Update active trades with these settings (simplified)
    # This keeps settings in sync with the UI
    for symbol in logic.execution.active_trades:
        logic.execution.active_trades[symbol]["trailing_dist_pct"] = trailing_dist / 100
    
    # Show Active Monitoring
    if logic.execution.active_trades:
        with st.sidebar.expander("👁️ Monitoreo Activo", expanded=True):
            for s, t in logic.execution.active_trades.items():
                st.markdown(f"**{s}** ({t['side']})")
                st.caption(f"Entrada: ${t['entry_price']:.2f}")
                if t.get('partial_exited'):
                    st.success("✅ Mitad Vendida (+1%)")
                else:
                    st.info("⏳ Esperando +1% Pnl")

    st.sidebar.markdown("---")

    # Stats Sections
    st.sidebar.subheader("📊 Marcador Histórico")
    col_h, col_m = st.sidebar.columns(2)
    
    with col_h:
        st.markdown(f"""
            <div style="background:rgba(0,255,189,0.05); padding:10px; border-radius:12px; border: 1px solid rgba(0,255,189,0.2); text-align:center;">
                <div style="font-size:0.7em; color:#888;">ACIERTOS</div>
                <div style="font-size:1.4em; font-weight:900; color:var(--neon-green);">{st.session_state.hits}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_m:
        st.markdown(f"""
            <div style="background:rgba(255,62,62,0.05); padding:10px; border-radius:12px; border: 1px solid rgba(255,62,62,0.2); text-align:center;">
                <div style="font-size:0.7em; color:#888;">FALLOS</div>
                <div style="font-size:1.4em; font-weight:900; color:var(--neon-red);">{st.session_state.misses}</div>
            </div>
        """, unsafe_allow_html=True)

    total_hist = st.session_state.hits + st.session_state.misses
    if total_hist > 0:
        winrate_hist = (st.session_state.hits / total_hist) * 100
        st.sidebar.markdown(f"<div style='margin-top:10px; font-size:0.8em; text-align:right; color:#888;'>Win Rate: {winrate_hist:.1f}%</div>", unsafe_allow_html=True)
        st.sidebar.progress(winrate_hist / 100)

    st.sidebar.markdown("---")
    st.sidebar.subheader("💎 Consumo de API")
    total_tokens = st.session_state.total_input + st.session_state.total_output
    cost_usd = (st.session_state.total_input / 1_000_000 * 0.10) + (st.session_state.total_output / 1_000_000 * 0.30)
    
    st.sidebar.markdown(f"""
        <div style="background:var(--glass-bg); padding:15px; border-radius:15px; border: 1px solid var(--glass-border);">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span style="color:#888; font-size:0.8em;">Tokens Total</span>
                <span style="font-weight:700;">{total_tokens:,}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#888; font-size:0.8em;">Coste Est.</span>
                <span style="color:var(--neon-green); font-weight:700;">${cost_usd:,.4f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

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

    st.sidebar.markdown("---")
    # --- LOG TRADE FORM ---
    with st.sidebar.expander("📝 REGISTRAR OPERACIÓN", expanded=False):
        with st.form("trade_form"):
            t_symbol = st.text_input("Símbolo", value="BTCUSDT")
            t_side = st.selectbox("Operación", ["BUY", "SELL"])
            t_entry = st.number_input("Precio Entrada", format="%.4f")
            t_exit = st.number_input("Precio Salida", format="%.4f")
            t_qty = st.number_input("Cantidad", format="%.4f")
            t_reason = st.text_area("Nota/Razón")
            if st.form_submit_button("Guardar en Bitácora"):
                logic.log_manual_trade(t_symbol, t_entry, t_exit, t_side, t_qty, t_reason)
                st.success("Trade guardado!")
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
            color = "var(--neon-green)" if change > 0 else "var(--neon-red)"
            arrow = "▲" if change > 0 else "▼"
            ticker_html += f'<span class="ticker-item" style="font-family:\'Outfit\';">{get_asset_icon(asset["symbol"])} {symbol}: <span style="color:white">${price:,.2f}</span> <span style="color:{color}; font-weight:900;">{arrow} {abs(change):.2f}%</span></span>'
        ticker_html += '</div></div>'
        st.html(ticker_html)

    # Main Content
    # Main Content Header
    st.markdown("""
        <div style="margin-bottom: 40px; text-align:center;">
            <h1 style="font-size: 3.5em; margin-bottom: 0px; background: linear-gradient(90deg, #fff, #888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Monstruo Bursátil</h1>
            <p style="color: #666; font-size: 1.1em; letter-spacing: 2px; text-transform: uppercase;">AI-Powered Terminal v2.0</p>
        </div>
    """, unsafe_allow_html=True)

    tab_radar, tab_backtest, tab_journal = st.tabs(["📡 Radar en Vivo", "🧪 Simulador (Backtest)", "📓 Diario de Trading"])

    with tab_radar:
        # Connection Health Check
        if not logic.is_healthy():
            st.markdown("""
                <div style="background:rgba(255,62,62,0.1); border:1px solid var(--neon-red); padding:15px; border-radius:15px; margin-bottom:20px;">
                    <div style="color:var(--neon-red); font-weight:900; font-family:'Outfit';">🚨 ESTADO CRÍTICO: CONEXIÓN RESTRINGIDA</div>
                    <div style="font-size:0.8em; color:#888;">Binance API unreachable or restricted. Switch to secondary markets or check proxy.</div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("🛠️ Tactical Diagnosis", expanded=False):
                tld_val = getattr(logic.ingestor, 'tld', 'N/A')
                sdk_val = getattr(logic.is_healthy(), 'sdk_ready', False)
                
                col_d1, col_d2 = st.columns(2)
                col_d1.markdown(f"**Region TLD**: `{tld_val}`")
                col_d2.markdown(f"**SDK Status**: `{'🟢 READY' if sdk_val else '🔴 ERROR'}`")
                
                if 'last_binance_error' in st.session_state:
                    st.error(f"Last Error: {st.session_state['last_binance_error']}")
                
                # Action Buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("🔄 Reload Core"): st.rerun()
                with btn_col2:
                    if st.button("🧹 Flush Cache"): st.cache_resource.clear(); st.rerun()

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
                "Green": ("🟢 COMPRAR", "var(--neon-green)", "signal-green"),
                "Red": ("🔴 VENDER", "var(--neon-red)", "signal-red"),
                "Yellow": ("🟡 MANTENER", "var(--neon-yellow)", "signal-yellow")
            }
            signal_text, signal_color, signal_class = signal_map.get(signal, ("⚪...", "#aaa", ""))

            # Performance logic
            performance_html = ""
            if 'prediction_history' in st.session_state and symbol in st.session_state.prediction_history:
                prev = st.session_state.prediction_history[symbol]
                p_diff = ((price - prev['price']) / prev['price']) * 100
                hit = (prev['signal'] == "Green" and p_diff > 0.02) or (prev['signal'] == "Red" and p_diff < -0.02) or (prev['signal'] == "Yellow" and abs(p_diff) <= 0.02)
                
                perf_color = "var(--neon-green)" if hit else "var(--neon-red)"
                pl_amount = (p_diff / 100) * investment_size
                
                performance_html = f"""
                    <div style="border: 1px solid {perf_color}44; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 18px; margin-top: 20px;">
                        <div style="font-size: 0.7em; color: #888; font-family: 'Outfit';">RESULTADO PREVIO ({prev['signal']})</div>
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
                    <div class="whale-badge" style="margin-bottom: 20px; text-align: center;">
                        🚨 WHALE ACTIVITY: {asset_data.get('vol_anomaly', 0):.1f}x Vol!
                    </div>
                """
            
            # Order Book Walls
            wall_html = ""
            walls = asset_data.get('walls')
            if walls:
                if walls.get('buy_wall'):
                    wall_html += f'<div style="font-size:0.7em; color:var(--neon-green); background:rgba(0,255,189,0.1); padding:4px 10px; border-radius:8px; margin-top:8px; font-family: \'Outfit\';">🛡️ BUY WALL: ${walls["buy_wall"]:,.2f}</div>'
                if walls.get('sell_wall'):
                    wall_html += f'<div style="font-size:0.7em; color:var(--neon-red); background:rgba(255,62,62,0.1); padding:4px 10px; border-radius:8px; margin-top:8px; font-family: \'Outfit\';">🚧 SELL WALL: ${walls["sell_wall"]:,.2f}</div>'

            mtf_html = ""
            if asset_data.get('mtf_summary'):
                mtf_badges = "".join([f'<span style="background:rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 8px; margin-right: 6px; font-size: 0.7em; font-family: \'Outfit\';">{tf}</span>' for tf in asset_data['mtf_summary']])
                mtf_html = f'<div style="margin-top: 15px;">{mtf_badges}</div>'

            # Build Card
            card_html = textwrap.dedent(f"""
                <div class="glass-card {signal_class} animate-in">
                    {whale_html}
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <span style="font-weight: 900; font-size: 1.6em; font-family: 'Outfit';">{get_asset_icon(symbol)} {symbol.replace("USDT","")}</span>
                        <span style="color: {signal_color}; font-weight: 900; font-size: 0.9em; letter-spacing: 1px;">{signal_text}</span>
                    </div>
                    <div style="font-size: 2.4em; font-weight: 900; margin: 15px 0; font-family: 'Outfit';">${price:,.2f}</div>
                    <div style="color: {'var(--neon-green)' if change > 0 else 'var(--neon-red)'}; font-weight: 700; font-size: 1.1em;">{change:+.2f}% <span style="font-size: 0.7em; font-weight: 400; color: #888;">(24h)</span></div>
                    {mtf_html}
                    {wall_html}
                    {performance_html}
                    <div style="margin-top: 25px; font-size: 0.9em; color: #ccc; line-height: 1.5; font-style: italic;">"{asset_data['reasoning']}"</div>
                    <div style="margin-top: 15px; font-size: 0.75em; color: #777; font-family: 'Outfit'; letter-spacing: 0.5px;">🎯 NIVELES CLAVE: {asset_data['levels']}</div>
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

    # Load Data Wrapper
    def load_data(symbols, chart_image=None):
        if not symbols: return []
        symbols = list(set(symbols))
        
        st.session_state.ticker_data = logic.get_ticker_data(limit=15)
        
        if st.session_state.market_overview:
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
            with st.spinner(f"Analizando {len(symbols)} activos..."):
                new_data = logic.get_market_overview(specific_symbols=symbols, image_bytes=chart_image)
                for asset in new_data:
                    usage = asset.get('usage', {})
                    if usage:
                        st.session_state.total_input += usage.get('prompt_tokens', 0)
                        st.session_state.total_output += usage.get('candidates_tokens', 0)
                
                # Update timestamp
                from datetime import datetime
                st.session_state.last_update_ts = datetime.now().strftime("%H:%M:%S")
                
                save_stats(st.session_state.hits, st.session_state.misses, st.session_state.total_input, st.session_state.total_output)
                
                # Trigger BOT if active (Autonomous Mode)
                if st.session_state.get('bot_active'):
                    for asset in new_data:
                        logic.trigger_automated_trade(asset)

                return new_data
        except Exception as e:
            st.error(f"Error: {e}")
            return []

    # Initialize assets (Binance Only)
    available_options = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT", "SHIBUSDT", "LTCUSDT", "NEARUSDT"]
    default_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT"]

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
        st.session_state.market_overview = load_data(selected_assets, chart_image=image_bytes)
        st.rerun()

    if st.button("Actualizar Análisis"):
        st.session_state.market_overview = load_data(selected_assets)
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
    st.subheader("📡 Feed de Inteligencia (Noticias)")
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
                            with st.expander(f"INTEL: {symbol_display}", expanded=False):
                                asset_news = row_asset.get('news', [])
                                for n in asset_news:
                                    if not isinstance(n, dict): continue
                                    n_title = n.get('title', 'Sin título')
                                    n_url = n.get('url', '#')
                                    n_sentiment = n.get('sentiment', 'Neutral')
                                    
                                    sent_color = "var(--neon-green)" if "Bull" in n_sentiment or "Positive" in n_sentiment else "var(--neon-red)" if "Bear" in n_sentiment or "Negative" in n_sentiment else "#888"
                                    
                                    st.markdown(f"""
                                        <div style="border-left: 3px solid {sent_color}; padding-left: 10px; margin-bottom: 12px; background:rgba(255,255,255,0.03); padding: 8px;">
                                            <div style="font-size:0.9em; font-weight:700;">{n_title}</div>
                                            <div style="font-size:0.7em; color:{sent_color}; font-family:'Outfit'; text-transform:uppercase; margin-top:4px;">Sentiment: {n_sentiment} | <a href="{n_url}" style="color:#555;">LINK</a></div>
                                        </div>
                                    """, unsafe_allow_html=True)
        else:
            st.write("No hay señales de inteligencia disponibles.")

    with tab_backtest:
        st.markdown("""
            <div style="background:var(--glass-bg); padding:30px; border-radius:24px; border:1px solid var(--glass-border); margin-bottom:30px;">
                <h2 style="margin-top:0; font-family:'Outfit'; color:var(--neon-green);">🧪 Simulador Táctico</h2>
                <p style="color:#888;">Simula el rendimiento de la IA en condiciones históricas de mercado.</p>
            </div>
        """, unsafe_allow_html=True)
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            bt_symbol = st.selectbox("Activo para Backtest", available_options, index=0)
        with col_b2:
            bt_days = st.slider("Días atrás", 1, 30, 7)
        with col_b3:
            bt_step = st.selectbox("Paso de Análisis (Velas)", [1, 2, 4, 8], index=2, help="Pasos más altos ahorran tokens.")

        if st.button("🚀 Iniciar Simulación"):
            with st.spinner(f"Simulando {bt_symbol} por {bt_days} días..."):
                results = logic.run_backtest(bt_symbol, days=bt_days, interval="1h")
                
                if "error" in results:
                    st.error(results["error"])
                else:
                    st.success("✅ Simulación Completada")
                    
                    # Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Win Rate", f"{results['win_rate']:.1f}%")
                    m2.metric("Profit Final", f"{results['profit_pct']:.2f}%")
                    m3.metric("Capital Final", f"${results['final_capital']:,.2f}")
                    m4.metric("Total Trades", results['total_trades'])
                    
                    # Equity Curve Chart
                    equity_df = pd.DataFrame(results['equity_curve'])
                    fig_equity = go.Figure()
                    fig_equity.add_trace(go.Scatter(x=equity_df['time'], y=equity_df['equity'], mode='lines', name='Equity Line', line=dict(color='#00ff7f', width=3)))
                    fig_equity.update_layout(title="📈 Curva de Equidad", template="plotly_dark", height=400)
                    st.plotly_chart(fig_equity, use_container_width=True)
                    
                    # Trade Log
                    with st.expander("📜 Registro de Operaciones"):
                        for t in results['trades']:
                            color = "#00ff7f" if "BUY" in t['type'] else "#ff4444"
                            st.markdown(f"""
                            <div style="border-left: 5px solid {color}; padding: 10px; margin-bottom: 5px; background: rgba(255,255,255,0.05);">
                                <b>{t['time']} - {t['type']}</b> | Precio: ${t['price']:,.2f} <br>
                                <span style="font-size:0.8em; color:#888;">{t['reason']}</span>
                            </div>
                            """, unsafe_allow_html=True)
    
    with tab_journal:
        st.markdown("""
            <div style="background:var(--glass-bg); padding:30px; border-radius:24px; border:1px solid var(--glass-border); margin-bottom:30px;">
                <h2 style="margin-top:0; font-family:'Outfit'; color:var(--neon-green);">📓 Diario de Trading</h2>
                <p style="color:#888;">Registro persistente de operaciones y rendimiento diario.</p>
            </div>
        """, unsafe_allow_html=True)

        # --- SNOWBALL PROJECTION CHART ---
        st.markdown("### 📈 Crecimiento Proyectado (Bola de Nieve)")
        strategy_info = logic.strategy.get_strategy_summary()
        
        # Generate data for the chart (next 30 days)
        from datetime import datetime, timedelta
        dates = []
        projected_vals = []
        for i in range(31):
            d = datetime.now() + timedelta(days=i)
            dates.append(d.strftime("%d/%m"))
            projected_vals.append(logic.strategy.get_projected_balance(d))
            
        chart_df = pd.DataFrame({
            "Fecha": dates,
            "USDT Proyectado": projected_vals
        })
        
        st.line_chart(chart_df.set_index("Fecha"), color="#00ffbd")
        
        cols_plan = st.columns(3)
        cols_plan[0].metric("Capital Proyectado Hoy", f"${strategy_info['projected_balance']:.2f}")
        cols_plan[1].metric("Aportación Mensual", f"$50.00")
        cols_plan[2].metric("Próxima Aportación", f"{strategy_info['next_contribution_days']} días")

        st.markdown("---")
        
        # --- PHASE 19: AI INTELLIGENCE ---
        st.markdown("### 🧠 Cerebro del Monstruo (Auto-Aprendizaje)")
        lessons = logic.intelligence.learned_lessons
        if not lessons:
             st.info("El Monstruo está observando... Aún no hay lecciones aprendidas.")
        else:
            for lesson in lessons:
                st.info(lesson)
        
        st.markdown("---")
        st.markdown("### 📜 Registros Recientes")
        recent_trades = logic.journal.get_recent_trades(20)
        if not recent_trades:
            st.info("Aún no hay trades registrados en la bitácora.")
        else:
            # Table Header
            st.markdown("""
                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr; background:rgba(255,255,255,0.05); padding:10px; border-radius:10px; font-weight:bold; font-size:0.9em; margin-bottom:10px;">
                    <div>Fecha</div>
                    <div>Símbolo</div>
                    <div>Lado</div>
                    <div>Entrada</div>
                    <div>Salida</div>
                    <div>P/L %</div>
                </div>
            """, unsafe_allow_html=True)
            
            for t in recent_trades:
                color = "var(--neon-green)" if t['pnl_pct'] > 0 else "var(--neon-red)"
                st.markdown(f"""
                    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr; padding:10px; border-bottom:1px solid rgba(255,255,255,0.03); font-size:0.85em;">
                        <div style="color:#888;">{t['timestamp']}</div>
                        <div style="font-weight:bold;">{t['symbol']}</div>
                        <div style="color:{'var(--neon-green)' if t['side']=='BUY' else 'var(--neon-red)'}; font-weight:700;">{t['side']}</div>
                        <div>${t['entry']:,.2f}</div>
                        <div>${t['exit']:,.2f}</div>
                        <div style="color:{color}; font-weight:bold;">{t['pnl_pct']:+.2f}%</div>
                    </div>
                """, unsafe_allow_html=True)

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
