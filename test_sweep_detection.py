import pandas as pd
import numpy as np
from ict_engine import ICTEngine

def test_sweep_detection():
    # Create sample data
    # We need enough candles for swing high calculation (swing_length=5)
    data = {
        'High': [110, 100, 95, 80, 92, 75, 93, 120],
        'Low':  [105, 90, 85, 70, 82, 65, 83, 110],
        'Open': [108, 98, 93, 78, 90, 73, 91, 115],
        'Close':[107, 92, 88, 72, 89, 70, 92, 118]
    }
    index = pd.date_range(start='2023-01-01', periods=8, freq='H')
    df = pd.DataFrame(data, index=index)
    
    engine = ICTEngine(fractal_period=1)
    
    # Need lowercase columns for find_fvgs
    df_lower = df.rename(columns=str.lower)
    
    # 1. Find FVGs
    fvg_data = engine.find_fvgs(df_lower)
    
    # 2. Find Swings
    shl_data = engine.swing_highs_lows(df, swing_length=1) # Using small swing length for demo
    
    # 3. Detect ITH/ITL and Sweeps
    ith_itl_data = engine.ith_itl(df, shl_data, fvg_data)
    
    print("FVG Data:\n", fvg_data[['fvg_type', 'fvg_top', 'fvg_bottom', 'mitigated_index']])
    print("\nSwing High/Low Data:\n", shl_data)
    print("\nITH/ITL Data:\n", ith_itl_data)
    
    # Validation
    # In our data:
    # C1 (idx 1): H=100, L=90
    # C2 (idx 2): H=95, L=85
    # C3 (idx 3): H=80, L=70
    # Bearish FVG between C1 and C3: top=90, btm=80
    
    # C4 (idx 4): H=92. This is outside the FVG top (90). Not an ITH?
    # Wait, let's adjust FVG to make C4 an ITH.
    # C1: H=100, L=95
    # C2: H=90, L=85
    # C3: H=80, L=75
    # FVG: 95 - 80.
    
    # Let's adjust data for better test case.
    pass

def test_sweep_detection_refined():
    # C0: H=110
    # C1: H=100, L=95
    # C2: H=90,  L=85  <- Swing High at 90 (if neighbors are < 90)
    # C3: H=80,  L=75
    # C4: H=70,  L=65
    # C5: H=92,  L=80  <- Sweep of C2
    
    # Wait, need swing length=1, so C2 H=90 must be > C1 H and > C3 H.
    # C1 H=80, C2 H=90, C3 H=85. Yes.
    
    data = {
        'High': [110, 80, 90, 85, 70, 92, 120],
        'Low':  [105, 75, 85, 80, 65, 80, 110],
        'Open': [108, 78, 88, 83, 68, 85, 115],
        'Close':[107, 76, 86, 81, 67, 86, 118]
    }
    index = pd.date_range(start='2023-01-01', periods=7, freq='H')
    df = pd.DataFrame(data, index=index)
    
    engine = ICTEngine(fractal_period=1)
    df_lower = df.rename(columns=str.lower)
    
    fvg_data = engine.find_fvgs(df_lower)
    shl_data = engine.swing_highs_lows(df, swing_length=1)
    
    # Debug inside ith_itl
    f_types, f_tops, f_btms, f_mits = fvg_data["fvg_type"].values, fvg_data["fvg_top"].values, fvg_data["fvg_bottom"].values, fvg_data["mitigated_index"].values
    f_indices = np.where(~np.isnan(f_types))[0]
    s_indices = np.where(~np.isnan(shl_data['HighLow'].values))[0]
    print(f"DEBUG: FVG indices: {f_indices}, Swing indices: {s_indices}")
    
    for fi in f_indices:
        mit = int(f_mits[fi]) if not np.isnan(f_mits[fi]) and f_mits[fi] > 0 else len(df)
        targets = s_indices[(s_indices > fi) & (s_indices < mit)]
        print(f"DEBUG: FVG index {fi}, mitigation {mit}, targets {targets}")
    
    ith_itl_data = engine.ith_itl(df, shl_data, fvg_data)
    
    print("FVG:\n", fvg_data[['fvg_type', 'fvg_top', 'fvg_bottom']])
    print("\nSHL:\n", shl_data)
    print("\nITH/ITL:\n", ith_itl_data)
    
    # Validate ITH detection (Type 1)
    ith_rows = ith_itl_data[ith_itl_data['Type'] == 1]
    assert len(ith_rows) > 0, "ITH not detected"
    
    # Validate Sweep detection
    swept_idx = ith_rows.iloc[0]['SweptIndex']
    assert not np.isnan(swept_idx), "Sweep not detected"
    assert df.index[int(swept_idx)] == df.index[5], "Sweep index incorrect"
    
    print("\nTest passed: ITH and Sweep correctly identified.")

if __name__ == "__main__":
    test_sweep_detection_refined()
