import pandas as pd
import numpy as np
from ict_engine import ICTEngine

def test_fvg_detection():
    # Create a mock dataframe with a bullish FVG
    # Candle 0: High 100, Low 90
    # Candle 1: High 110, Low 105
    # Candle 2: High 120, Low 102
    # Gap between Candle 0 High (100) and Candle 2 Low (102) -> 2 point gap
    data = {
        'Open':  [95, 106, 115, 101, 103],
        'High':  [100, 110, 120, 105, 108],
        'Low':   [90, 105, 102, 98, 99],
        'Close': [98, 108, 110, 102, 105]
    }
    df = pd.DataFrame(data)
    engine = ICTEngine()
    
    df_result = engine.find_fvgs(df)
    
    # Check if FVG detected at index 1
    assert df_result.iloc[1]['fvg_type'] == 1
    assert df_result.iloc[1]['fvg_top'] == 102
    assert df_result.iloc[1]['fvg_bottom'] == 100
    print("FVG Detection Test Passed!")

def test_internal_fractal_and_sweep():
    # Create a mock dataframe with a Bearish FVG and internal ITH sweep
    # Candle 0: H: 150, L: 140
    # Candle 1: H: 135, L: 130
    # Candle 2: H: 138, L: 125  -> Bearish FVG (H2 < L0: 138 < 140)
    # Candle 3: H: 138, L: 137  -> Buffer candle
    # Candle 4: H: 139, L: 138  -> Potential Fractal High (ITH) inside 138-140
    # Candle 5: H: 138.5, L: 138-> Confirmation candle for fractal high
    # Candle 6: H: 139.5, L: 138-> Sweep of 139 (High 6 > High 4 and Close 6 < High 4)
    # Candle 7: H: 142, L: 141  -> Close above 140 (Inversion)
    
    data = {
        'Open':  [145, 132, 128, 137.5, 138.5, 138.2, 139, 141.5],
        'High':  [150, 135, 138, 138, 139, 138.5, 139.5, 142],
        'Low':   [140, 130, 125, 137, 138, 138, 138.2, 141],
        'Close': [142, 131, 127, 137.8, 138.8, 138.3, 138.9, 141.8]
    }
    df = pd.DataFrame(data)
    engine = ICTEngine(fractal_period=1)
    
    df_fvg = engine.find_fvgs(df)
    fvg_idx = 2
    fvg_top = 140
    fvg_bottom = 138
    fvg_type = -1 # Bearish
    
    # 1. Find Internal Fractals
    fractals = engine.find_internal_fractals(df, fvg_idx, fvg_top, fvg_bottom, fvg_type)
    assert len(fractals) > 0
    assert fractals[0]['price'] == 139
    print("Internal Fractal Detection Test Passed!")
    
    # 2. Detect Sweeps
    sweeps = engine.detect_sweeps(df, fractals[0], fvg_type)
    assert len(sweeps) > 0
    assert sweeps[0] == 6
    print("Sweep Detection Test Passed!")
    
    # 3. Detect Inversion
    entry = engine.detect_inversion(df, fvg_idx, fvg_top, fvg_bottom, fvg_type, sweeps)
    assert entry == 7
    print("Inversion Detection Test Passed!")

if __name__ == "__main__":
    test_fvg_detection()
    test_internal_fractal_and_sweep()
