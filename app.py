import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
try:
    import pandas_ta as ta
except ImportError:
    import pandas_ta as ta # Fallback or let it fail with clear error

from data_manager import DataManager
from ict_engine import ICTEngine
from backtester import Backtester
from charts import ChartVisualizer

st.set_page_config(layout="wide", page_title="ICT Quantitative Terminal", page_icon="📈")

# Custom CSS for UI/UX
st.markdown("""
<style>
    /* Metric Card Styling */
    [data-testid="stMetric"] {
        background-color: #1e222d;
        border: 1px solid #2b2b43;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stMetricValue"] {
        color: #2ecc71 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #d1d4dc !important;
    }
    
    /* Main Background */
    .stApp {
        background-color: #0b0e11;
    }
    
    /* Header Polish */
    h2, h3 {
        color: #f1f3f6 !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    
    /* Sidebar Polish */
    .css-1d391kg {
        background-color: #131722;
    }
    
    /* Button Polish */
    .stButton>button {
        width: 100%;
        background-color: #2962ff;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px;
        font-weight: 600;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #1e4bd8;
        box-shadow: 0 0 15px rgba(41, 98, 255, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Initialization
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'engine' not in st.session_state:
    st.session_state.engine = ICTEngine()
if 'chart_viz' not in st.session_state:
    st.session_state.chart_viz = ChartVisualizer()

# Sidebar
with st.sidebar:
    st.image("https://cryptologos.cc/logos/gold-standard-gst-logo.png", width=60)
    st.title("🎛️ Terminal Settings")
    
    with st.expander("📊 Market Selection", expanded=True):
        asset = st.selectbox("Symbol", ["Gold", "Nasdaq", "SP500"])
        timeframe = st.selectbox("Timeframe", ["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        chart_type = st.radio("Primary Interface", ["💹 TradingView Live (Recommended)", "🚀 Quantitative Analysis"], horizontal=True)
        
        # Dynamic period options based on timeframe
        if timeframe == "M1":
            period_options = ["1d", "3d", "7d"]
        elif timeframe in ["M5", "M15", "M30"]:
            period_options = ["7d", "30d", "60d"]
        else:
            period_options = ["60d", "6mo", "1y", "max"]
        
        period = st.selectbox("History Period", period_options)

    with st.expander("📈 Indicators (Context)", expanded=True):
        show_ema = st.checkbox("Show EMA 200 (Trend)", value=True)
        show_rsi = st.checkbox("Show RSI (Momentum)", value=False)
        
    with st.expander("🛡️ Risk Management", expanded=True):
        risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0) / 100
        trend_filter = st.checkbox("EMA 200 Trend Filter", value=False, help="Only Long above EMA 200, Only Short below.")
        show_rr_tool = st.checkbox("Show R:R Visual Tool", value=True)
        
    with st.expander("🧠 Strategy Legend", expanded=False):
        st.markdown("""
        | Element | Description |
        | :--- | :--- |
        | 🟡 **(S)** | Liquidity Sweep |
        | 🟢 **UP** | Bullish Entry |
        | 🔴 **DOWN** | Bearish Entry |
        | 🟪 **Zone** | Bullish FVG (Purple) |
        | 🟧 **Zone** | Bearish FVG (Orange) |
        | 🟩 **R:R** | Profit Target (1:2) |
        | 🟥 **R:R** | Stop Loss (1:1) |
        """)
        st.info("💡 Tip: Wait for the **Sweep (S)** inside a zone, then enter on the **Arrow** confirmation.")

    st.markdown("---")
    st.subheader("⚡ Terminal Execution")
    run_backtest = st.button("🚀 Run Backtest Engine")
    
    st.markdown("---")
    st.subheader("📡 Live Terminal")
    live_mode = st.toggle("Live Polling (60s)", value=False)
    if live_mode:
        st.info("🔄 Polling Market Every 60s...")
        time.sleep(60)
        st.rerun()

    st.markdown("---")
    st.caption("🚀 Data: Yahoo Finance (Real-time 1m for Futures)")
    st.caption("🕒 Timezone: UTC+1 (Central European Time)")
    st.caption("Powered by QuantDev Senior Lab")

# Main Page
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown(f"## 🏛️ {asset} Quantitative Terminal")
    st.markdown(f"**Asset:** {asset} | **Timeframe:** {timeframe} | **History:** {period}")
if col_status.button("ℹ️ Help"):
    st.info("""
    **The ICT Silver Bullet Strategy Logic:**
    1.  **Zone Creation:** Look for a 3-candle gap (FVG).
    2.  **Liquidity Hunt:** Wait for price to enter the FVG and form an internal high/low (ITH/ITL).
    3.  **The Sweep:** Look for price to sweep that extreme internal level.
    4.  **Confirmation:** Enter when price closes on the opposite side of the FVG (Inversion).
    """)

# 1. Fetch Data
@st.cache_data(ttl=3600, show_spinner="🛒 Sourcing Market Data...")
def load_data(asset, timeframe, period):
    # Fetch primary data
    df = st.session_state.data_manager.fetch_data(asset, timeframe, period)
    
    # Fetch HTF data for background analysis
    htf_data = {}
    if timeframe in ["M1", "M5"]:
        for tf in ["M15", "M30", "H1"]:
            htf_data[tf] = st.session_state.data_manager.fetch_data(asset, tf, period)
    elif timeframe == "M15":
        for tf in ["M30", "H1"]:
            htf_data[tf] = st.session_state.data_manager.fetch_data(asset, tf, period)
            
    return df, htf_data

df, htf_dfs = load_data(asset, timeframe, period)

if df is not None and not df.empty:
    # 1.5 Market Overview Header
    latest_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    price_change = float(latest_candle['Close'] - prev_candle['Close'])
    pct_change = (price_change / float(prev_candle['Close'])) * 100
    
    st.markdown("---")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Current Price", f"{latest_candle['Close']:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
    m_col2.metric("High (Session)", f"{df['High'].max():.2f}")
    m_col3.metric("Low (Session)", f"{df['Low'].min():.2f}")
    m_col4.metric("Volatility (Avg)", f"{(df['High'] - df['Low']).mean():.2f}")

    # ICT Status Banner
    ict_status = st.session_state.engine.get_current_status(df)
    st.info(f"⚡ **ICT Engine Status:** {ict_status}")

    # 2. Process ICT Logic
    df_with_fvgs = st.session_state.engine.find_fvgs(df)
    
    # 2.2 Process TA Context Indicators
    if show_ema:
        df['ema_200'] = ta.ema(df['Close'], length=200)
    if show_rsi:
        df['rsi'] = ta.rsi(df['Close'], length=14)
    
    # 2.5 Process HTF FVGs
    htf_fvgs_dict = {}
    for tf, hdf in htf_dfs.items():
        if not hdf.empty:
            htf_fvgs_dict[tf] = st.session_state.engine.find_fvgs(hdf)

    # 3. Detect Signal Chain (FVG -> Internal Fractal -> Sweep -> iFVG)
    all_signals = []
    markers = []
    
    # Analyze all detected FVGs for current timeframe
    active_fvgs = df_with_fvgs[df_with_fvgs['fvg_type'] != 0]
    
    for idx, row in active_fvgs.iterrows():
        fvg_idx = df.index.get_loc(idx)
        top = row['fvg_top']
        bottom = row['fvg_bottom']
        fvg_type = row['fvg_type']
        
        # Use Consolidated Signal Detection
        signal = st.session_state.engine.get_consolidated_signals(
            df, fvg_idx, top, bottom, fvg_type
        )
        
        if signal:
            # Trend Filter Logic
            is_valid = True
            if trend_filter and 'ema_200' in df.columns:
                ema_val = df.iloc[signal['entry_index']]['ema_200']
                if not pd.isna(ema_val):
                    if fvg_type == -1 and df.iloc[signal['entry_index']]['Close'] < ema_val: # Long Entry
                        is_valid = False
                    elif fvg_type == 1 and df.iloc[signal['entry_index']]['Close'] > ema_val: # Short Entry
                        is_valid = False
            
            if is_valid:
                # 1. Add Marker for the Sweep
                markers.append({
                    "time": int(df.index[signal['sweep_index']].timestamp()),
                    "position": "aboveBar" if fvg_type == -1 else "belowBar",
                    "color": "#f1c40f",
                    "shape": "circle",
                    "text": "S"
                })
                
                # 2. Add Marker for the Entry
                markers.append({
                    "time": int(df.index[signal['entry_index']].timestamp()),
                    "position": "belowBar" if fvg_type == -1 else "aboveBar",
                    "color": "#2ecc71" if fvg_type == -1 else "#e74c3c",
                    "shape": "arrowUp" if fvg_type == -1 else "arrowDown",
                    "text": "iFVG Entry"
                })
                
                # 3. Add to Signal List for Backtester
                all_signals.append({
                    'entry_index': signal['entry_index'],
                    'sl_price': signal['sl_price'],
                    'fvg_type': fvg_type,
                    'asset': asset
                })

    # 4. Results Display
    if run_backtest:
        with st.spinner("🧠 Calculating Backtest Statistics..."):
            bt = Backtester(risk_per_trade=risk_pct)
            bt.run_backtest(df, all_signals)
            stats = bt.get_stats()
            st.session_state.last_bt_trades = bt.trades
            
            if stats:
                st.markdown("---")
                st.subheader("📊 Performance Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Win Rate", f"{stats['win_rate']:.1%}", help="Percent of profitable trades.")
                col2.metric("Profit Factor", f"{stats['profit_factor']:.2f}", help="Gross Profit / Gross Loss.")
                col3.metric("Max Drawdown", f"{stats['max_drawdown']:.1%}", help="Deepest equity dip.")
                col4.metric("Sharpe Ratio", f"{stats['sharpe']:.2f}", help="Risk-adjusted return.")
                
                col5, col6, col7, col8 = st.columns(4)
                col5.metric("Avg Win ($)", f"{stats['avg_win']:.2f}")
                col6.metric("Avg Loss ($)", f"{stats['avg_loss']:.2f}")
                col7.metric("Total P/L ($)", f"{stats['final_balance'] - bt.initial_balance:+.2f}")
                col8.metric("Total Trades", stats['total_trades'])
                
                # Plot Equity Curve with better styling
                st.subheader("📉 Equity Performance")
                equity_df = pd.DataFrame({"Equity": bt.equity_curve})
                st.area_chart(equity_df, color="#2ecc71")
                
                # Trade History with search/filter
                with st.expander("📖 Detailed Trade Journal"):
                    trades_df = pd.DataFrame(bt.trades)
                    if not trades_df.empty:
                        # Clean up DataFrame for display
                        trades_df['entry_time'] = trades_df['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
                        trades_df['exit_time'] = trades_df['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
                        # Rename columns for clarity
                        trades_df = trades_df.rename(columns={
                            'entry_time': '📅 Entry Time',
                            'entry_price': '💵 Entry Price',
                            'sl_price': '🛑 Stop Loss',
                            'tp_price': '🎯 Take Profit',
                            'profit': '💰 Profit/Loss ($)',
                            'outcome': '🏆 Outcome'
                        })
                        # Display table with formatting
                        st.dataframe(trades_df.style.map(
                            lambda x: 'color: #2ecc71' if x == 'TP' else ('color: #e74c3c' if x == 'SL' else ''),
                            subset=['🏆 Outcome']
                        ), use_container_width=True)
            else:
                st.info("⚠️ No valid ICT signals found for the current configuration.")

    # 5. Render Chart Layout
    st.markdown("---")
    
    if "TradingView" in chart_type:
        st.subheader(f"💹 Live {asset} Analysis Feed")
        
        # Dual-column layout: TradingView on left, Quantitative Signals on right
        tv_col, signal_col = st.columns([3, 1])
        
        with tv_col:
            tv_symbol = "OANDA:XAUUSD" if asset == "Gold" else ("NASDAQ:NDX" if asset == "Nasdaq" else "CME_MINI:ES1!")
            tv_html = f"""
            <div class="tradingview-widget-container" style="height:650px;width:100%">
              <div id="tradingview_12345" style="height:100%;width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget({{
                "autosize": true,
                "symbol": "{tv_symbol}",
                "interval": "{'1' if timeframe == 'M1' else ('5' if timeframe == 'M5' else ('15' if timeframe == 'M15' else ('30' if timeframe == 'M30' else ('60' if timeframe == 'H1' else ('240' if timeframe == 'H4' else 'D')))))}",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "withdateranges": true,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "details": true,
                "hotlist": true,
                "calendar": true,
                "container_id": "tradingview_12345"
              }});
              </script>
            </div>
            """
            components.html(tv_html, height=650)
            
        with signal_col:
            st.markdown("### 🎯 ICT Live Signals")
            st.caption("Auto-detected via Quant Engine")
            
            # Display signals in high-clarity cards
            if all_signals:
                for sig in all_signals[-5:][::-1]: # Show last 5
                    with st.container():
                        st.markdown(f"""
                        <div style="background-color: #1e222d; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid {'#2ecc71' if sig['fvg_type'] == -1 else '#e74c3c'}">
                            <h4 style="margin: 0; color: white;">{'BULLISH' if sig['fvg_type'] == -1 else 'BEARISH'}</h4>
                            <p style="margin: 5px 0; font-size: 0.9em; color: #d1d4dc;">
                                <b>Entry:</b> {df.iloc[sig['entry_index']]['Close']:.2f}<br>
                                <b>SL:</b> {sig['sl_price']:.2f}<br>
                                <b>Time:</b> {df.index[sig['entry_index']].strftime('%H:%M')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Searching for setups...")
                st.caption("Waiting for FVG -> Sweep -> Inversion sequence.")

    else:
        st.subheader("🚀 High-Fidelity Quantitative Terminal")
        
        # Time offset for UTC+1
        time_offset = 3600
        candles = st.session_state.chart_viz.prepare_candles(df, time_offset=time_offset)
        
        # Sync markers
        chart_markers = []
        for m in markers:
            m_copy = m.copy()
            m_copy['time'] = m_copy['time'] + time_offset
            chart_markers.append(m_copy)
            
        extra_series = []
        
        # 1. HTF FVGs
        for tf, hdf_fvgs in htf_fvgs_dict.items():
            recent_htf = hdf_fvgs[hdf_fvgs['fvg_type'] != 0].tail(3)
            for h_idx, h_fvg in recent_htf.iterrows():
                h_start, h_end = int(h_idx.timestamp()) + time_offset, int(df.index[-1].timestamp()) + time_offset
                h_color = "rgba(155, 89, 182, 0.1)" if h_fvg['fvg_type'] == 1 else "rgba(243, 156, 18, 0.1)"
                h_border = "rgba(155, 89, 182, 0.3)" if h_fvg['fvg_type'] == 1 else "rgba(243, 156, 18, 0.3)"
                extra_series.append({
                    "type": "Baseline",
                    "data": [{"time": h_start, "value": float(h_fvg['fvg_top'])}, {"time": h_end, "value": float(h_fvg['fvg_top'])}],
                    "options": {
                        "baseValue": {"type": "price", "price": float(h_fvg['fvg_bottom'])},
                        "topFillColor1": h_color, "topFillColor2": h_color,
                        "topLineColor": h_border, "bottomLineColor": h_border,
                        "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False
                    }
                })

        # 2. LTF FVGs
        for idx, fvg in active_fvgs.tail(10).iterrows():
            start_t, end_t = int(idx.timestamp()) + time_offset, int(df.index[-1].timestamp()) + time_offset
            color = "rgba(155, 89, 182, 0.2)" if fvg['fvg_type'] == 1 else "rgba(243, 156, 18, 0.2)"
            border = "rgba(155, 89, 182, 0.4)" if fvg['fvg_type'] == 1 else "rgba(243, 156, 18, 0.4)"
            extra_series.append({
                "type": "Baseline",
                "data": [{"time": start_t, "value": float(fvg['fvg_top'])}, {"time": end_t, "value": float(fvg['fvg_top'])}],
                "options": {
                    "baseValue": {"type": "price", "price": float(fvg['fvg_bottom'])},
                    "topFillColor1": color, "topFillColor2": color,
                    "topLineColor": border, "bottomLineColor": border,
                    "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False
                }
            })

        # 3. R:R Tool
        if show_rr_tool and 'last_bt_trades' in st.session_state:
            for trade in st.session_state.last_bt_trades[-10:]:
                t_e, t_x = int(trade['entry_time'].timestamp()) + time_offset, int(trade['exit_time'].timestamp()) + time_offset
                if trade['entry_time'] not in df.index: continue
                e_p, sl_p, tp_p, is_l = float(trade['entry_price']), float(trade['sl_price']), float(trade['tp_price']), trade['fvg_type'] == -1
                
                chart_markers.append({"time": t_x, "position": "aboveBar" if trade['outcome']=='TP' else "belowBar", 
                                "color": "#26a69a" if trade['outcome']=='TP' else "#ef5350", "shape": "star", "text": f"R:R {trade['outcome']}"})
                
                tr_mask = (df.index >= trade['entry_time']) & (df.index <= trade['exit_time'])
                tr_slc = df[tr_mask]
                tp_pts = [{"time": int(t.timestamp()) + time_offset, "value": tp_p} for t in tr_slc.index]
                sl_pts = [{"time": int(t.timestamp()) + time_offset, "value": sl_p} for t in tr_slc.index]

                extra_series.append({
                    "type": "Baseline", "data": tp_pts,
                    "options": {
                        "baseValue": {"type": "price", "price": e_p},
                        "topFillColor1": "rgba(38, 166, 154, 0.3)" if is_l else "transparent",
                        "topFillColor2": "rgba(38, 166, 154, 0.05)" if is_l else "transparent",
                        "bottomFillColor1": "transparent" if is_l else "rgba(38, 166, 154, 0.3)",
                        "bottomFillColor2": "transparent" if is_l else "rgba(38, 166, 154, 0.05)",
                        "topLineColor": "rgba(38, 166, 154, 0.8)", "bottomLineColor": "rgba(38, 166, 154, 0.8)",
                        "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False
                    }
                })
                extra_series.append({
                    "type": "Baseline", "data": sl_pts,
                    "options": {
                        "baseValue": {"type": "price", "price": e_p},
                        "topFillColor1": "transparent" if is_l else "rgba(239, 83, 80, 0.3)",
                        "topFillColor2": "transparent" if is_l else "rgba(239, 83, 80, 0.05)",
                        "bottomFillColor1": "rgba(239, 83, 80, 0.3)" if is_l else "transparent",
                        "bottomFillColor2": "rgba(239, 83, 80, 0.05)" if is_l else "transparent",
                        "topLineColor": "rgba(239, 83, 80, 0.8)", "bottomLineColor": "rgba(239, 83, 80, 0.8)",
                        "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False
                    }
                })

        # Indicators
        if show_ema and 'ema_200' in df.columns:
            extra_series.append({"type": "Line", "data": [{"time": int(t.timestamp()) + time_offset, "value": float(v)} for t, v in df['ema_200'].dropna().items()], "options": {"color": "#f1c40f", "lineWidth": 2, "title": "EMA 200"}})
        
        rsi_s = [{"time": int(t.timestamp()) + time_offset, "value": float(v)} for t, v in df['rsi'].dropna().items()] if show_rsi and 'rsi' in df.columns else None
        st.session_state.chart_viz.render(candles, series_data=extra_series, markers=chart_markers, rsi_data=rsi_s, key='main_chart')


else:
    st.warning("No data found for the selected asset/timeframe.")
