import pandas as pd
import numpy as np

class ICTEngine:
    def __init__(self, fractal_period=1):
        self.fractal_period = fractal_period

    def find_fvgs(self, df):
        """Strict SMC FVG: Gap between candle 1 and 3."""
        ohlc = df.rename(columns=str.lower)
        n = len(ohlc)
        high = ohlc["high"].values
        low = ohlc["low"].values
        
        fvg = np.full(n, np.nan)
        top = np.full(n, np.nan)
        btm = np.full(n, np.nan)
        
        # Bearish FVG
        bear_mask = (low[:-2] > high[2:])
        fvg[1:-1] = np.where(bear_mask, -1, fvg[1:-1])
        top[1:-1] = np.where(bear_mask, low[:-2], top[1:-1])
        btm[1:-1] = np.where(bear_mask, high[2:], btm[1:-1])
        
        # Bullish FVG
        bull_mask = (high[:-2] < low[2:])
        fvg[1:-1] = np.where(bull_mask, 1, fvg[1:-1])
        top[1:-1] = np.where(bull_mask, low[2:], top[1:-1])
        btm[1:-1] = np.where(bull_mask, high[:-2], btm[1:-1])
        
        # Mitigation: Full traverse (Standard ICT)
        mitigated_index = np.zeros(n, dtype=np.int32)
        indices = np.where(~np.isnan(fvg))[0]
        for i in indices:
            search = high[i+2:] if fvg[i] == -1 else low[i+2:]
            mask = search > top[i] if fvg[i] == -1 else search < btm[i]
            if np.any(mask):
                mitigated_index[i] = np.flatnonzero(mask)[0] + i + 2
        
        res = df.copy()
        res['fvg_type'] = fvg
        res['fvg_top'] = top
        res['fvg_bottom'] = btm
        res['mitigated_index'] = np.where(np.isnan(fvg), np.nan, mitigated_index)
        return res

    def ith_itl(self, ohlc, swing_highs_lows, fvg_data):
        """
        ITH: Swing High inside active Bearish FVG.
        ITL: Swing Low inside active Bullish FVG.
        """
        n = len(ohlc)
        highs, lows = ohlc['High'].values, ohlc['Low'].values
        shl_val, shl_price = swing_highs_lows["HighLow"].values, swing_highs_lows["Level"].values
        f_types, f_tops, f_btms, f_mits = fvg_data["fvg_type"].values, fvg_data["fvg_top"].values, fvg_data["fvg_bottom"].values, fvg_data["mitigated_index"].values
        
        res_types, res_levels = np.zeros(n), np.full(n, np.nan)
        swept_indices = np.zeros(n, dtype=np.int32)
        
        f_indices = np.where(~np.isnan(f_types))[0]
        s_indices = np.where(~np.isnan(shl_val))[0]
        
        for fi in f_indices:
            f_type, top, btm = f_types[fi], f_tops[fi], f_btms[fi]
            mit = int(f_mits[fi]) if not np.isnan(f_mits[fi]) and f_mits[fi] > 0 else n
            
            # Find swings within this FVG window
            targets = s_indices[(s_indices > fi) & (s_indices < mit)]
            for si in targets:
                if f_type == -1 and shl_val[si] == 1: # ITH candidate
                    if btm <= shl_price[si] <= top:
                        res_types[si], res_levels[si] = 1, shl_price[si]
                        sw = np.where(highs[si+1:] > shl_price[si])[0]
                        if len(sw) > 0: swept_indices[si] = sw[0] + si + 1
                elif f_type == 1 and shl_val[si] == -1: # ITL candidate
                    if btm <= shl_price[si] <= top:
                        res_types[si], res_levels[si] = -1, shl_price[si]
                        sw = np.where(lows[si+1:] < shl_price[si])[0]
                        if len(sw) > 0: swept_indices[si] = sw[0] + si + 1
        
        return pd.DataFrame({"Type": res_types, "Level": res_levels, "SweptIndex": swept_indices}, index=ohlc.index)

    def find_ifvgs(self, df):
        """Inversion FVG: Bullish FVG closed below, or Bearish closed above."""
        fvg_df = self.find_fvgs(df)
        n = len(df)
        closes, tops, btms = df['Close'].values, fvg_df['fvg_top'].values, fvg_df['fvg_bottom'].values
        types = fvg_df['fvg_type'].values
        
        ifvg = np.zeros(n)
        for i in np.where(~np.isnan(types))[0]:
            viol = np.where(closes[i+1:] < btms[i])[0] if types[i] == 1 else np.where(closes[i+1:] > tops[i])[0]
            if len(viol) > 0:
                v_idx = viol[0] + i + 1
                ifvg[v_idx] = -1 if types[i] == 1 else 1 # Invert type
        return pd.DataFrame({'type': ifvg, 'top': tops, 'btm': btms}, index=df.index)

    def compute_mtf_signals(self, primary_df, htf_dfs, timeframe):
        """Unified MTF Signal Engine with finite visibility and cross-TF filters."""
        now = primary_df.index[-1]
        cutoff = now - pd.Timedelta(days=3)
        levels_to_draw, entry_markers = [], []
        
        # 1. Structural Hierarchy Analysis
        # Only show levels >= current timeframe
        tf_rank = {"M1": 0, "M5": 1, "M15": 2, "M30": 3, "H1": 4}
        curr_rank = tf_rank.get(timeframe, 0)
        
        # Include primary in analysis
        all_dfs = htf_dfs.copy()
        all_dfs[timeframe] = primary_df
        
        htf_sweeps = []
        for tf, hdf in all_dfs.items():
            if hdf.empty or tf_rank.get(tf, 0) < curr_rank: continue
            
            fvg = self.find_fvgs(hdf)
            shl = self.swing_highs_lows(hdf, swing_length=5)
            ith_itl = self.ith_itl(hdf, shl, fvg)
            
            for t, row in ith_itl.dropna(subset=['Level']).iterrows():
                if t < cutoff: continue
                is_swept = row['SweptIndex'] > 0
                end_t = hdf.index[int(row['SweptIndex'])] if is_swept else now
                
                # Filter: Unswept or very recent sweep (4h)
                if not is_swept or end_t > now - pd.Timedelta(hours=4):
                    levels_to_draw.append({
                        'time': t, 'end_time': end_t, 'price': row['Level'], 
                        'type': 'ITH' if row['Type'] == 1 else 'ITL', 'tf': tf, 'is_swept': is_swept
                    })
                
                if is_swept and tf != timeframe: 
                    htf_sweeps.append({'time': end_t, 'type': 'short' if row['Type'] == 1 else 'long'})

        # 2. M1 Execution Logic
        exec_df = htf_dfs.get('M1', primary_df if timeframe == 'M1' else pd.DataFrame())
        if not exec_df.empty and htf_sweeps:
            ifvgs = self.find_ifvgs(exec_df)
            sweeps_df = pd.DataFrame(htf_sweeps)
            
            for i_t, i_row in ifvgs[ifvgs['type'] != 0].iterrows():
                # Session: 7:00 - 20:00 CET
                if not (7 <= i_t.hour < 20): continue
                
                recent_sweeps = sweeps_df[(sweeps_df['time'] < i_t) & (sweeps_df['time'] > i_t - pd.Timedelta(hours=6))]
                is_long = i_row['type'] == 1 and (recent_sweeps['type'] == 'long').any()
                is_short = i_row['type'] == -1 and (recent_sweeps['type'] == 'short').any()
                
                if is_long or is_short:
                    entry_markers.append({'time': i_t, 'type': 'LONG' if is_long else 'SHORT'})

        return {'global_entries': entry_markers, 'htf_levels': levels_to_draw}

    def swing_highs_lows(self, ohlc, swing_length=5):
        high, low = ohlc['High'].values, ohlc['Low'].values
        n = len(ohlc)
        shl, level = np.full(n, np.nan), np.full(n, np.nan)
        for i in range(swing_length, n - swing_length):
            if high[i] == np.max(high[i-swing_length:i+swing_length+1]): shl[i], level[i] = 1, high[i]
            if low[i] == np.min(low[i-swing_length:i+swing_length+1]): shl[i], level[i] = -1, low[i]
        return pd.DataFrame({"HighLow": shl, "Level": level}, index=ohlc.index)

    def get_sessions(self, df):
        sessions = {"Asian": (0, 4, "rgba(41,98,255,0.05)"), "London": (7, 15, "rgba(255,152,0,0.05)"), "NY": (12, 20, "rgba(76,175,80,0.05)")}
        res = []
        for name, (s, e, c) in sessions.items():
            mask = (df.index.hour >= s) & (df.index.hour < e)
            diff = np.diff(mask.astype(int), prepend=0)
            starts, ends = np.where(diff == 1)[0], np.where(diff == -1)[0]
            if len(starts) > len(ends): ends = np.append(ends, len(df)-1)
            for st, en in zip(starts, ends): res.append({"start": df.index[st], "end": df.index[en], "color": c, "name": name})
        return res

    def get_current_status(self, df): return "Terminal Active | Monitoring Session Levels"
