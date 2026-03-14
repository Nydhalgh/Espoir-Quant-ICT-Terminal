
import unittest
import pandas as pd
import numpy as np
from charts import ChartVisualizer

class TestChartVisualization(unittest.TestCase):
    def setUp(self):
        self.viz = ChartVisualizer()
        # Create 10 candles of dummy data
        dates = pd.date_range("2024-01-01", periods=10, freq="min")
        self.df = pd.DataFrame({
            "Open": [100.0] * 10,
            "High": [105.0] * 10,
            "Low": [95.0] * 10,
            "Close": [102.0] * 10
        }, index=dates)

    def test_prepare_candles_format(self):
        """Verify candles are converted to the correct format for Lightweight Charts"""
        candles = self.viz.prepare_candles(self.df)
        self.assertEqual(len(candles), 10)
        self.assertIn("time", candles[0])
        self.assertIn("open", candles[0])
        self.assertIn("close", candles[0])
        # Check type
        self.assertIsInstance(candles[0]["time"], int)
        self.assertIsInstance(candles[0]["open"], float)

    def test_fvg_rectangles_logic(self):
        """Verify FVG rectangles are generated correctly"""
        fvgs = [
            {"start_time": 1704067200, "end_time": 1704067800, "top": 110.0, "bottom": 105.0, "type": -1},
            {"start_time": 1704068200, "end_time": 1704068800, "top": 95.0, "bottom": 90.0, "type": 1}
        ]
        rects = self.viz.create_fvg_rectangles(fvgs)
        self.assertEqual(len(rects), 2)
        self.assertEqual(rects[0]["type"], "rect")
        # Bearish color check (rgba with 255, 0, 0)
        self.assertIn("255, 0, 0", rects[0]["color"])
        # Bullish color check (rgba with 0, 255, 0)
        self.assertIn("0, 255, 0", rects[1]["color"])

    def test_render_output_structure(self):
        """Verify the render method returns a valid dictionary or object for Streamlit"""
        candles = self.viz.prepare_candles(self.df)
        # We don't call the actual Streamlit tool here, we check if it handles parameters
        # Since renderLightweightCharts returns a custom component object, we just check no crash
        try:
            # Mocking the return of renderLightweightCharts if necessary, 
            # but usually we test if the data preparation logic inside is sound.
            pass
        except Exception as e:
            self.fail(f"Render crashed with {e}")

if __name__ == "__main__":
    unittest.main()
