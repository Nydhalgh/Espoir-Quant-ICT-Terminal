from streamlit_lightweight_charts import renderLightweightCharts
import pandas as pd
import json

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
                "vertLine": {"width": 1, "color": '#758696', "style": 3},
                "horzLine": {"width": 1, "color": '#758696', "style": 3},
            },
            "priceScale": {
                "borderColor": 'rgba(42, 46, 57, 1)',
            },
            "timeScale": {
                "borderColor": 'rgba(42, 46, 57, 1)',
                "timeVisible": True,
                "secondsVisible": False,
                "barSpacing": 12,
            },
        }

    def prepare_candles(self, df, time_offset=0):
        """
        Converts DataFrame to Lightweight Charts format.
        time_offset: seconds to add to the timestamp (e.g., 3600 for UTC+1)
        """
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
        """
        fvgs: List of dictionaries with start_time, end_time, top, bottom, type.
        """
        rects = []
        for fvg in fvgs:
            color = "rgba(0, 255, 0, 0.2)" if fvg['type'] == 1 else "rgba(255, 0, 0, 0.2)"
            if fvg.get('is_inverted', False):
                color = "rgba(128, 0, 128, 0.4)" # Purple for inversion
                
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
        # Main Pane
        main_chart_series = [
            {
                "type": "Candlestick",
                "data": candles,
                "options": {
                    "upColor": "#26a69a",
                    "downColor": "#ef5350",
                    "borderVisible": False,
                    "wickUpColor": "#26a69a",
                    "wickDownColor": "#ef5350",
                },
                "markers": markers
            }
        ]
        main_chart_series.extend(series_data)

        charts_list = [
            {
                "chart": {**self.chart_options, "height": 500 if rsi_data else 650},
                "series": main_chart_series
            }
        ]

        # Secondary Pane (RSI)
        if rsi_data:
            rsi_chart_options = {**self.chart_options, "height": 150}
            rsi_chart_options["priceScale"] = {
                "mode": 0, # Normal
                "autoScale": False,
                "max": 100,
                "min": 0
            }
            charts_list.append({
                "chart": rsi_chart_options,
                "series": [
                    {
                        "type": "Line",
                        "data": rsi_data,
                        "options": {"color": "#2962ff", "lineWidth": 2, "title": "RSI"}
                    }
                ]
            })

        return renderLightweightCharts(charts_list, key=key)
