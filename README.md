# ICT Quantitative Terminal 

A professional-grade quantitative backtesting and visualization platform for **XAU/USD**, **NASDAQ**, and **SP500**, specifically designed for the **ICT Internal Sweep & Inversion** strategy.

---

##  Quantitative Logic & Strategy

The terminal automates a high-probability "Smart Money Concepts" setup across multiple timeframes (M1 to D1).

### 1. Fair Value Gap (FVG) Detection
The engine identifies price imbalances using a 3-candle sequence:
*   **Bullish FVG:** Occurs when the **Low of Candle 3** is higher than the **High of Candle 1**. This creates a "buy-side imbalance" zone.
*   **Bearish FVG:** Occurs when the **High of Candle 3** is lower than the **Low of Candle 1**. This creates a "sell-side imbalance" zone.

### 2. Internal Liquidity (ITH/ITL)
Once an FVG is created, the system monitors price action *inside* the gap boundaries:
*   **Extreme ITH (Intermediate Term High):** The highest 3-candle fractal formed strictly between the Bearish FVG's top and bottom.
*   **Extreme ITL (Intermediate Term Low):** The lowest 3-candle fractal formed strictly between the Bullish FVG's top and bottom.
*   *Note: We focus on the "Extreme" level as it represents the final point of internal liquidity before a reversal.*

### 3. The Execution Chain
A trade signal is generated only when the following sequence is completed:
1.  **Zone Creation:** An FVG is formed and shaded on the chart.
2.  **Level Establishment:** Price enters the zone and forms an internal ITH/ITL.
3.  **The Sweep (S):** Price pierces the internal level (wicking through it) but fails to close beyond it, indicating a liquidity grab.
4.  **iFVG Inversion (Entry):** A candle subsequently **closes through** the original FVG boundary.
    *   *Short entry* if price closes below a Bullish FVG after sweeping an ITL.
    *   *Long entry* if price closes above a Bearish FVG after sweeping an ITH.

---

##  Installation

### 1. Prerequisites
Ensure you have **Python 3.10** or higher installed on your system.

### 2. Clone or Download
Download the project files to your local directory.

### 3. Install Dependencies
Run the following command in your terminal to install the required quantitative and visualization libraries:

```bash
pip install streamlit yfinance pandas numpy streamlit-lightweight-charts pandas_ta
```

---

##  How to Start

Navigate to the project folder in your terminal and execute:

```bash
streamlit run app.py
```

The terminal will automatically open in your default browser (usually at `http://localhost:8501`).

---

##  Terminal Features
*   **Interactive TradingView Charts:** Powered by Lightweight Charts for smooth zooming and panning.
*   **Multi-Timeframe Support:** Seamlessly switch between M1, M5, M15, M30, H1, H4, and D1.
*   **Backtest Engine:** 1% Risk-based position sizing with 1:2 Risk/Reward tracking.
*   **Visual R:R Tool:** Automatically draws TradingView-style red/green rectangles for each executed trade to visualize Stop Loss and Take Profit zones.
*   **Live Status Banner:** Real-time feedback on the "state" of the current market setup.
*   **Historical Simulation:** Load up to 60 days of intraday data to analyze past setups.

---
**Disclaimer:** *This software is for educational and backtesting purposes only. Past performance does not guarantee future results.*
