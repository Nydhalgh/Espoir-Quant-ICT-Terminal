# ICT Quantitative Terminal - Smart Money Concepts (SMC)

A professional-grade quantitative backtesting and visualization platform for **XAU/USD**, **NASDAQ**, and **SP500**, specifically designed for the **ICT Internal Sweep & M1 iFVG Inversion** strategy.

---

##  Quantitative Logic & Aligned Strategy

The terminal automates high-probability setups across multiple timeframes, rigorously following the technical specifications of **Smart Money Concepts (SMC)**.

### 1. Fair Value Gap (FVG) Detection
The engine identifies price imbalances using the standard SMC 3-candle sequence:
*   **Bullish FVG:** $\text{High}_{t-1} < \text{Low}_{t+1}$ with a bullish middle candle.
*   **Bearish FVG:** $\text{Low}_{t-1} > \text{High}_{t+1}$ with a bearish middle candle.
*   **Mitigation:** An FVG is considered mitigated once price action completely crosses its boundary level.

### 2. Market Structure: Swings & Fractals
Precise market structure is established using:
*   **Swing Highs/Lows:** Highest high or lowest low within a specific rolling window (e.g., 50 candles), with consecutive extreme removal logic.
*   **ITH (Intermediate Term High):** A Swing High that forms strictly inside an **unmitigated** Bearish FVG.
*   **ITL (Intermediate Term Low):** A Swing Low that forms strictly inside an **unmitigated** Bullish FVG.
*   *Rule:* An ITH/ITL is only valid if the FVG was still open (unmitigated) at the exact moment the swing point reached into it.

### 3. Multi-Timeframe (MTF) Execution Chain
A trade signal is generated through a rigorous cross-timeframe confirmation process:
1.  **HTF Level Establishment:** The system identifies ITH/ITL levels on Higher Timeframes (M15, M30, H1).
2.  **The HTF Sweep (S):** Price pierces an HTF level (wicking through it) and closes back inside, indicating a liquidity grab.
3.  **M1 iFVG Inversion (Confirmation):** Once an HTF sweep is detected, the engine waits for an **Inversion FVG** on the **M1 timeframe**.
4.  **Global Signal Projection:** Upon M1 confirmation, the entry signal (Green/Red Arrow) is projected onto **all timeframes**, allowing for high-precision entries with higher timeframe context.

---

##  Installation

### 1. Prerequisites
Ensure you have **Python 3.10** or higher installed.

### 2. Install Dependencies
Run the following command to install the required quantitative and visualization libraries:

```bash
pip install streamlit yfinance pandas numpy streamlit-lightweight-charts pandas_ta
```

---

##  How to Start

Navigate to the project folder and execute:

```bash
python -m streamlit run app.py
```

The terminal will automatically open in your default browser at `http://localhost:8501`.

---

##  Terminal Features
*   **Immersive Immersive Charts:** 900px high charts with advanced scroll/scale enabled.
*   **30-Day Historical Data:** Intraday timeframes (M1-H1) now load 30 days of data by default for comprehensive backtesting.
*   **MTF Signal Visibility:** M1-confirmed entry arrows are visible across all timeframes.
*   **Contextual Overlays:** HTF ITH/ITL levels are projected onto LTF charts as dashed horizontal lines.
*   **Dynamic FVG Rendering:** Only FVGs for the currently selected timeframe are shown to reduce visual clutter.
*   **Visual R:R Tool:** Automatically draws red/green risk-reward rectangles for each trade.

---
**Disclaimer:** *This software is for educational and backtesting purposes only. Past performance does not guarantee future results.*
