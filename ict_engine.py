import pandas as pd
import numpy as np

class ICTEngine:
    def __init__(self, fractal_period=1):
        """
        fractal_period: 1 for 3-candle fractal, 2 for 5-candle fractal.
        We'll use 1 by default (3-candle fractal).
        """
        self.fractal_period = fractal_period

    def find_all_fractals(self, df):
        """
        Finds ALL ITH/ITL fractals in the dataframe regardless of FVGs.
        """
        fractals = []
        for i in range(self.fractal_period, len(df) - self.fractal_period):
            curr = df.iloc[i]
            is_ith = True
            is_itl = True
            for p in range(1, self.fractal_period + 1):
                if df.iloc[i-p]['High'] >= curr['High'] or df.iloc[i+p]['High'] >= curr['High']:
                    is_ith = False
                if df.iloc[i-p]['Low'] <= curr['Low'] or df.iloc[i+p]['Low'] <= curr['Low']:
                    is_itl = False
            
            if is_ith:
                fractals.append({'index': i, 'time': df.index[i], 'price': curr['High'], 'type': 'ITH'})
            if is_itl:
                fractals.append({'index': i, 'time': df.index[i], 'price': curr['Low'], 'type': 'ITL'})
        return fractals

    def find_fvgs(self, df):
        """
        Implementation of SMC Document: fvg logic
        Returns FVG type, Top, Bottom, and MitigatedIndex
        """
        ohlc = df.rename(columns=str.lower)
        n = len(ohlc)
        
        fvg = np.where(
            (
                (ohlc["high"].shift(1) < ohlc["low"].shift(-1))
                & (ohlc["close"] > ohlc["open"])
            )
            | (
                (ohlc["low"].shift(1) > ohlc["high"].shift(-1))
                & (ohlc["close"] < ohlc["open"])
            ),
            np.where(ohlc["close"] > ohlc["open"], 1, -1),
            np.nan,
        )

        top = np.where(
            ~np.isnan(fvg),
            np.where(
                ohlc["close"] > ohlc["open"],
                ohlc["low"].shift(-1),
                ohlc["low"].shift(1),
            ),
            np.nan,
        )

        bottom = np.where(
            ~np.isnan(fvg),
            np.where(
                ohlc["close"] > ohlc["open"],
                ohlc["high"].shift(1),
                ohlc["high"].shift(-1),
            ),
            np.nan,
        )

        mitigated_index = np.zeros(n, dtype=np.int32)
        for i in np.where(~np.isnan(fvg))[0]:
            mask = np.zeros(n, dtype=bool)
            if fvg[i] == 1:
                if i + 2 < n:
                    mask[i+2:] = ohlc["low"].iloc[i + 2 :] <= top[i]
            elif fvg[i] == -1:
                if i + 2 < n:
                    mask[i+2:] = ohlc["high"].iloc[i + 2 :] >= bottom[i]
            
            if np.any(mask):
                j = np.flatnonzero(mask)[0]
                mitigated_index[i] = j

        # Final DF
        res = df.copy()
        res['fvg_type'] = fvg
        res['fvg_top'] = top
        res['fvg_bottom'] = bottom
        res['mitigated_index'] = np.where(np.isnan(fvg), np.nan, mitigated_index)
        
        return res

    @classmethod
    def ith_itl(cls, ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, fvg_data: pd.DataFrame) -> pd.Series:
        """
        Implementation of SMC Document: ith_itl logic
        ITH = Swing High inside an active Bearish FVG
        ITL = Swing Low inside an active Bullish FVG
        """
        ith_itl = np.zeros(len(ohlc), dtype=np.int32)
        
        shl_val = swing_highs_lows["HighLow"].values
        shl_level = swing_highs_lows["Level"].values
        
        fvg_val = fvg_data["fvg_type"].values
        fvg_top = fvg_data["fvg_top"].values
        fvg_bottom = fvg_data["fvg_bottom"].values
        fvg_mitigated = fvg_data["mitigated_index"].values
        
        for i in range(len(ohlc)):
            if shl_val[i] == 1:  # Swing High
                # Check if this high formed inside an active Bearish FVG
                for j in range(i):
                    if fvg_val[j] == -1:  # Bearish FVG
                        # Rule: FVG was still open (unmitigated) at the exact moment the Swing High reached into it
                        is_active = np.isnan(fvg_mitigated[j]) or fvg_mitigated[j] == 0 or fvg_mitigated[j] >= i
                        if is_active and (fvg_bottom[j] <= shl_level[i] <= fvg_top[j]):
                            ith_itl[i] = 1  # Mark as ITH
                            break
                            
            elif shl_val[i] == -1:  # Swing Low
                # Check if this low formed inside an active Bullish FVG
                for j in range(i):
                    if fvg_val[j] == 1:  # Bullish FVG
                        is_active = np.isnan(fvg_mitigated[j]) or fvg_mitigated[j] == 0 or fvg_mitigated[j] >= i
                        if is_active and (fvg_bottom[j] <= shl_level[i] <= fvg_top[j]):
                            ith_itl[i] = -1  # Mark as ITL
                            break

        # Convert zeros to NaN to keep data clean
        ith_itl = np.where(ith_itl != 0, ith_itl, np.nan)

        return pd.Series(ith_itl, name="ITH_ITL", index=ohlc.index)

    def get_current_status(self, df):
        """
        Detects the current state of the most recent FVG.
        """
        fvgs = self.find_fvgs(df)
        active_fvgs = fvgs[fvgs['fvg_type'] != 0]
        
        if active_fvgs.empty:
            return "No Active FVG Detected"
            
        last_fvg_row = active_fvgs.iloc[-1]
        fvg_idx = df.index.get_loc(last_fvg_row.name)
        top = last_fvg_row['fvg_top']
        bottom = last_fvg_row['fvg_bottom']
        fvg_type = last_fvg_row['fvg_type']
        
        signal = self.get_consolidated_signals(df, fvg_idx, top, bottom, fvg_type)
        if signal:
            return f"✅ Setup Completed: Entry @ {df.index[signal['entry_index']].strftime('%H:%M')}"
            
        search_df = df.iloc[fvg_idx+1:]
        extreme_fractal = None
        for i in range(self.fractal_period, len(search_df) - self.fractal_period):
            idx = i + fvg_idx + 1
            curr_candle = df.iloc[idx]
            
            is_f = True
            for p in range(1, self.fractal_period + 1):
                if fvg_type == -1:
                    if df.iloc[idx-p]['High'] >= curr_candle['High'] or df.iloc[idx+p]['High'] >= curr_candle['High']:
                        is_f = False; break
                else:
                    if df.iloc[idx-p]['Low'] <= curr_candle['Low'] or df.iloc[idx+p]['Low'] <= curr_candle['Low']:
                        is_f = False; break
            
            if is_f:
                price = curr_candle['High'] if fvg_type == -1 else curr_candle['Low']
                if bottom < price < top:
                    if extreme_fractal is None: extreme_fractal = price
                    else:
                        if fvg_type == -1: extreme_fractal = max(extreme_fractal, price)
                        else: extreme_fractal = min(extreme_fractal, price)
        
        if extreme_fractal is None:
            return "🔭 Observation: Waiting for Internal ITH/ITL formation..."
            
        has_sweep = False
        for i in range(fvg_idx+1, len(df)):
            curr = df.iloc[i]
            if fvg_type == -1:
                if curr['High'] > extreme_fractal and curr['Close'] < extreme_fractal:
                    has_sweep = True; break
            else:
                if curr['Low'] < extreme_fractal and curr['Close'] > extreme_fractal:
                    has_sweep = True; break
                    
        if has_sweep:
            return "💥 Liquidity Swept! Watching for iFVG Inversion (Boundary Close)..."
            
        return f"🎯 Level Established ({extreme_fractal:.2f}). Waiting for Sweep..."
