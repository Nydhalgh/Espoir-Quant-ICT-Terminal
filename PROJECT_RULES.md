# Project Rules: Intermediate Term Logic (ITL)

This project strictly adheres to ITL concepts for XAU/USD. Deviation from these rules constitutes a bug.

## 1. Structural Significance
- **Level Validation**: A level is only valid if it is an ITH or ITL (forms inside an FVG).
- **Fractal Strength**: All swings must have a minimum 5-candle fractal (2 lower/higher on left, 2 lower/higher on right).

## 2. Visualization Rules
- **Noise Reduction**: On M1/M3 timeframes, only plot the **3 most recent** structural levels, not the entire lookback.
- **Finite Rendering**: All levels must start at their formation time and terminate immediately upon being swept.
- **Sweep Confirmation**: If a level is swept but **no iFVG** forms within 90 minutes, the sweep is considered "failed" and should not be visualized as a trade trigger.

## 3. Signal Cascade Rules
- **Timeframe Cascade**: Signals are only valid if they pass the confirmation filter across the 1m -> 3m -> 5m cascade.
- **Consumption**: A sweep is a "one-time-use" setup. Once an iFVG triggers a trade from a sweep, that sweep is "consumed" and cannot trigger further trades.
