"""
Collecte des données de marché OHLCV.
Source principale : Yahoo Finance (gratuit)
Source alternative : MetaTrader 5 (si disponible)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import time
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class DataCollector:
    """Collecte les données OHLCV depuis Yahoo Finance."""

    YF_SYMBOLS = {
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
        "USDCHF": "CHF=X", "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X",
        "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
        "GBPJPY": "GBPJPY=X", "AUDJPY": "AUDJPY=X", "XAUUSD": "GC=F",
    }

    YF_INTERVALS = {
        "M1": "1m", "M5": "5m", "M15": "15m",
        "H1": "1h", "H4": "4h", "D1": "1d",
    }

    YF_PERIODS = {
        "M1": "7d", "M5": "60d", "M15": "60d",
        "H1": "730d", "H4": "730d", "D1": "5y",
    }

    def get_ohlcv(self, symbol: str, timeframe: str = "H1", bars: int = 500) -> Optional[pd.DataFrame]:
        """Récupère les données OHLCV pour un symbole."""
        try:
            yf_symbol   = self.YF_SYMBOLS.get(symbol, symbol)
            yf_interval = self.YF_INTERVALS.get(timeframe, "1h")
            period      = self.YF_PERIODS.get(timeframe, "730d")

            logger.info(f"Collecte {symbol} [{timeframe}]")
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=yf_interval, auto_adjust=True)

            if df.empty:
                logger.warning(f"Aucune donnée pour {symbol}")
                return None

            df = df.rename(columns={
                "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume"
            })
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")].dropna()
            return df.tail(bars)

        except Exception as e:
            logger.error(f"Erreur collecte {symbol}: {e}")
            return None

    def get_all_pairs(self, pairs: list, timeframe: str = "H1") -> Dict[str, pd.DataFrame]:
        """Récupère les données pour toutes les paires."""
        data = {}
        for pair in pairs:
            df = self.get_ohlcv(pair, timeframe)
            if df is not None:
                data[pair] = df
            time.sleep(0.5)
        return data

    def resample_to_h4(self, df_h1: pd.DataFrame) -> pd.DataFrame:
        """Rééchantillonne H1 en H4."""
        return df_h1.resample("4h").agg({
            "open": "first", "high": "max",
            "low": "min", "close": "last", "volume": "sum"
        }).dropna()


class MT5Collector:
    """Collecte via MetaTrader 5 (Windows uniquement)."""

    def __init__(self):
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            if not self.mt5.initialize():
                raise ConnectionError(f"MT5 erreur: {self.mt5.last_error()}")
            logger.info("MT5 connecté avec succès")
        except ImportError:
            logger.warning("MetaTrader5 non disponible — utiliser DataCollector")
            self.mt5 = None

    def get_ohlcv(self, symbol: str, timeframe_str: str, bars: int = 500) -> Optional[pd.DataFrame]:
        if not self.mt5:
            return None
        tf_map = {
            "M1": self.mt5.TIMEFRAME_M1, "M5": self.mt5.TIMEFRAME_M5,
            "M15": self.mt5.TIMEFRAME_M15, "H1": self.mt5.TIMEFRAME_H1,
            "H4": self.mt5.TIMEFRAME_H4, "D1": self.mt5.TIMEFRAME_D1,
        }
        tf    = tf_map.get(timeframe_str, self.mt5.TIMEFRAME_H1)
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")
        return df.rename(columns={"tick_volume": "volume"})[
            ["open", "high", "low", "close", "volume"]
        ]
