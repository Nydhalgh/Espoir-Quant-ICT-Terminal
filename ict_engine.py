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
        """
        Refined MTF Logic:
        - Uses 5-candle fractals (less noise).
        - Consumes sweeps (1 trade per setup).
        - Strict 60-minute window between sweep and entry.
        """
        htf_levels_list = []
        htf_sweeps = []
        now = primary_df.index[-1]
        cutoff = now - pd.Timedelta(days=3)
        
        exec_df = htf_dfs.get('M1', primary_df if timeframe == 'M1' else pd.DataFrame())
        if exec_df.empty:
            exec_df = primary_df 
            
        current_price = exec_df['Close'].iloc[-1]

        # 1. Identify all Structural Levels (H1, M30, M15)
        for tf, hdf in htf_dfs.items():
            if hdf.empty or tf == 'M1': continue
            
            fvg_data = self.find_fvgs(hdf)
            shl_data = self.swing_highs_lows(hdf, swing_length=5)
            ith_data = self.ith_itl(hdf, shl_data, fvg_data)
            
            active_levels = ith_data.dropna(subset=['Level'])
            
            for t, row in active_levels.iterrows():
                if t < cutoff: continue
                
                val = row['Type']
                price = row['Level']
                sweep_idx = row['SweptIndex']
                is_swept = not pd.isna(sweep_idx)
                
                end_time = hdf.index[int(sweep_idx)] if is_swept else now
                
                dist_pct = abs(price - current_price) / current_price
                is_recently_swept = is_swept and (now - end_time) < pd.Timedelta(hours=24)
                is_close_active = not is_swept and dist_pct < 0.015
                
                if is_recently_swept or is_close_active:
                    htf_levels_list.append({
                        'time': t, 'end_time': end_time, 'price': price, 
                        'type': 'ITH' if val == 1 else 'ITL', 'tf': tf, 'is_swept': is_swept
                    })
                    
                if is_swept:
                    htf_sweeps.append({
                        'time': end_time, 
                        'type': 'short' if val == 1 else 'long',
                        'high': hdf.loc[end_time, 'High'],
                        'low': hdf.loc[end_time, 'Low']
                    })

        # 2. Local Levels (Primary TF) filtering applies here too
        p_fvg = self.find_fvgs(primary_df)
        p_shl = self.swing_highs_lows(primary_df, swing_length=5)
        p_ith_data = self.ith_itl(primary_df, p_shl, p_fvg)
        
        for t, row in p_ith_data.dropna(subset=['Level']).iterrows():
            if t < cutoff: continue
            
            val = row['Type']
            price = row['Level']
            sweep_idx = row['SweptIndex']
            is_swept = not pd.isna(sweep_idx)
            
            end_time = primary_df.index[int(sweep_idx)] if is_swept else now
            dist_pct = abs(price - current_price) / current_price
            
            is_recently_swept = is_swept and (now - end_time) < pd.Timedelta(hours=24)
            is_close_active = not is_swept and dist_pct < 0.015
            
            if is_recently_swept or is_close_active:
                if not any(l['price'] == price for l in htf_levels_list):
                    htf_levels_list.append({
                        'time': t, 'end_time': end_time, 'price': price, 
                        'type': 'ITH' if val == 1 else 'ITL', 'tf': timeframe, 'is_primary': True, 'is_swept': is_swept
                    })

        # 3. M1/M5 Entry Confirmation (STRICT One-Trade-Per-Sweep Logic)
        global_entries = []
        if not exec_df.empty and htf_sweeps:
            exec_ifvgs = self.find_ifvgs(exec_df)
            active_ifvgs = exec_ifvgs[exec_ifvgs['type'] != 0]
            
            sweeps_df = pd.DataFrame(htf_sweeps).sort_values('time').drop_duplicates('time')
            
            consumed_sweeps = set()
            
            for i_time, i_row in active_ifvgs.iterrows():
                # Ensure i_time is a Timestamp
                ts = pd.Timestamp(i_time)
                hour = ts.hour
                
                is_london = 7 <= hour < 12
                is_ny = 13 <= hour < 17
                if not (is_london or is_ny):
                    continue
                    
                lookback = ts - pd.Timedelta(minutes=90)
                recent_sweeps = sweeps_df[(sweeps_df['time'] < ts) & (sweeps_df['time'] >= lookback)]
                
                if recent_sweeps.empty: continue
                
                if i_row['type'] == 1:
                    long_sweeps = recent_sweeps[
                        (recent_sweeps['type'] == 'long') &
                        (recent_sweeps['low'] <= exec_df.loc[i_time, 'Close']) &
                        (recent_sweeps['high'] >= exec_df.loc[i_time, 'Close'])
                    ]
                    unconsumed = [s for s in long_sweeps['time'] if s not in consumed_sweeps]
                    
                    if unconsumed:
                        global_entries.append({
                            'time': i_time, 'price': exec_df.loc[i_time, 'Close'], 'type': 'LONG'
                        })
                        consumed_sweeps.add(unconsumed[-1])
                
                elif i_row['type'] == -1:
                    short_sweeps = recent_sweeps[
                        (recent_sweeps['type'] == 'short') &
                        (recent_sweeps['low'] <= exec_df.loc[i_time, 'Close']) &
                        (recent_sweeps['high'] >= exec_df.loc[i_time, 'Close'])
                    ]
                    unconsumed = [s for s in short_sweeps['time'] if s not in consumed_sweeps]
                    
                    if unconsumed:
                        global_entries.append({
                            'time': i_time, 'price': exec_df.loc[i_time, 'Close'], 'type': 'SHORT'
                        })
                        consumed_sweeps.add(unconsumed[-1])
                        
        # FIX: Filter levels for low timeframes (M1, M5) to show only the 3 most recent
        if timeframe in ['M1', 'M5']:
            htf_levels_list = sorted(htf_levels_list, key=lambda x: x['time'], reverse=True)[:3]
                        
        return {'global_entries': global_entries, 'htf_levels': htf_levels_list}

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
