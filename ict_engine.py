import pandas as pd
import numpy as np

class ICTEngine:
    def __init__(self, fractal_period=1):
        """
        fractal_period: 1 for 3-candle fractal, 2 for 5-candle fractal.
        We'll use 1 by default (3-candle fractal).
        """
        self.fractal_period = fractal_period

    def find_fvgs(self, df):
        """
        Detects Bullish and Bearish Fair Value Gaps.
        Bullish: Low(n) > High(n-2)
        Bearish: High(n) < Low(n-2)
        """
        df = df.copy()
        df['fvg_type'] = 0  # 1 for Bullish, -1 for Bearish
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan
        
        # Bullish FVG
        bullish_fvg = df['Low'] > df['High'].shift(2)
        df.loc[bullish_fvg, 'fvg_type'] = 1
        df.loc[bullish_fvg, 'fvg_top'] = df['Low']
        df.loc[bullish_fvg, 'fvg_bottom'] = df['High'].shift(2)
        
        # Bearish FVG
        bearish_fvg = df['High'] < df['Low'].shift(2)
        df.loc[bearish_fvg, 'fvg_type'] = -1
        df.loc[bearish_fvg, 'fvg_top'] = df['Low'].shift(2)
        df.loc[bearish_fvg, 'fvg_bottom'] = df['High']
        
        return df

    def find_internal_fractals(self, df, fvg_index, fvg_top, fvg_bottom, fvg_type):
        """
        Finds ITH/ITL that form strictly INSIDE the FVG price range after its creation.
        """
        search_df = df.iloc[fvg_index+1:]
        internal_fractals = []
        
        for i in range(self.fractal_period, len(search_df) - self.fractal_period):
            idx = i + fvg_index + 1
            curr_candle = df.iloc[idx]
            
            is_fractal = True
            for p in range(1, self.fractal_period + 1):
                if fvg_type == -1: # Bearish FVG, looking for ITH (High)
                    if df.iloc[idx-p]['High'] >= curr_candle['High'] or df.iloc[idx+p]['High'] >= curr_candle['High']:
                        is_fractal = False
                        break
                elif fvg_type == 1: # Bullish FVG, looking for ITL (Low)
                    if df.iloc[idx-p]['Low'] <= curr_candle['Low'] or df.iloc[idx+p]['Low'] <= curr_candle['Low']:
                        is_fractal = False
                        break
            
            if is_fractal:
                price = curr_candle['High'] if fvg_type == -1 else curr_candle['Low']
                if fvg_bottom < price < fvg_top:
                    internal_fractals.append({'index': idx, 'price': price, 'type': 'ITH' if fvg_type == -1 else 'ITL'})
                    
        return internal_fractals

    def detect_sweeps(self, df, internal_fractal, fvg_type):
        """
        Detects if price sweeps the internal fractal.
        """
        start_idx = internal_fractal['index'] + 1
        fractal_price = internal_fractal['price']
        
        sweeps = []
        for i in range(start_idx, len(df)):
            if fvg_type == -1: # Bearish FVG, sweeping ITH
                if df.iloc[i]['High'] > fractal_price and df.iloc[i]['Close'] < fractal_price:
                    sweeps.append(i)
            elif fvg_type == 1: # Bullish FVG, sweeping ITL
                if df.iloc[i]['Low'] < fractal_price and df.iloc[i]['Close'] > fractal_price:
                    sweeps.append(i)
        return sweeps

    def detect_inversion(self, df, fvg_index, fvg_top, fvg_bottom, fvg_type, sweep_indices):
        """
        Detects if price closes through the FVG (Inversion) after a sweep.
        """
        if not sweep_indices:
            return None
            
        last_sweep_idx = sweep_indices[-1]
        for i in range(last_sweep_idx + 1, len(df)):
            if fvg_type == -1: # Bearish FVG -> Bullish Inversion
                if df.iloc[i]['Close'] > fvg_top:
                    return i # Entry Index
            elif fvg_type == 1: # Bullish FVG -> Bearish Inversion
                if df.iloc[i]['Close'] < fvg_bottom:
                    return i # Entry Index
        return None

    def get_consolidated_signals(self, df, fvg_index, fvg_top, fvg_bottom, fvg_type):
        """
        Consolidated signal detection for a single FVG.
        """
        search_df = df.iloc[fvg_index+1:]
        extreme_fractal = None
        has_sweep = False
        sweep_idx = None
        
        for i in range(self.fractal_period, len(search_df) - self.fractal_period):
            idx = i + fvg_index + 1
            curr_candle = df.iloc[idx]
            
            is_fractal = True
            for p in range(1, self.fractal_period + 1):
                if fvg_type == -1: # Bearish FVG
                    if df.iloc[idx-p]['High'] >= curr_candle['High'] or df.iloc[idx+p]['High'] >= curr_candle['High']:
                        is_fractal = False
                        break
                elif fvg_type == 1: # Bullish FVG
                    if df.iloc[idx-p]['Low'] <= curr_candle['Low'] or df.iloc[idx+p]['Low'] <= curr_candle['Low']:
                        is_fractal = False
                        break
            
            if is_fractal:
                price = curr_candle['High'] if fvg_type == -1 else curr_candle['Low']
                if fvg_bottom < price < fvg_top:
                    if extreme_fractal is None:
                        extreme_fractal = {'price': price, 'index': idx}
                    else:
                        if fvg_type == -1: # Bearish FVG, extreme is highest
                            if price > extreme_fractal['price']:
                                extreme_fractal = {'price': price, 'index': idx}
                        elif fvg_type == 1: # Bullish FVG, extreme is lowest
                            if price < extreme_fractal['price']:
                                extreme_fractal = {'price': price, 'index': idx}
            
            if extreme_fractal is not None:
                if fvg_type == -1:
                    if curr_candle['High'] > extreme_fractal['price'] and curr_candle['Close'] < extreme_fractal['price']:
                        has_sweep = True
                        sweep_idx = idx
                elif fvg_type == 1:
                    if curr_candle['Low'] < extreme_fractal['price'] and curr_candle['Close'] > extreme_fractal['price']:
                        has_sweep = True
                        sweep_idx = idx
            
            if has_sweep and extreme_fractal is not None:
                if fvg_type == -1:
                    if curr_candle['Close'] > fvg_top:
                        return {
                            'sweep_index': sweep_idx,
                            'entry_index': idx,
                            'sl_price': extreme_fractal['price'],
                            'extreme_price': extreme_fractal['price']
                        }
                elif fvg_type == 1:
                    if curr_candle['Close'] < fvg_bottom:
                        return {
                            'sweep_index': sweep_idx,
                            'entry_index': idx,
                            'sl_price': extreme_fractal['price'],
                            'extreme_price': extreme_fractal['price']
                        }
                        
            if fvg_type == -1:
                if curr_candle['Close'] < fvg_bottom - (fvg_top - fvg_bottom) * 2:
                    break
            elif fvg_type == 1:
                if curr_candle['Close'] > fvg_top + (fvg_top - fvg_bottom) * 2:
                    break
            
        return None

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
