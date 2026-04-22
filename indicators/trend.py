"""
Analyse de tendance : EMA, RSI, MACD, structure de marché (HH/HL/LH/LL).
"""

import pandas as pd
import numpy as np
import ta
from dataclasses import dataclass, field
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketStructure:
    trend: str
    ema_fast: float
    ema_slow: float
    ema_signal: str
    swing_highs: List[dict]
    swing_lows: List[dict]
    hh_hl: bool
    lh_ll: bool
    rsi: float
    rsi_signal: str
    macd_line: float
    macd_signal_line: float
    macd_histogram: float
    macd_bullish: bool


class TrendAnalyzer:
    """Analyse complète de la tendance sur une série OHLCV."""

    def __init__(self, config):
        self.config = config

    def analyze(self, df: pd.DataFrame) -> MarketStructure:
        df = df.copy()

        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], self.config.EMA_FAST).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], self.config.EMA_SLOW).ema_indicator()
        df["rsi"]      = ta.momentum.RSIIndicator(df["close"], self.config.RSI_PERIOD).rsi()

        macd_ind       = ta.trend.MACD(df["close"], self.config.MACD_FAST, self.config.MACD_SLOW, self.config.MACD_SIGNAL)
        df["macd"]     = macd_ind.macd()
        df["macd_sig"] = macd_ind.macd_signal()
        df["macd_h"]   = macd_ind.macd_diff()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        ema_signal               = self._get_ema_signal(df)
        swing_highs, swing_lows  = self._find_swing_points(df)
        hh_hl                    = self._is_hh_hl(swing_highs, swing_lows)
        lh_ll                    = self._is_lh_ll(swing_highs, swing_lows)
        trend                    = self._determine_trend(last, ema_signal, hh_hl, lh_ll)
        rsi_signal               = self._get_rsi_signal(last["rsi"])
        macd_bullish             = (
            last["macd"] > last["macd_sig"] and
            last["macd_h"] > 0 and
            last["macd_h"] > prev["macd_h"]
        )

        return MarketStructure(
            trend=trend,
            ema_fast=round(last["ema_fast"], 5),
            ema_slow=round(last["ema_slow"], 5),
            ema_signal=ema_signal,
            swing_highs=swing_highs[-5:],
            swing_lows=swing_lows[-5:],
            hh_hl=hh_hl, lh_ll=lh_ll,
            rsi=round(last["rsi"], 2),
            rsi_signal=rsi_signal,
            macd_line=round(last["macd"], 6),
            macd_signal_line=round(last["macd_sig"], 6),
            macd_histogram=round(last["macd_h"], 6),
            macd_bullish=macd_bullish
        )

    def _get_ema_signal(self, df: pd.DataFrame) -> str:
        last, prev = df.iloc[-1], df.iloc[-2]
        if prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"]:
            return "CROSSING_UP"
        if prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"]:
            return "CROSSING_DOWN"
        return "ABOVE" if last["ema_fast"] > last["ema_slow"] else "BELOW"

    def _find_swing_points(self, df: pd.DataFrame, lookback: int = 5) -> Tuple[list, list]:
        highs, lows = df["high"].values, df["low"].values
        swing_highs, swing_lows = [], []
        for i in range(lookback, len(df) - lookback):
            if highs[i] == max(highs[i-lookback:i+lookback+1]):
                swing_highs.append({"index": i, "price": highs[i], "time": df.index[i]})
            if lows[i] == min(lows[i-lookback:i+lookback+1]):
                swing_lows.append({"index": i, "price": lows[i], "time": df.index[i]})
        return swing_highs, swing_lows

    def _is_hh_hl(self, sh: list, sl: list) -> bool:
        if len(sh) < 2 or len(sl) < 2:
            return False
        rh, rl = sh[-3:], sl[-3:]
        hh = all(rh[i]["price"] > rh[i-1]["price"] for i in range(1, len(rh)))
        hl = all(rl[i]["price"] > rl[i-1]["price"] for i in range(1, len(rl)))
        return hh and hl

    def _is_lh_ll(self, sh: list, sl: list) -> bool:
        if len(sh) < 2 or len(sl) < 2:
            return False
        rh, rl = sh[-3:], sl[-3:]
        lh = all(rh[i]["price"] < rh[i-1]["price"] for i in range(1, len(rh)))
        ll = all(rl[i]["price"] < rl[i-1]["price"] for i in range(1, len(rl)))
        return lh and ll

    def _determine_trend(self, last, ema_signal, hh_hl, lh_ll) -> str:
        bull, bear = 0, 0
        if ema_signal in ("ABOVE", "CROSSING_UP"):
            bull += 2
        elif ema_signal in ("BELOW", "CROSSING_DOWN"):
            bear += 2
        if hh_hl:
            bull += 3
        if lh_ll:
            bear += 3
        bull += 1 if last["close"] > last["ema_fast"] else 0
        bear += 1 if last["close"] < last["ema_fast"] else 0
        if bull > bear + 1:
            return "BULLISH"
        elif bear > bull + 1:
            return "BEARISH"
        return "NEUTRAL"

    def _get_rsi_signal(self, rsi: float) -> str:
        if rsi >= self.config.RSI_OB:
            return "OVERBOUGHT"
        elif rsi <= self.config.RSI_OS:
            return "OVERSOLD"
        return "NEUTRAL"
