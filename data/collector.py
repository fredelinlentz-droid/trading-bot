"""
Collecte des donnees OHLCV via Alpha Vantage (cloud-compatible).
"""

import pandas as pd
import requests
import time
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class DataCollector:

    AV_SYMBOLS = {
        "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"),
        "USDJPY": ("USD", "JPY"), "USDCHF": ("USD", "CHF"),
        "AUDUSD": ("AUD", "USD"), "USDCAD": ("USD", "CAD"),
        "NZDUSD": ("NZD", "USD"), "EURGBP": ("EUR", "GBP"),
        "EURJPY": ("EUR", "JPY"), "GBPJPY": ("GBP", "JPY"),
        "AUDJPY": ("AUD", "JPY"),
    }

    def __init__(self):
        self.api_key     = os.getenv("ALPHA_VANTAGE_KEY", "")
        self.base_url    = "https://www.alphavantage.co/query"
        self._cache      = {}
        self._cache_time = {}
        self.cache_ttl   = 3600

    def get_ohlcv(self, symbol: str, timeframe: str = "H1", bars: int = 500) -> Optional[pd.DataFrame]:
        cache_key = f"{symbol}_{timeframe}"
        if self._is_cached(cache_key):
            logger.info(f"Cache: {symbol} [{timeframe}]")
            return self._cache[cache_key].tail(bars)

        df = None
        if self.api_key:
            df = self._from_alphavantage(symbol, timeframe)

        if df is None or len(df) < 50:
            logger.warning(f"Alpha Vantage indisponible pour {symbol}, tentative yfinance...")
            df = self._from_yfinance(symbol, timeframe)

        if df is not None and len(df) >= 50:
            self._cache[cache_key]      = df
            self._cache_time[cache_key] = time.time()
            return df.tail(bars)

        logger.error(f"Aucune donnee pour {symbol}")
        return None

    def _from_alphavantage(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        try:
            if symbol == "XAUUSD":
                return self._gold_av(timeframe)

            if symbol not in self.AV_SYMBOLS:
                return None

            from_sym, to_sym = self.AV_SYMBOLS[symbol]
            logger.info(f"Alpha Vantage: {symbol} [{timeframe}]")

            params = {
                "function":    "FX_INTRADAY",
                "from_symbol": from_sym,
                "to_symbol":   to_sym,
                "interval":    "60min",
                "outputsize":  "full",
                "apikey":      self.api_key,
                "datatype":    "json",
            }

            resp = requests.get(self.base_url, params=params, timeout=20)
            data = resp.json()

            if "Error Message" in data or "Note" in data or "Information" in data:
                logger.warning(f"AV limite ou erreur: {list(data.keys())}")
                return None

            key = [k for k in data.keys() if "Time Series" in k]
            if not key:
                return None

            df = pd.DataFrame(data[key[0]]).T
            df = df.rename(columns={
                "1. open":  "open",
                "2. high":  "high",
                "3. low":   "low",
                "4. close": "close",
                "5. volume":"volume"
            })
            df.index = pd.to_datetime(df.index)
            df = df.astype(float).sort_index()
            df = df[~df.index.duplicated(keep="last")].dropna()

            if timeframe == "H4":
                df = self.resample_to_h4(df)

            return df

        except Exception as e:
            logger.error(f"Erreur AV {symbol}: {e}")
            return None

    def _gold_av(self, timeframe: str) -> Optional[pd.DataFrame]:
        try:
            params = {
                "function":   "TIME_SERIES_INTRADAY",
                "symbol":     "XAUUSD",
                "interval":   "60min",
                "outputsize": "full",
                "apikey":     self.api_key,
            }
            resp = requests.get(self.base_url, params=params, timeout=20)
            data = resp.json()
            key  = [k for k in data.keys() if "Time Series" in k]
            if not key:
                return self._from_yfinance("XAUUSD", timeframe)

            df = pd.DataFrame(data[key[0]]).T
            df = df.rename(columns={
                "1. open":  "open",
                "2. high":  "high",
                "3. low":   "low",
                "4. close": "close",
                "5. volume":"volume"
            })
            df.index = pd.to_datetime(df.index)
            df = df.astype(float).sort_index()
            if timeframe == "H4":
                df = self.resample_to_h4(df)
            return df

        except Exception as e:
            logger.error(f"Erreur AV Gold: {e}")
            return None

    def _from_yfinance(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        try:
            import yfinance as yf

            yf_map = {
                "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
                "USDJPY": "JPY=X",    "USDCHF": "CHF=X",
                "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X",
                "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X",
                "EURJPY": "EURJPY=X", "GBPJPY": "GBPJPY=X",
                "AUDJPY": "AUDJPY=X", "XAUUSD": "GC=F",
            }
            tf_map = {
                "M1":  ("1m",  "7d"),
                "M5":  ("5m",  "60d"),
                "M15": ("15m", "60d"),
                "H1":  ("1h",  "730d"),
                "H4":  ("1h",  "730d"),
            }

            yf_sym           = yf_map.get(symbol, symbol)
            interval, period = tf_map.get(timeframe, ("1h", "730d"))

            ticker = yf.Ticker(yf_sym)
            df     = ticker.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                return None

            df = df.rename(columns={
                "Open":   "open",
                "High":   "high",
                "Low":    "low",
                "Close":  "close",
                "Volume": "volume"
            })[["open", "high", "low", "close", "volume"]]

            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")].dropna()

            if timeframe == "H4":
                df = self.resample_to_h4(df)
            return df

        except Exception as e:
            logger.error(f"Erreur yfinance {symbol}: {e}")
            return None

    def get_all_pairs(self, pairs: list, timeframe: str = "H1") -> Dict[str, pd.DataFrame]:
        data = {}
        for pair in pairs:
            df = self.get_ohlcv(pair, timeframe)
            if df is not None:
                data[pair] = df
            time.sleep(13)
        return data

    def resample_to_h4(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.resample("4h").agg({
            "open":   "first",
            "high":   "max",
            "low":    "min",
            "close":  "last",
            "volume": "sum"
        }).dropna()

    def _is_cached(self, key: str) -> bool:
        if key not in self._cache:
            return False
        age = time.time() - self._cache_time.get(key, 0)
        return age < self.cache_ttl