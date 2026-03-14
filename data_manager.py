import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class DataManager:
    def __init__(self):
        self.symbols = {
            "Gold": "GC=F",
            "Nasdaq": "NQ=F",
            "SP500": "ES=F"
        }
        self.timeframes = {
            "M1": "1m",
            "M5": "5m",
            "M15": "15m",
            "M30": "30m",
            "H1": "60m",
            "H4": "1h", # Use 1h for H4 resampling or directly if available
            "D1": "1d"
        }

    def fetch_data(self, asset_name, timeframe_name, period="60d"):
        """
        Fetches historical data for a given asset and timeframe.
        """
        symbol = self.symbols.get(asset_name)
        interval = self.timeframes.get(timeframe_name)
        
        # Enforce yfinance limits
        if timeframe_name == "M1":
            interval = "1m"
            if any(x in period for x in ["30d", "60d", "6mo", "1y", "max"]):
                period = "7d"
        elif timeframe_name in ["M5", "M15", "M30"]:
            if any(x in period for x in ["6mo", "1y", "max"]):
                period = "60d"
        elif timeframe_name in ["H1", "H4"]:
            interval = "1h"
            if any(x in period for x in ["1y", "max"]):
                period = "60d"
            
        if not symbol or not interval:
            raise ValueError(f"Invalid asset {asset_name} or timeframe {timeframe_name}")

        try:
            # DISABLE internal yfinance threads to prevent deadlocks in Streamlit
            df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        except Exception as e:
            print(f"[ERROR] yfinance failed for {symbol} ({timeframe_name}): {e}")
            return pd.DataFrame()
        
        if df is None or df.empty:
            return pd.DataFrame()

        # Safer MultiIndex flattening
        if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
            for i in range(df.columns.nlevels):
                if 'Close' in df.columns.get_level_values(i):
                    df.columns = df.columns.get_level_values(i)
                    break
        
        # Resample for H4 if needed
        if timeframe_name == "H4":
            ohlc_dict = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }
            df = df.resample('4H').agg(ohlc_dict).dropna()
            
        # Convert to UTC+1
        if not df.empty:
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert('Etc/GMT-1') # Etc/GMT-1 is UTC+1
            
        return df

    def get_latest_tick(self, asset_name):
        """
        Fetches the single latest candle (simulated 'tick').
        """
        symbol = self.symbols.get(asset_name)
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        
        if df is None or df.empty:
            return pd.DataFrame()
            
        if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
            # Try to find the level that contains OHLC data
            for i in range(df.columns.nlevels):
                if 'Close' in df.columns.get_level_values(i):
                    df.columns = df.columns.get_level_values(i)
                    break
            
        if not df.empty:
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert('Etc/GMT-1')
            
        return df.iloc[-1:]

if __name__ == "__main__":
    dm = DataManager()
    data = dm.fetch_data("Gold", "M15")
    print(data.head())
