import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor
try:
    import pandas_ta as ta
except ImportError:
    import pandas_ta as ta # Fallback or let it fail with clear error

from data_manager import DataManager
from ict_engine import ICTEngine
from backtester import Backtester
from charts import ChartVisualizer

# Robust JSON serializer for Chart Data (Prevents NaN crashes)
def safe_json_serialize(obj):
    if isinstance(obj, list):
        return [safe_json_serialize(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (float, int, np.number)):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    else:
        return obj

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
        
        # Default to Quantitative view since that's where the value is
        chart_type = st.radio("Primary Interface", ["🚀 Quantitative Analysis (Backtest View)", "💹 TradingView Live"], index=0, horizontal=True)
        
        # Dynamic period options based on timeframe
        if timeframe == "M1":
            period_options = ["7d", "1d", "3d"] # Default to 7d for M1
        elif timeframe in ["M5", "M15", "M30"]:
            period_options = ["30d", "7d", "60d"] # Default to 30d
        else:
            period_options = ["60d", "6mo", "1y", "max"]
        
        period = st.selectbox("History Period", period_options)

    with st.expander("🛡️ Risk Management", expanded=True):
        risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0) / 100
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

    st.markdown("---")
    with st.expander("🛠️ System Diagnostics", expanded=False):
        if 'diagnostics' in st.session_state:
            for d in st.session_state.diagnostics[-10:]:
                st.caption(f"⏱️ {d}")
        if st.button("Clear Diagnostics"):
            st.session_state.diagnostics = []
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

@st.cache_data(ttl=3600, show_spinner="🛒 Sourcing Market Data...")
def load_data(asset, timeframe, period):
    start_time = time.time()
    # Fetch primary data
    print(f"[DIAGNOSTIC] Fetching primary data: {asset} {timeframe} ({period})")
    df = st.session_state.data_manager.fetch_data(asset, timeframe, period)
    
    # Fetch HTF data + ALWAYS fetch M1 for execution signals
    htf_data = {}
    target_tfs = ["M1"] # Always include M1
    
    if timeframe == "M1":
        target_tfs = ["M5", "M15", "M30", "H1"]
    elif timeframe == "M5":
        target_tfs = ["M1", "M15", "M30", "H1"]
    elif timeframe == "M15":
        target_tfs = ["M1", "M30", "H1"]
    elif timeframe in ["M30", "H1"]:
        target_tfs = ["M1", "H1" if timeframe == "M30" else "M30"]
    
    # Remove current timeframe from background targets
    target_tfs = [t for t in target_tfs if t != timeframe]
    
    if target_tfs:
        print(f"[DIAGNOSTIC] Fetching background data in parallel: {target_tfs}")
        with ThreadPoolExecutor(max_workers=len(target_tfs)) as executor:
            future_to_tf = {executor.submit(st.session_state.data_manager.fetch_data, asset, tf, period): tf for tf in target_tfs}
            for future in future_to_tf:
                tf = future_to_tf[future]
                try:
                    htf_data[tf] = future.result(timeout=30)
                except Exception as e:
                    print(f"[DIAGNOSTIC] Timeout or Error fetching {tf}: {e}")
                    htf_data[tf] = pd.DataFrame()
    
    end_time = time.time()
    msg = f"Data Loading took {end_time - start_time:.2f}s for {asset} {timeframe}"
    if 'diagnostics' not in st.session_state: st.session_state.diagnostics = []
    st.session_state.diagnostics.append(msg)
    return df, htf_data

