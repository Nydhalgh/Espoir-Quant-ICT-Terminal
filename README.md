# ICT Quantitative Terminal - ITL (Intermediate Term Logic)

A professional-grade quantitative backtesting and visualization platform for **XAU/USD**, designed specifically to execute the **Intermediate Term Trading (ITL)** strategy.

---

##  The ITTL (Intermediate Term Trading Logic)

This project strictly adheres to the ITL structural standard. Please consult [PROJECT_RULES.md](PROJECT_RULES.md) for the authoritative rules on structural significance, visualization constraints, and signal cascading.

### Core Architecture Principles
1.  **5-Candle Fractals**: Market structure is identified via a 5-candle minimum lookback.
2.  **Sweep Consumption**: A liquidity sweep is a "one-time-use" setup. Once consumed by an entry signal, it cannot trigger further trades.
3.  **Signal Cascading**: Entry signals are validated across the 1m → 3m → 5m hierarchy.
4.  **Finite Rendering**: Chart clutter is minimized by enforcing finite visualization of structural levels.

---

##  Quantitative Engine Specification

### 1. Market Structure Analysis (ITH/ITL)
- **ITH (Intermediate Term High)**: Swing High forming inside an unmitigated Bearish FVG.
- **ITL (Intermediate Term Low)**: Swing Low forming inside an unmitigated Bullish FVG.
- **Validation**: Strict adherence to the "inside FVG" constraint ensures only high-probability levels are plotted.

### 2. MTF Signal Cascade (The Execution Chain)
The engine generates trades through a mandatory confirmation cascade:
1.  **HTF Level Establishment**: Structure is identified on M15, M30, H1.
2.  **Liquidity Sweep**: Price sweeps an HTF level.
3.  **iFVG Inversion**: The engine waits for an **Inversion FVG** (iFVG) on the execution timeframe (M1-M5).
4.  **Cascading Filter**: If multiple iFVGs appear on the current timeframe, the engine cascades up to the next timeframe until exactly **one** iFVG is found. If no valid setup exists by the 5m timeframe, the setup is **invalidated**.

---

##  Installation

### 1. Prerequisites
Ensure you have **Python 3.10** or higher installed.

### 2. Install Dependencies
```bash
pip install streamlit yfinance pandas numpy streamlit-lightweight-charts pandas_ta
```

---

##  How to Start

Navigate to the project folder and execute:

```bash
streamlit run app.py
```

The terminal will automatically open in your default browser at `http://localhost:8501`.

---

##  Terminal Features
*   **Architectural Noise Reduction**: M1/M5 charts automatically filter and display only the **3 most recent** relevant structural levels.
*   **Timezone & Killzone Awareness**: Integrated session shading for London (07:00-15:00 CET) and NY (12:00-20:00 CET).
*   **Contextual Overlays**: HTF ITH/ITL levels are projected as persistent horizontal lines until consumed by a sweep.
*   **Proactive Risk Control**: Trade entries are restricted to valid killzones to prevent over-trading in illiquid conditions.

---

**Disclaimer:** *This software is for educational and backtesting purposes only. Past performance does not guarantee future results.*
