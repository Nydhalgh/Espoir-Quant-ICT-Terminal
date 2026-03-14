
import unittest
import pandas as pd
import numpy as np
from ict_engine import ICTEngine
from datetime import datetime

class TestSMC(unittest.TestCase):
    def setUp(self):
        self.engine = ICTEngine(fractal_period=1)
        # Create 200 candles across 50 periods (to allow for fractal detection)
        rng = pd.date_range("2024-01-01", periods=200, freq="1min")
        self.df = pd.DataFrame({
            "Open": np.random.rand(len(rng))*10+1000,
            "High": np.random.rand(len(rng))*10+1005,
            "Low": np.random.rand(len(rng))*10+995,
            "Close": np.random.rand(len(rng))*10+1000,
        }, index=rng)

    def test_fvg_exists(self):
        """Test if FVG detection adds necessary columns."""
        df = self.engine.find_fvgs(self.df)
        self.assertTrue("fvg_type" in df.columns)
        self.assertTrue(df["fvg_type"].isnull().sum() < len(df))

    def test_internal_fractals_detection(self):
        """Test if internal fractals are found within a dummy FVG."""
        df = self.engine.find_fvgs(self.df)
        # Find the first FVG to test against
        fvg_row = df[df['fvg_type'] != 0].iloc[0]
        fvg_index = df.index.get_loc(fvg_row.name)
        
        frs = self.engine.find_internal_fractals(df, fvg_index, fvg_row['fvg_top'], fvg_row['fvg_bottom'], fvg_row['fvg_type'])
        # Assert it returns a list, even if empty, it shouldn't crash
        self.assertIsInstance(frs, list)

if __name__ == "__main__":
    unittest.main()