@st.cache_data(ttl=600, show_spinner="🧠 Analyzing MTF Signals...")
def compute_cached_signals(asset, timeframe, _df, _htf_dfs):
    start_time = time.time()
    res = st.session_state.engine.compute_mtf_signals(_df, _htf_dfs, timeframe)
    end_time = time.time()
    msg = f"MTF Signal Analysis took {end_time - start_time:.2f}s"
    if 'diagnostics' not in st.session_state: st.session_state.diagnostics = []
    st.session_state.diagnostics.append(msg)
    print(f"[DIAGNOSTIC] {msg}")
    return res

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
    
    # 2.5 Process HTF FVGs
    htf_fvgs_dict = {}
    for tf, hdf in htf_dfs.items():
        if not hdf.empty:
            htf_fvgs_dict[tf] = st.session_state.engine.find_fvgs(hdf)

    # 3. Detect Signal Chain (HTF Sweep -> M1 iFVG Entry)
    all_signals = []
    markers = []
    extra_series = []
    time_offset = 3600 # UTC+1
    end_t = int(df.index[-1].timestamp()) + time_offset

    # Session Boxes (As background shading - Moved to Left Scale to fix zooming)
    sessions = st.session_state.engine.get_sessions(df)
    y_min, y_max = float(df['Low'].min()), float(df['High'].max())
    for sess in sessions:
        sess_start = int(sess['start'].timestamp()) + time_offset
        sess_end = int(sess['end'].timestamp()) + time_offset
        extra_series.append({
            "type": "Baseline",
            "data": [{"time": sess_start, "value": y_max}, {"time": sess_end, "value": y_max}],
            "options": {
                "baseValue": {"type": "price", "price": y_min},
                "topFillColor1": sess['color'], "topFillColor2": sess['color'],
                "lineWidth": 0, "priceLineVisible": False, "lastValueVisible": False,
                "priceScaleId": "left" # IMPORTANT: Prevents squashing the main price scale
            }
        })

    # Use optimized and cached signal engine
    mtf_results = compute_cached_signals(asset, timeframe, df, htf_dfs)
    global_entries = mtf_results['global_entries']
    htf_levels = mtf_results['htf_levels']

    # 3.1 Plot Levels (HTF + Primary)
    # Filter for alerts: Current day, Current TF, London Open to NY Close
    ith_itl_alerts = []
    current_day = df.index[-1].date()
    
    for level in htf_levels:
        if pd.isna(level['price']): continue
        
        is_p = level.get('is_primary', False)
        
        # Draw level line if within 7 days
        if level['time'] > df.index[-1] - pd.Timedelta(days=7):
            color = "rgba(155, 89, 182, 0.9)" if level['type'] == 'ITH' else "rgba(52, 152, 219, 0.9)"
            if not is_p: # HTF levels are slightly more transparent
                color = color.replace("0.9", "0.4")
                
            extra_series.append({
                "type": "Line",
                "data": [
                    {"time": int(level['time'].timestamp()) + time_offset, "value": float(level['price'])},
                    {"time": end_t, "value": float(level['price'])}
                ],
                "options": {
                    "color": color,
                    "lineWidth": 2 if is_p else 1, 
                    "lineStyle": 0 if is_p else 2, 
                    "title": f"{level['tf']} {level['type']}"
                }
            })
            
        # Collect alerts for primary TF, current day, and London-NY window
        if is_p and level['time'].date() == current_day:
            hour = level['time'].hour
            if 7 <= hour < 20: # London Open (7) to NY Close (20)
                ith_itl_alerts.append(level)

    # 3.2 Plot Global Entries on Current Chart (Session Only)
    for entry in global_entries:
        if entry['time'] >= df.index[0] and entry['time'] <= df.index[-1]:
            # Session Filter: London Open (7) to NY Close (20)
            hour = entry['time'].hour
            is_in_session = 7 <= hour < 20
            
            if is_in_session:
                try:
                    # Find the corresponding candle on the CURRENT timeframe (M1, M5, M15, etc)
                    # method='pad' ensures we pick the HTF candle that contains this M1 signal
                    idx_pos = df.index.get_indexer([entry['time']], method='pad')[0]
                    if idx_pos == -1: continue
                    
                    all_signals.append({
                        'entry_index': idx_pos,
                        'sl_price': df.iloc[idx_pos]['Low'] if entry['type'] == 'LONG' else df.iloc[idx_pos]['High'],
                        'fvg_type': -1 if entry['type'] == 'LONG' else 1,
                        'asset': asset
                    })
                    
                    # Align marker time to the actual chart timestamp
                    aligned_time = int(df.index[idx_pos].timestamp()) + time_offset
                    
                    markers.append({
                        "time": aligned_time,
                        "position": "belowBar" if entry['type'] == 'LONG' else "aboveBar",
                        "color": "#2ecc71" if entry['type'] == 'LONG' else "#e74c3c",
                        "shape": "arrowUp" if entry['type'] == 'LONG' else "arrowDown",
                        "text": f"{entry['type']} ENTRY",
                        "size": 2 # Make arrows larger
                    })
                except: pass

    # 3.3 FVG Rendering (Selected TF Only)
    active_fvgs = df_with_fvgs[df_with_fvgs['fvg_type'].isin([1, -1])].tail(5)
    for idx, row in active_fvgs.iterrows():
        # Safety check: skip if levels are NaN
        if pd.isna(row['fvg_top']) or pd.isna(row['fvg_bottom']):
            continue
            
        start_t = int(idx.timestamp()) + time_offset
        color = "rgba(155, 89, 182, 0.1)" if row['fvg_type'] == 1 else "rgba(243, 156, 18, 0.1)"
        extra_series.append({
            "type": "Baseline",
            "data": [{"time": start_t, "value": float(row['fvg_top'])}, {"time": end_t, "value": float(row['fvg_top'])}],
            "options": {
                "baseValue": {"type": "price", "price": float(row['fvg_bottom'])},
                "topFillColor1": color, "topFillColor2": color,
                "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False
            }
        })

    # 4. Results Display (Old logic follows...)

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
            st.info("💡 Note: ICT Logic (FVGs, Sweeps, R:R Tools) are only visible in the '🚀 Quantitative Analysis' tab.")
            # Use TradingView Official Symbol for Gold
            tv_symbol = "TVC:GOLD" if asset == "Gold" else ("NASDAQ:NDX" if asset == "Nasdaq" else "CME_MINI:ES1!")
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
                "container_id": "tradingview_12345"
              }});
              </script>
            </div>
            """
            components.html(tv_html, height=650)
            
        with signal_col:
            st.markdown("### 🔔 ITH/ITL Alerts")
            st.caption(f"Current TF: {timeframe} | Session Only")
            
            if ith_itl_alerts:
                for alt in ith_itl_alerts[-5:][::-1]: # Show last 5
                    with st.container():
                        st.markdown(f"""
                        <div style="background-color: #1e222d; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid {'#9b59b6' if alt['type'] == 'ITH' else '#3498db'}">
                            <p style="margin: 0; font-size: 0.85em; color: {'#9b59b6' if alt['type'] == 'ITH' else '#3498db'}; font-weight: bold;">{alt['type']} DETECTED</p>
                            <p style="margin: 2px 0; font-size: 1.1em; color: white; font-weight: bold;">{alt['price']:.2f}</p>
                            <p style="margin: 0; font-size: 0.75em; color: #d1d4dc;">{alt['time'].strftime('%H:%M')} | {alt['tf']}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No session levels detected for today.")

            st.markdown("---")
            st.markdown("### 🎯 ICT Entry Signals")
            st.caption("Auto-detected via Quant Engine")
            
            if all_signals:
                for sig in all_signals[-5:][::-1]:
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

    if "Quantitative" in chart_type:
        st.subheader("🚀 High-Fidelity Quantitative Terminal")
        
        start_prep = time.time()
        candles = st.session_state.chart_viz.prepare_candles(df, time_offset=time_offset)
        
        if show_rr_tool and 'last_bt_trades' in st.session_state:
            for trade in st.session_state.last_bt_trades[-10:]:
                t_e, t_x = int(trade['entry_time'].timestamp()) + time_offset, int(trade['exit_time'].timestamp()) + time_offset
                if trade['entry_time'] not in df.index: continue
                e_p, sl_p, tp_p, is_l = float(trade['entry_price']), float(trade['sl_price']), float(trade['tp_price']), trade['fvg_type'] == -1
                
                # Markers on all timeframes
                markers.append({"time": t_x, "position": "aboveBar" if trade['outcome']=='TP' else "belowBar", 
                                "color": "#26a69a" if trade['outcome']=='TP' else "#ef5350", "shape": "star", "text": f"R:R {trade['outcome']}"})
                
                tr_mask = (df.index >= trade['entry_time']) & (df.index <= trade['exit_time'])
                tr_slc = df[tr_mask]
                tp_pts = [{"time": int(t.timestamp()) + time_offset, "value": float(tp_p)} for t in tr_slc.index]
                sl_pts = [{"time": int(t.timestamp()) + time_offset, "value": float(sl_p)} for t in tr_slc.index]

                extra_series.append({
                    "type": "Baseline", "data": tp_pts,
                    "options": {
                        "baseValue": {"type": "price", "price": float(e_p)},
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
                        "baseValue": {"type": "price", "price": float(e_p)},
                        "topFillColor1": "transparent" if is_l else "rgba(239, 83, 80, 0.3)",
                        "topFillColor2": "transparent" if is_l else "rgba(239, 83, 80, 0.05)",
                        "bottomFillColor1": "rgba(239, 83, 80, 0.3)" if is_l else "transparent",
                        "bottomFillColor2": "rgba(239, 83, 80, 0.05)" if is_l else "transparent",
                        "topLineColor": "rgba(239, 83, 80, 0.8)", "bottomLineColor": "rgba(239, 83, 80, 0.8)",
                        "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False
                    }
                })

        # Final Sanitization & Single Render
        clean_candles = safe_json_serialize(candles)
        clean_series = safe_json_serialize(extra_series)
        clean_markers = safe_json_serialize(markers)
        
        try:
            st.session_state.chart_viz.render(clean_candles, series_data=clean_series, markers=clean_markers, key=f"chart_{timeframe}_{asset}_{period}")
        except Exception as e:
            st.error(f"⚠️ Chart Rendering Error: {e}")
            st.session_state.chart_viz.render(clean_candles, markers=clean_markers, key=f"fallback_{timeframe}_{asset}")
        
        end_prep = time.time()
        print(f"[DIAGNOSTIC] Final UI Prep & Render took {end_prep - start_prep:.2f}s")


else:
    st.warning("No data found for the selected asset/timeframe.")

# Live Polling (Must be at the very end to avoid blocking initial render)
if live_mode:
    time.sleep(60)
    st.rerun()
