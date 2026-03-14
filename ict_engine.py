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

    def find_internal_fractals(self, df, fvg_idx, top, bottom, fvg_type):
        """
        Detects ITH/ITL within the price range of an FVG.
        """
        search_df = df.iloc[fvg_idx+1:]
        fractals = []
        for i in range(self.fractal_period, len(search_df) - self.fractal_period):
            idx = i + fvg_idx + 1
            curr_candle = df.iloc[idx]
            
            is_f = True
            for p in range(1, self.fractal_period + 1):
                if fvg_type == -1: # Bearish FVG, looking for ITH
                    if df.iloc[idx-p]['High'] >= curr_candle['High'] or df.iloc[idx+p]['High'] >= curr_candle['High']:
                        is_f = False; break
                else: # Bullish FVG, looking for ITL
                    if df.iloc[idx-p]['Low'] <= curr_candle['Low'] or df.iloc[idx+p]['Low'] <= curr_candle['Low']:
                        is_f = False; break
            
            if is_f:
                price = curr_candle['High'] if fvg_type == -1 else curr_candle['Low']
                if bottom < price < top:
                    fractals.append({'index': idx, 'price': price, 'time': df.index[idx]})
        return fractals

    def detect_sweeps(self, df, fractal, fvg_type):
        """
        Detects when price sweeps an internal fractal.
        """
        sweeps = []
        for i in range(fractal['index'] + 1, len(df)):
            curr = df.iloc[i]
            if fvg_type == -1: # Bearish FVG, sweep ITH
                if curr['High'] > fractal['price'] and curr['Close'] < fractal['price']:
                    sweeps.append(i)
            else: # Bullish FVG, sweep ITL
                if curr['Low'] < fractal['price'] and curr['Close'] > fractal['price']:
                    sweeps.append(i)
        return sweeps

    def detect_inversion(self, df, fvg_idx, top, bottom, fvg_type, sweeps):
        """
        Detects when price closes on the opposite side of the FVG (Inversion).
        """
        if not sweeps: return None
        first_sweep = sweeps[0]
        
        for i in range(first_sweep + 1, len(df)):
            curr = df.iloc[i]
            if fvg_type == -1: # Bearish FVG
                if curr['Close'] > top:
                    return i
            else: # Bullish FVG
                if curr['Close'] < bottom:
                    return i
        return None

    def get_consolidated_signals(self, df, fvg_idx, top, bottom, fvg_type):
        """
        Combines the steps into a single signal search.
        """
        fractals = self.find_internal_fractals(df, fvg_idx, top, bottom, fvg_type)
        if not fractals: return None
        
        # We take the most extreme fractal for better reliability
        if fvg_type == -1:
            extreme_fractal = max(fractals, key=lambda x: x['price'])
        else:
            extreme_fractal = min(fractals, key=lambda x: x['price'])
            
        sweeps = self.detect_sweeps(df, extreme_fractal, fvg_type)
        if not sweeps: return None
        
        entry_idx = self.detect_inversion(df, fvg_idx, top, bottom, fvg_type, sweeps)
        if entry_idx:
            return {'entry_index': entry_idx, 'fvg_type': fvg_type}
        return None

    def find_ifvgs(self, df):
        """
        Detects Inversion Fair Value Gaps (iFVGs) as standalone triggers.
        """
        fvg_df = self.find_fvgs(df)
        res = df.copy()
        res['ifvg_type'] = 0
        
        for idx, row in fvg_df[fvg_df['fvg_type'] != 0].iterrows():
            f_idx = df.index.get_loc(idx)
            f_type = row['fvg_type']
            f_top = row['fvg_top']
            f_bottom = row['fvg_bottom']
            
            for i in range(f_idx + 1, len(df)):
                close = df.iloc[i]['Close']
                if f_type == 1: # Bullish FVG
                    if close < f_bottom:
                        res.iloc[i, res.columns.get_loc('ifvg_type')] = -1
                        break
                elif f_type == -1: # Bearish FVG
                    if close > f_top:
                        res.iloc[i, res.columns.get_loc('ifvg_type')] = 1
                        break
        return res

    @classmethod
    def swing_highs_lows(cls, ohlc: pd.DataFrame, swing_length: int = 5) -> pd.DataFrame:
        """
        SMC Vectorized Swing Highs/Lows implementation.
        """
        ohlc = ohlc.rename(columns=str.lower)
        swing_length *= 2
        
        highs = ohlc["high"].shift(-(swing_length // 2)).rolling(swing_length).max()
        lows = ohlc["low"].shift(-(swing_length // 2)).rolling(swing_length).min()
        
        shl = np.where(ohlc["high"] == highs, 1, np.where(ohlc["low"] == lows, -1, np.nan))
        
        # Simple cleanup for consecutive same-type swings (keep the extreme)
        pos = np.where(~np.isnan(shl))[0]
        if len(pos) > 1:
            for i in range(len(pos) - 1):
                idx1, idx2 = pos[i], pos[i+1]
                if shl[idx1] == shl[idx2]:
                    if shl[idx1] == 1: # Both highs
                        if ohlc["high"].iloc[idx1] > ohlc["high"].iloc[idx2]: shl[idx2] = np.nan
                        else: shl[idx1] = np.nan
                    else: # Both lows
                        if ohlc["low"].iloc[idx1] < ohlc["low"].iloc[idx2]: shl[idx2] = np.nan
                        else: shl[idx1] = np.nan
        
        level = np.where(~np.isnan(shl), np.where(shl == 1, ohlc["high"], ohlc["low"]), np.nan)
        return pd.DataFrame({"HighLow": shl, "Level": level}, index=ohlc.index)

    def compute_mtf_signals(self, primary_df, htf_dfs, timeframe):
        """
        Optimized calculation of MTF signals (HTF Sweep -> M1 iFVG Entry).
        Limits HTF levels to the last 48 hours for clarity.
        """
        htf_sweeps = []
        extra_series_data = []
        cutoff_time = primary_df.index[-1] - pd.Timedelta(days=2)
        
        # 1. Process HTF Levels & Sweeps
        for tf, hdf in htf_dfs.items():
            if hdf.empty: continue
            
            # Use formal SMC ITH/ITL logic
            fvg_data = self.find_fvgs(hdf)
            shl_data = self.swing_highs_lows(hdf)
            ith_itl_series = self.ith_itl(hdf, shl_data, fvg_data)
            
            # Find indices where ITH/ITL != NaN
            indices = ith_itl_series.dropna().index
            
            for t in indices:
                price = shl_data.loc[t, 'Level']
                l_type = 'ITH' if ith_itl_series.loc[t] == 1 else 'ITL'
                
                # Store level for visualization (Only if within cutoff)
                if t >= cutoff_time:
                    extra_series_data.append({
                        'time': t, 'price': price, 'type': l_type, 'tf': tf
                    })
                
                # Sweep detection (Vectorized)
                hdf_after = hdf.loc[t:]
                if l_type == 'ITH': # Short Sweep
                    sweeps = hdf_after[(hdf_after['High'] > price) & (hdf_after['Close'] < price)]
                    for ts in sweeps.index:
                        htf_sweeps.append({'time': ts, 'type': 'short'})
                else: # Long Sweep
                    sweeps = hdf_after[(hdf_after['Low'] < price) & (hdf_after['Close'] > price)]
                    for ts in sweeps.index:
                        htf_sweeps.append({'time': ts, 'type': 'long'})
                        
        # 2. Process M1 Confirmation
        m1_df = htf_dfs.get('M1', primary_df if timeframe == 'M1' else pd.DataFrame())
        global_entries = []
        
        if not m1_df.empty:
            m1_ifvgs = self.find_ifvgs(m1_df)
            active_ifvgs = m1_ifvgs[m1_ifvgs['ifvg_type'] != 0]
            
            if htf_sweeps:
                sweeps_df = pd.DataFrame(htf_sweeps).sort_values('time')
                for i_time, i_row in active_ifvgs.iterrows():
                    relevant_sweeps = sweeps_df[
                        (sweeps_df['time'] < i_time) & 
                        (sweeps_df['time'] > i_time - pd.Timedelta(hours=12))
                    ]
                    if not relevant_sweeps.empty:
                        if i_row['ifvg_type'] == 1 and (relevant_sweeps['type'] == 'long').any():
                            global_entries.append({'time': i_time, 'price': i_row['Close'], 'type': 'LONG'})
                        elif i_row['ifvg_type'] == -1 and (relevant_sweeps['type'] == 'short').any():
                            global_entries.append({'time': i_time, 'price': i_row['Close'], 'type': 'SHORT'})
                                
        return {
            'global_entries': global_entries,
            'htf_levels': extra_series_data
        }

    def get_sessions(self, df):
        """
        Calculates session masks for background shading.
        """
        # Session times in UTC
        sessions = {
            "Asian": {"start": 0, "end": 4, "color": "rgba(41, 98, 255, 0.05)"},
            "London": {"start": 7, "end": 15, "color": "rgba(255, 152, 0, 0.05)"},
            "NY": {"start": 12, "end": 20, "color": "rgba(76, 175, 80, 0.05)"}
        }
        
        session_data = []
        for name, config in sessions.items():
            # Find ranges where hour is between start and end
            mask = (df.index.hour >= config['start']) & (df.index.hour < config['end'])
            # Group consecutive True values to find session boxes
            diff = np.diff(mask.astype(int), prepend=0)
            starts = np.where(diff == 1)[0]
            ends = np.where(diff == -1)[0]
            
            # Handle case where session is active at the end of the dataframe
            if len(starts) > len(ends):
                ends = np.append(ends, len(df) - 1)
                
            for s, e in zip(starts, ends):
                session_data.append({
                    "start": df.index[s],
                    "end": df.index[e],
                    "color": config['color'],
                    "name": name
                })
        return session_data

    def get_current_status(self, df):
        """
        Detects the current state of the most recent FVG using consolidated logic.
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
        
        # Check if completed
        signal = self.get_consolidated_signals(df, fvg_idx, top, bottom, fvg_type)
        if signal:
            return f"✅ Setup Completed: Entry @ {df.index[signal['entry_index']].strftime('%H:%M')}"
            
        # If not completed, check partial status
        fractals = self.find_internal_fractals(df, fvg_idx, top, bottom, fvg_type)
        if not fractals:
            return "🔭 Observation: Waiting for Internal ITH/ITL formation..."
            
        if fvg_type == -1: extreme_fractal = max(fractals, key=lambda x: x['price'])
        else: extreme_fractal = min(fractals, key=lambda x: x['price'])
            
        sweeps = self.detect_sweeps(df, extreme_fractal, fvg_type)
        if not sweeps:
            return f"🎯 Level Established ({extreme_fractal['price']:.2f}). Waiting for Sweep..."
            
        return "💥 Liquidity Swept! Watching for iFVG Inversion (Boundary Close)..."
