from streamlit_lightweight_charts import renderLightweightCharts
import pandas as pd
import numpy as np

class ChartVisualizer:
    def __init__(self):
        self.chart_options = {
            "layout": {
                "textColor": '#d1d4dc',
                "background": { "type": 'solid', "color": '#131722' },
                "fontSize": 12,
            },
            "grid": {
                "vertLines": { "color": 'rgba(42, 46, 57, 0.5)' },
                "horzLines": { "color": 'rgba(42, 46, 57, 0.5)' },
            },
            "crosshair": {
                "mode": 0,
            },
            "priceScale": {
                "borderColor": 'rgba(42, 46, 57, 1)',
                "autoScale": True,
            },
            "timeScale": {
                "borderColor": 'rgba(42, 46, 57, 1)',
                "timeVisible": True,
                "secondsVisible": False,
                "barSpacing": 15,
                "rightOffset": 20,
            },
            "handleScroll": True,
            "handleScale": True,
        }

    def prepare_candles(self, df, time_offset=0):
        candles = []
        for index, row in df.iterrows():
            candles.append({
                "time": int(index.timestamp()) + time_offset,
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
            })
        return candles

    def create_fvg_rectangles(self, fvgs):
        rects = []
        for fvg in fvgs:
            color = "rgba(0, 255, 0, 0.2)" if fvg['type'] == 1 else "rgba(255, 0, 0, 0.2)"
            rects.append({
                "type": "rect",
                "data": [
                    { "time": fvg['start_time'], "price": fvg['top'] },
                    { "time": fvg['end_time'], "price": fvg['bottom'] }
                ],
                "color": color
            })
        return rects

    def render(self, candles, series_data=[], markers=[], rsi_data=None, key=None):
        """
        Renders the final chart with optional indicator panes.
        """
        # Main series
        main_series = [
            {
                "type": "Candlestick",
                "data": candles,
                "options": {
                    "upColor": "#26a69a",
                    "downColor": "#ef5350",
                },
                "markers": markers
            }
        ]
        
        # Add extra series (FVGs etc)
        for s in series_data:
            main_series.append(s)

        # Single chart config - Increased height to 900 for full screen feel
        chart_config = {
            "chart": {**self.chart_options, "height": 900},
            "series": main_series
        }

        # Wrap in list - standard for multi-pane or single pane
        return renderLightweightCharts([chart_config], key=str(key) if key else "main")
