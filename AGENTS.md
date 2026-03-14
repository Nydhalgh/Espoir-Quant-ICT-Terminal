# Agent Instructions - ICT Quantitative Terminal

This repository contains a high-fidelity quantitative trading terminal based on **Smart Money Concepts (SMC)**. It is built with **Streamlit** (Frontend) and **Pandas/NumPy** (Backend Engine).

##  Execution & Verification
### Run the Application
```bash
streamlit run app.py
```
### Stop the Application
```bash
taskkill /F /IM python.exe /T
```
### Run Tests
- Run all tests: `pytest` or `python -m pytest`
- Run a single test file: `python test_ict_logic.py`
- Verify engine methods: `python verify_engine.py`

##  Project Structure
- `app.py`: Main entry point and UI orchestration. Handles Streamlit layout, session state, and component integration.
- `ict_engine.py`: Core mathematical logic for SMC. Includes vectorized FVG detection, Swing Highs/Lows, and ITH/ITL identification.
- `data_manager.py`: Market data fetching using Yahoo Finance. Handles parallel requests and timeframe resampling.
- `charts.py`: Wrapper for `streamlit-lightweight-charts`. Sanitizes data for JSON serialization and configures chart themes.
- `backtester.py`: Execution simulation. Processes signals to calculate Profit Factor, Sharpe Ratio, and Max Drawdown.

##  Code Style & Guidelines
### 1. Imports & Dependencies
- Group imports: Standard library, third-party, and then local modules.
- Always use `from concurrent.futures import ThreadPoolExecutor` for I/O bound tasks.
- Keep `pandas` and `numpy` as primary data processing libraries.

### 2. Formatting & Naming
- Use `snake_case` for all functions and variable names.
- Use `PascalCase` for classes (e.g., `ICTEngine`, `DataManager`).
- Maintain a consistent indentation of 4 spaces.
- Variable names should be descriptive (e.g., `primary_df`, `htf_levels`).

### 3. Logic & Performance
- **Vectorization is Mandatory**: Avoid `iterrows()` or `itertuples()`. Use NumPy vectorized operations (`np.where`, `np.logical_and`) for processing large datasets.
- **Strict SMC Compliance**: All calculations MUST align with the definitions in `@Smart Money Concepts Technical_logic.md`.
- **Caching**: Use Streamlit's `@st.cache_data` for heavy computations and data fetching to ensure UI responsiveness.

### 4. Frontend (UI/UX)
- **Minimalism First**: Use a dark theme palette (`#0b0e11` background, `#1e222d` card background).
- **Metric Cards**: Use metric components for key data points (Current Price, Session High/Low).
- **Responsive Charts**: Ensure charts use the full container width and have a height of at least 900px for professional analysis.

### 5. Type Safety & Error Handling
- **NaN Safety**: Technical indicators often produce `NaN` values. Always use `safe_json_serialize` before passing data to chart components.
- **Explicit Casting**: Cast Pandas series to `float()` or `int()` when preparing JSON data.
- **Graceful Failures**: Wrap data fetching and chart rendering in `try-except` blocks to prevent the entire UI from crashing.

##  Core Strategy Logic
- **Fair Value Gap (FVG)**: Detected via 3-candle sequences. A gap is unmitigated until price fully traverses the range.
- **ITH (Intermediate Term High)**: A Swing High forming within an unmitigated Bearish FVG.
- **ITL (Intermediate Term Low)**: A Swing Low forming within an unmitigated Bullish FVG.
- **Signal Hierarchy**: Arrows (M1/M5) > HTF Levels (M15/M30/H1) > Market Bias (D1).

##  Timezone & Sessions
- All data is normalized to **UTC+1 (CET)**.
- **London Session**: 07:00 - 15:00.
- **NY Session**: 12:00 - 20:00.
- Kill Zones are highlighted as background shading on the chart.

##  Testing Protocol
- Always run `python test_ict_logic.py` after modifying `ict_engine.py`.
- Use `verify_engine.py` to check for missing method definitions or session state issues.
- Check the "System Diagnostics" expander in the UI for performance bottlenecks.

##  Contribution Workflow
1.  **Branching Strategy**: Use `feature/` for new logic or UI components and `fix/` for bug resolution.
2.  **Logic Verification**: Ensure any new indicator or signal matches the SMC technical documentation exactly.
3.  **UI Verification**: Test chart zooming and scaling on multiple resolutions. Ensure background session boxes do not block candle visibility.
4.  **Performance Check**: Verify that new logic does not increase loading times beyond 5-10 seconds for 30 days of M1 data.

##  JSON Serialization Protocol
The `streamlit-lightweight-charts` component is sensitive to `NaN` and `Inf` values. Always use the `safe_json_serialize` utility in `app.py` before passing data to the component.
```python
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
```

##  Session Management
Streamlit reruns the script on every interaction. Use `st.session_state` to store heavy objects like `DataManager` and `ICTEngine` to avoid re-initialization.
```python
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
```

##  Data Flow
1. User selects Symbol/Timeframe.
2. `DataManager.fetch_data` downloads OHLCV data using `yfinance`.
3. `ICTEngine` processes the data using vectorized Pandas/NumPy.
4. `ChartVisualizer` prepares the data series and markers.
5. `app.py` renders the Streamlit layout and Chart component.
