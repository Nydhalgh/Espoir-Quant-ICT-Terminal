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
        yfinance supports up to 60 days of intraday data for 1m/5m/15m/30m/60m.
        """
        symbol = self.symbols.get(asset_name)
        
        # Mapping timeframe_name to yfinance interval
        interval = self.timeframes.get(timeframe_name)
        
        # Enforce yfinance limits for intraday data
        if timeframe_name == "M1":
            interval = "1m"
            # Cap period at 7 days for 1m
            if any(x in period for x in ["30d", "60d", "6mo", "1y", "max"]):
                period = "7d"
        elif timeframe_name in ["M5", "M15", "M30"]:
            # Cap period at 60 days for 5m-30m
            if any(x in period for x in ["6mo", "1y", "max"]):
                period = "60d"
        elif timeframe_name in ["H1", "H4"]:
            interval = "1h" # Fetch 1h and resample for H4
            # Cap period at 730 days for 1h
            if any(x in period for x in ["1y", "max"]):
                period = "60d" # Actually yfinance 1h can go up to 2y but 60d is safer/faster
            
        if not symbol or not interval:
            raise ValueError(f"Invalid asset {asset_name} or timeframe {timeframe_name}")

        df = yf.download(symbol, period=period, interval=interval, progress=False)
        
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
