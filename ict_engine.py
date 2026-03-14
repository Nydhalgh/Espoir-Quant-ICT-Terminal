import pandas as pd
import numpy as np

class ICTEngine:
    def __init__(self, fractal_period=1):
        self.fractal_period = fractal_period

    def find_all_fractals(self, df):
        """Finds ALL ITH/ITL fractals in the dataframe."""
        fractals = []
        highs = df['High'].values
        lows = df['Low'].values
        n = len(df)
        
        for i in range(self.fractal_period, n - self.fractal_period):
            is_ith = True
            is_itl = True
            for p in range(1, self.fractal_period + 1):
                if highs[i-p] >= highs[i] or highs[i+p] >= highs[i]:
                    is_ith = False
                if lows[i-p] <= lows[i] or lows[i+p] <= lows[i]:
                    is_itl = False
            
            if is_ith:
                fractals.append({'index': i, 'time': df.index[i], 'price': highs[i], 'type': 'ITH'})
            if is_itl:
                fractals.append({'index': i, 'time': df.index[i], 'price': lows[i], 'type': 'ITL'})
        return fractals

    def find_fvgs(self, df):
        """Standard SMC FVG logic with relaxed mitigation for ITH/ITL."""
        ohlc = df.rename(columns=str.lower)
        n = len(ohlc)
        
        high = ohlc["high"].values
        low = ohlc["low"].values
        open_ = ohlc["open"].values
        close = ohlc["close"].values
        
        fvg = np.full(n, np.nan)
        top = np.full(n, np.nan)
        btm = np.full(n, np.nan)
        
        # Bullish FVG (Gap between High of candle 1 and Low of candle 3)
        bull_mask = (high[:-2] < low[2:]) & (close[1:-1] > open_[1:-1])
        fvg[1:-1] = np.where(bull_mask, 1, fvg[1:-1])
        top[1:-1] = np.where(bull_mask, low[2:], top[1:-1])
        btm[1:-1] = np.where(bull_mask, high[:-2], btm[1:-1])
        
        # Bearish FVG (Gap between Low of candle 1 and High of candle 3)
        bear_mask = (low[:-2] > high[2:]) & (close[1:-1] < open_[1:-1])
        fvg[1:-1] = np.where(bear_mask, -1, fvg[1:-1])
        top[1:-1] = np.where(bear_mask, low[:-2], top[1:-1])
        btm[1:-1] = np.where(bear_mask, high[2:], btm[1:-1])
        
        # MITIGATION: Relaxed for ITH/ITL. 
        # A Bearish FVG is fully closed only if price goes ABOVE the top (low[i-1]).
        # A Bullish FVG is fully closed only if price goes BELOW the bottom (high[i-1]).
        mitigated_index = np.zeros(n, dtype=np.int32)
        indices = np.where(~np.isnan(fvg))[0]
        for i in indices:
            if fvg[i] == 1:
                mask = low[i+2:] < btm[i] # Bullish gap closed if price drops below gap floor
            else:
                mask = high[i+2:] > top[i] # Bearish gap closed if price rises above gap ceiling
            
            if np.any(mask):
                mitigated_index[i] = np.flatnonzero(mask)[0] + i + 2

        res = df.copy()
        res['fvg_type'] = fvg
        res['fvg_top'] = top
        res['fvg_bottom'] = btm
        res['mitigated_index'] = np.where(np.isnan(fvg), np.nan, mitigated_index)
        return res

    def swing_highs_lows(self, ohlc, swing_length=5):
        """Robust Vectorized Swing Highs/Lows with Flat-Peak handling."""
        high = ohlc['High'].values
        low = ohlc['Low'].values
        n = len(ohlc)
        
        shl = np.full(n, np.nan)
        level = np.full(n, np.nan)
        
        for i in range(swing_length, n - swing_length):
            is_high = True
            is_low = True
            for p in range(1, swing_length + 1):
                if high[i-p] > high[i] or high[i+p] >= high[i]:
                    is_high = False
                if low[i-p] < low[i] or low[i+p] <= low[i]:
                    is_low = False
            
            if is_high:
                shl[i] = 1
                level[i] = high[i]
            elif is_low:
                shl[i] = -1
                level[i] = low[i]
        
        # LOGGING
        num_sh = np.sum(shl == 1)
        num_sl = np.sum(shl == -1)
        print(f"[LOG] Swing Detection (len={swing_length}): {num_sh} Highs, {num_sl} Lows found.")
        
        return pd.DataFrame({"HighLow": shl, "Level": level}, index=ohlc.index)

    def ith_itl(self, ohlc, swing_highs_lows, fvg_data):
        """ITH/ITL: Swing high/low formed within the price range of an unmitigated FVG."""
        n = len(ohlc)
        res = np.full(n, np.nan)
        
        shl_val = swing_highs_lows["HighLow"].values
        shl_price = swing_highs_lows["Level"].values # This is High for SH, Low for SL
        
        f_types = fvg_data["fvg_type"].values
        f_tops = fvg_data["fvg_top"].values
        f_btms = fvg_data["fvg_bottom"].values
        f_mits = fvg_data["mitigated_index"].values
        
        f_indices = np.where(~np.isnan(f_types))[0]
        s_indices = np.where(~np.isnan(shl_val))[0]
        
        for fi in f_indices:
            f_type = f_types[fi]
            # Price range of the gap
            top = f_tops[fi]
            btm = f_btms[fi]
            mit = f_mits[fi]
            f_mit = int(mit) if not np.isnan(mit) and mit > 0 else n
            
            # Find all swings that occur after the FVG but before full mitigation
            targets = s_indices[(s_indices > fi) & (s_indices < f_mit)]
            for si in targets:
                # ITH = Swing High inside Bearish FVG
                if f_type == -1 and shl_val[si] == 1:
                    # Check if the Swing High (Peak) is within the gap range
                    if btm <= shl_price[si] <= top:
                        res[si] = 1
                # ITL = Swing Low inside Bullish FVG
                elif f_type == 1 and shl_val[si] == -1:
                    # Check if the Swing Low (Trough) is within the gap range
                    if btm <= shl_price[si] <= top:
                        res[si] = -1
        
        # LOGGING
        num_ith = np.sum(res == 1)
        num_itl = np.sum(res == -1)
        print(f"[LOG] ITH/ITL Scan: Found {num_ith} ITH and {num_itl} ITL levels.")
        
        return pd.Series(res, name="ITH_ITL", index=ohlc.index)



    def find_ifvgs(self, df):
        """Standalone iFVG detection."""
        fvg_df = self.find_fvgs(df)
        res = df.copy()
        res['ifvg_type'] = 0
        
        closes = df['Close'].values
        fvg_types = fvg_df['fvg_type'].values
        fvg_tops = fvg_df['fvg_top'].values
        fvg_btms = fvg_df['fvg_bottom'].values
        
        indices = np.where(~np.isnan(fvg_types))[0]
        for i in indices:
            search = closes[i+1:]
            if fvg_types[i] == 1:
                mask = search < fvg_btms[i]
            else:
                mask = search > fvg_tops[i]
            
            if np.any(mask):
                idx = np.flatnonzero(mask)[0] + i + 1
                res.iloc[idx, res.columns.get_loc('ifvg_type')] = -1 if fvg_types[i] == 1 else 1
        return res

    def compute_mtf_signals(self, primary_df, htf_dfs, timeframe):
        """
        Refined MTF Logic: 
        1. HTF Levels from H1/M30/M15.
        2. Sweeps detected using M1 data.
        3. Entries confirmed using M1 iFVGs.
        """
        htf_levels_list = []
        htf_sweeps = []
        now = primary_df.index[-1]
        cutoff = now - pd.Timedelta(days=2)
        
        # We ALWAYS use M1 for execution logic (Sweeps and iFVGs)
        # If primary is M1, use it; otherwise get it from htf_dfs
        exec_df = htf_dfs.get('M1', primary_df if timeframe == 'M1' else pd.DataFrame())
        
        if exec_df.empty:
            print("[LOG] Warning: Execution DF (M1) not found. Signals will be limited.")
            exec_df = primary_df # Fallback to primary
            
        e_highs = exec_df['High'].values
        e_lows = exec_df['Low'].values
        e_closes = exec_df['Close'].values
        e_times = exec_df.index

        # 1. Identify all Structural Levels (H1, M30, M15)
        for tf, hdf in htf_dfs.items():
            if hdf.empty or tf == 'M1': continue # Skip execution TF for structure
            
            fvg_data = self.find_fvgs(hdf)
            shl_data = self.swing_highs_lows(hdf, swing_length=2) 
            ith_itl_data = self.ith_itl(hdf, shl_data, fvg_data)
            
            for t, val in ith_itl_data.dropna().items():
                if t < cutoff: continue
                price = shl_data.at[t, 'Level']
                
                # Check for sweep anytime AFTER the level formed using EXECUTION DF
                try:
                    idx = exec_df.index.get_indexer([t], method='bfill')[0]
                    if idx == -1: continue
                    
                    after_h, after_l, after_c = e_highs[idx:], e_lows[idx:], e_closes[idx:]
                    
                    if val == 1: # ITH (Short Draw)
                        sweeps = (after_h > price) & (after_c < price)
                        is_unswept = not np.any(sweeps)
                        if not is_unswept:
                            first_s = np.flatnonzero(sweeps)[0]
                            htf_sweeps.append({'time': e_times[idx + first_s], 'type': 'short'})
                    else: # ITL (Long Draw)
                        sweeps = (after_l < price) & (after_c > price)
                        is_unswept = not np.any(sweeps)
                        if not is_unswept:
                            first_s = np.flatnonzero(sweeps)[0]
                            htf_sweeps.append({'time': e_times[idx + first_s], 'type': 'long'})
                    
                    if is_unswept:
                        htf_levels_list.append({'time': t, 'price': price, 'type': 'ITH' if val == 1 else 'ITL', 'tf': tf})
                except: continue

        # 2. Local Levels (Primary TF)
        p_fvg = self.find_fvgs(primary_df)
        p_shl = self.swing_highs_lows(primary_df, swing_length=2)
        p_ith_itl = self.ith_itl(primary_df, p_shl, p_fvg)
        for t, val in p_ith_itl.dropna().items():
            if t < cutoff: continue
            price = p_shl.at[t, 'Level']
            # Only add to list if not already there from HTF
            if not any(l['price'] == price for l in htf_levels_list):
                htf_levels_list.append({'time': t, 'price': price, 'type': 'ITH' if val == 1 else 'ITL', 'tf': timeframe, 'is_primary': True})

        # 3. M1 Entry Confirmation (iFVG after sweep)
        global_entries = []
        if not exec_df.empty and htf_sweeps:
            m1_ifvgs = self.find_ifvgs(exec_df)
            active = m1_ifvgs[m1_ifvgs['ifvg_type'] != 0]
            
            sweeps_df = pd.DataFrame(htf_sweeps).sort_values('time').drop_duplicates('time')
            sweep_times = sweeps_df['time']
            sweep_types = sweeps_df['type']
            
            last_entry_time = None
            for i_time, i_row in active.iterrows():
                if last_entry_time and i_time - last_entry_time < pd.Timedelta(minutes=30):
                    continue
                    
                lookback = i_time - pd.Timedelta(hours=6)
                matches = sweep_types[(sweep_times < i_time) & (sweep_times > lookback)]
                
                is_bullish_entry = i_row['ifvg_type'] == 1 and (matches == 'long').any()
                is_bearish_entry = i_row['ifvg_type'] == -1 and (matches == 'short').any()
                
                if is_bullish_entry or is_bearish_entry:
                    global_entries.append({'time': i_time, 'price': i_row['Close'], 'type': 'LONG' if is_bullish_entry else 'SHORT'})
                    last_entry_time = i_time
                        
        return {'global_entries': global_entries, 'htf_levels': htf_levels_list}


    def get_sessions(self, df):
        """Session markers."""
        sessions = {"Asian": (0, 4, "rgba(41,98,255,0.05)"), "London": (7, 15, "rgba(255,152,0,0.05)"), "NY": (12, 20, "rgba(76,175,80,0.05)")}
        res = []
        for name, (s, e, c) in sessions.items():
            mask = (df.index.hour >= s) & (df.index.hour < e)
            diff = np.diff(mask.astype(int), prepend=0)
            starts = np.where(diff == 1)[0]
            ends = np.where(diff == -1)[0]
            if len(starts) > len(ends): ends = np.append(ends, len(df)-1)
            for st, en in zip(starts, ends):
                res.append({"start": df.index[st], "end": df.index[en], "color": c, "name": name})
        return res

    def get_current_status(self, df):
        """Simplified status tracker."""
        fvgs = self.find_fvgs(df)
        active = fvgs[fvgs['fvg_type'].notna() & (fvgs['fvg_type'] != 0)]
        if active.empty: return "No Active FVG Detected"
        
        last = active.iloc[-1]
        f_idx = df.index.get_loc(last.name)
        
        shl = self.swing_highs_lows(df)
        ith_itl = self.ith_itl(df, shl, fvgs)
        
        sub = ith_itl.iloc[f_idx:].dropna()
        if sub.empty: return "🔭 Waiting for Internal ITH/ITL formation..."
        
        price = shl.at[sub.index[-1], 'Level']
        is_long = sub.iloc[-1] == -1
        
        after = df.iloc[df.index.get_loc(sub.index[-1])+1:]
        if is_long:
            sweep = after[(after['Low'] < price) & (after['Close'] > price)]
        else:
            sweep = after[(after['High'] > price) & (after['Close'] < price)]
            
        if not sweep.empty: return "💥 Liquidity Swept! Watching for iFVG Inversion..."
        return f"🎯 Level Established ({price:.2f}). Waiting for Sweep..."

    def find_internal_fractals(self, df, fvg_idx, top, bottom, fvg_type):
        return []

    def detect_sweeps(self, df, fractal, fvg_type):
        return []

    def detect_inversion(self, df, fvg_idx, top, bottom, fvg_type, sweeps):
        return None

    def get_consolidated_signals(self, df, fvg_idx, top, bottom, fvg_type):
        return None
