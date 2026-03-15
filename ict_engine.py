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

    def _is_in_killzone(self, time):
        hour = time.hour
        # ITL Standard: London 07-12, NY 13-17
        return (7 <= hour < 12) or (13 <= hour < 17)

    def _get_ifvg_count_in_leg(self, sweep, exec_df):
        # Counts iFVGs in the manipulation leg
        ifvg = self.find_ifvgs(exec_df)
        mask = (ifvg.index >= sweep['time']) & \
               (ifvg.index <= sweep['time'] + pd.Timedelta(minutes=90)) & \
               (ifvg['type'] != 0)
        
        # Further filter iFVGs that fall within the price bounds of the sweep candle
        relevant_ifvgs = ifvg[mask]
        in_bounds = relevant_ifvgs[
            (relevant_ifvgs['btm'] <= sweep['high']) & 
            (relevant_ifvgs['top'] >= sweep['low'])
        ]
        return len(in_bounds)

    def compute_mtf_signals(self, primary_df, htf_dfs, timeframe):
        htf_levels_list = []
        htf_sweeps = []
        now = primary_df.index[-1]
        cutoff = now - pd.Timedelta(days=30)
        
        # 1. Gather HTF Sweeps
        for tf, hdf in htf_dfs.items():
            if hdf.empty: continue
            fvg_data = self.find_fvgs(hdf)
            shl_data = self.swing_highs_lows(hdf, swing_length=5)
            ith_data = self.ith_itl(hdf, shl_data, fvg_data)
            for t, row in ith_data.dropna(subset=['Level']).iterrows():
                if t < cutoff: continue
                val, price, sweep_idx = row['Type'], row['Level'], row['SweptIndex']
                if not pd.isna(sweep_idx):
                    end_time = hdf.index[int(sweep_idx)]
                    htf_levels_list.append({'time': t, 'end_time': end_time, 'price': price, 'type': 'ITH' if val == 1 else 'ITL', 'tf': tf, 'is_swept': True})
                    htf_sweeps.append({'time': end_time, 'type': 'short' if val == 1 else 'long', 'high': hdf.loc[end_time, 'High'], 'low': hdf.loc[end_time, 'Low']})

        # 2. Pipeline Cascade: M1 -> M3 -> M5 -> H1
        # Store entries by timeframe
        entries_by_tf = {tf: [] for tf in ['M1', 'M3', 'M5', 'H1']}
        sweeps_df = pd.DataFrame(htf_sweeps)
        if not sweeps_df.empty:
            sweeps_df = sweeps_df.sort_values('time').drop_duplicates('time')
            consumed_sweeps = set()
            timeframe_cascade = ['M1', 'M3', 'M5', 'H1']
            for tf in timeframe_cascade:
                exec_df = htf_dfs.get(tf, primary_df)
                if len(exec_df) == 0: continue
                
                # Check killzone if applicable
                ts = pd.Timestamp(exec_df.index[-1])
                if not self._is_in_killzone(ts): continue
                
                # Validation logic
                for _, sweep in sweeps_df.iterrows():
                    if sweep['time'] in consumed_sweeps: continue
                    if self._get_ifvg_count_in_leg(sweep, exec_df) == 1:
                        entry = {'time': sweep['time'], 'price': exec_df.loc[sweep['time'], 'Close'], 'type': str(sweep['type']).upper()}
                        entries_by_tf[tf].append(entry)
                        consumed_sweeps.add(sweep['time'])
                        
        # FIX: Ensure htf_levels_list are populated regardless of signals
        if timeframe in ['M1', 'M5']:
            htf_levels_list = sorted(htf_levels_list, key=lambda x: x['time'], reverse=True)[:3]
                        
        return {'entries_by_tf': entries_by_tf, 'htf_levels': htf_levels_list}




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

    def prepare_plot_data(self, df, timeframe, htf_levels, global_entries):
        """
        Orchestrator: Pre-computes all structural levels, signals, and markers.
        This follows the 'Compute-First' ITT-Analytics architecture.
        """
        markers = []
        extra_series = []
        time_offset = 3600 # UTC+1

        # 1. Plot Structural Levels
        for level in htf_levels:
            if pd.isna(level['price']): continue
            price_val = float(level['price'])
            start_t = int(level['time'].timestamp()) + time_offset
            end_t_val = int(level['end_time'].timestamp()) + time_offset
            color = "rgba(155, 89, 182, 0.9)" if level['type'] == 'ITH' else "rgba(52, 152, 219, 0.9)"
            is_htf = level['tf'] != timeframe
            if is_htf: color = color.replace("0.9", "0.4")
            
            extra_series.append({
                "type": "Line",
                "data": [{"time": start_t, "value": price_val}, {"time": end_t_val, "value": price_val}],
                "options": {"color": color, "lineWidth": 2 if not is_htf else 1, "lineStyle": 0 if not is_htf else 2, "title": f"[{level['tf']}] {level['type']}"}
            })
            
            tf_label = "Int" if level['tf'] in ['M1', 'M3', 'M5'] else "Ext"
            label = f"[{level['tf']}] {tf_label} {level['type']}"
            markers.append({
                "time": start_t,
                "position": "aboveBar" if level['type'] == 'ITH' else "belowBar",
                "color": color,
                "shape": "arrowDown" if level['type'] == 'ITH' else "arrowUp",
                "text": label
            })
            
            if level.get('is_swept'):
                markers.append({
                    "time": end_t_val,
                    "position": "aboveBar" if level['type'] == 'ITH' else "belowBar",
                    "color": "#f1c40f",
                    "shape": "circle",
                    "text": f"[{level['tf']}] SWEEP"
                })

        # 2. Plot Global Entries
        for entry in global_entries:
            aligned_time = int(entry['time'].timestamp()) + time_offset
            markers.append({
                "time": aligned_time,
                "position": "belowBar" if entry['type'] == 'LONG' else "aboveBar",
                "color": "#2ecc71" if entry['type'] == 'LONG' else "#e74c3c",
                "shape": "arrowUp" if entry['type'] == 'LONG' else "arrowDown",
                "text": entry['type']
            })
            
        return {'markers': markers[-50:], 'extra_series': extra_series}

    def get_current_status(self, df): return "Terminal Active | Monitoring Session Levels"
