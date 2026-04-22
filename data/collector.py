"""
Collecte des données OHLCV.
Source principale : Alpha Vantage (fonctionne sur serveurs cloud)
Source de secours : yfinance (fonctionne en local)
"""

import pandas as pd
import requests
import time
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class DataCollector:
    """Collecte les données OHLCV via Alpha Vantage."""

    # Mapping Alpha Vantage — symboles Forex
    AV_SYMBOLS = {
        "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"),
        "USDJPY": ("USD", "JPY"), "USDCHF": ("USD", "CHF"),
        "AUDUSD": ("AUD", "USD"), "USDCAD": ("USD", "CAD"),
        "NZDUSD": ("NZD", "USD"), "EURGBP": ("EUR", "GBP"),
        "EURJPY": ("EUR", "JPY"), "GBPJPY": ("GBP", "JPY"),
        "AUDJPY": ("AUD", "JPY"),
    }

    # Alpha Vantage intervals
    AV_INTERVALS = {
        "M1": "1min", "M5": "5min", "M15": "15min",
        "H1": "60min", "H4": "60min",
    }

    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_KEY", "")
        self.base_url = "https://www.alphavantage.co/query"
        # Cache pour éviter de dépasser la limite gratuite
        self._cache = {}
        self._cache_time = {}
        self.cache_duration = 3600  # 1 heure en secondes

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "H1",
        bars: int = 500
    ) -> Optional[pd.DataFrame]:
        """
        Récupère les données OHLCV.
        Essaie Alpha Vantage d'abord, puis yfinance en secours.
        """
        # Vérifier le cache d'abord
        cache_key = f"{symbol}_{timeframe}"
        if self._is_cached(cache_key):
            logger.info(f"Cache hit : {symbol} [{timeframe}]")
            return self._cache[cache_key].tail(bars)

        # Essayer Alpha Vantage si clé disponible
        if self.api_key:
            df = self._get_from_alphavantage(symbol, timeframe)
            if df is not None and len(df) > 50:
                self._cache[cache_key] = df
                self._cache_time[cache_key] = time.time()
                return df.tail(bars)

        # Secours : yfinance (marche en local)
        logger.warning(
            f"Alpha Vantage indisponible pour {symbol}, "
            f"tentative yfinance..."
        )
        df = self._get_from_yfinance(symbol, timeframe)
        if df is not None:
            self._cache[cache_key] = df
            self._cache_time[cache_key] = time.time()
            return df.tail(bars)

        logger.error(f"Impossible de récupérer {symbol}")
        return None

    def _get_from_alphavantage(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """Récupère depuis Alpha Vantage."""
        try:
            # Cas spécial : Or (XAUUSD)
            if symbol == "XAUUSD":
                return self._get_gold_av(timeframe)

            if symbol not in self.AV_SYMBOLS:
                logger.warning(f"Symbole non supporté AV : {symbol}")
                return None

            from_sym, to_sym = self.AV_SYMBOLS[symbol]
            interval = self.AV_INTERVALS.get(timeframe, "60min")

            # Pour H4 : on récupère H1 puis on rééchantillonne
            actual_interval = "60min" if timeframe == "H4" else interval

            logger.info(f"Alpha Vantage : {symbol} [{timeframe}]")

            params = {
                "function":    "FX_INTRADAY",
                "from_symbol": from_sym,
                "to_symbol":   to_sym,
                "interval":    actual_interval,
                "outputsize":  "full",
                "apikey":      self.api_key,
                "datatype":    "json",
            }

            resp = requests.get(self.base_url, params=params, timeout=15)
            data = resp.json()

            # Vérifier les erreurs API
            if "Error Message" in data:
                logger.error(f"AV Error : {data['Error Message']}")
                return None
            if "Note" in data:
                logger.warning(f"AV Rate limit : {data['Note']}")
                return None
            if "Information" in data:
                logger.warning(f"AV Info : {data['Information']}")
                return None

            # Extraire les données
            key = [k for k in data.keys() if "Time Series" in k]
            if not key:
                return None

            ts  = data[key[0]]
            df  = pd.DataFrame(ts).T
            df  = df.rename(columns={
                "1. open":  "open",  "2. high": "high",
                "3. low":   "low",   "4. close": "close",
                "5. volume": "volume"
            })
            df.index = pd.to_datetime(df.index)
            df = df.astype(float).sort_index()
            df = df[~df.index.duplicated(keep="last")].dropna()

            # Rééchantillonner en H4 si nécessaire
            if timeframe == "H4":
                df = self._resample_h4(df)

            return df

        except Exception as e:
            logger.error(f"Erreur Alpha Vantage {symbol} : {e}")
            return None

    def _get_gold_av(self, timeframe: str) -> Optional[pd.DataFrame]:
        """Récupère l'or via Alpha Vantage (TIME_SERIES_INTRADAY sur XAUUSD)."""
        try:
            interval = self.AV_INTERVALS.get(timeframe, "60min")
            if timeframe == "H4":
                interval = "60min"

            params = {
                "function":  "TIME_SERIES_INTRADAY",
                "symbol":    "XAUUSD",
                "interval":  interval,
                "outputsize": "full",
                "apikey":    self.api_key,
            }

            resp = requests.get(self.base_url, params=params, timeout=15)
            data = resp.json()

            key = [k for k in data.keys() if "Time Series" in k]
            if not key:
                # Essayer avec le symbole GLD (ETF or)
                return self._get_from_yfinance("XAUUSD", timeframe)

            ts = data[key[0]]
            df = pd.DataFrame(ts).T.rename(columns={
                "1. open": "open", "2. high": "high",
                "3. low": "low",   "4. close": "close",
                "5. volume": "volume"
            })
            df.index = pd.to_datetime(df.index)
            df = df.astype(float).sort_index()

            if timeframe == "H4":
                df = self._resample_h4(df)

            return df

        except Exception as e:
            logger.error(f"Erreur AV Gold : {e}")
            return None

    def _get_from_yfinance(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """Secours : récupère depuis yfinance."""
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
                "M1": ("1m","7d"),   "M5": ("5m","60d"),
                "M15":("15m","60d"), "H1": ("1h","730d"),
                "H4": ("1h","730d"),
            }

            yf_sym            = yf_map.get(symbol, symbol)
            interval, period  = tf_map.get(timeframe, ("1h","730d"))

            ticker = yf.Ticker(yf_sym)
            df     = ticker.history(
                period=period, interval=interval, auto_adjust=True
            )

            if df.empty:
                return None

            df = df.rename(columns={
                "Open":"open","High":"high",
                "Low":"low","Close":"close","Volume":"volume"
            })[["open","high","low","close","volume"]]

            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")].dropna()

            if timeframe == "H4":
                df = self._resample_h4(df)

            return df

        except Exception as e:
            logger.error(f"Erreur yfinance {symbol} : {e}")
            return None

    def get_all_pairs(
        self,
        pairs: list,
        timeframe: str = "H1"
    ) -> Dict[str, pd.DataFrame]:
        """Récupère les données pour toutes les paires."""
        data = {}
        for pair in pairs:
            df = self.get_ohlcv(pair, timeframe)
            if df is not None:
                data[pair] = df
            # Respecter la limite Alpha Vantage (5 req/min en gratuit)
            time.sleep(13)
        return data

    def resample_to_h4(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rééchantillonne H1 en H4."""
        return self._resample_h4(df)

    def _resample_h4(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rééchantillonne en H4."""
        return df.resample("4h").agg({
            "open":  "first", "high": "max",
            "low":   "min",   "close": "last",
            "volume": "sum"
        }).dropna()

    def _is_cached(self, key: str) -> bool:
        """Vérifie si les données sont encore valides dans le cache."""
        if key not in self._cache:
            return False
        age = time.time() - self._cache_time.get(key, 0)
        return age < self.cache_duration