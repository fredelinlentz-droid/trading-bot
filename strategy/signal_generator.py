"""
Générateur de signaux de trading.
Logique : Confirmation H4 → Entrée H1 sur pullback.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    pair: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    timeframe: str
    timestamp: datetime
    reasons: list
    lot_size: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "confidence": self.confidence,
            "timeframe": self.timeframe,
            "timestamp": str(self.timestamp),
            "reasons": self.reasons,
            "lot_size": self.lot_size,
        }


class SignalGenerator:
    """Génère des signaux BUY/SELL/HOLD basés sur continuation de tendance."""

    def __init__(self, config, trend_analyzer):
        self.config   = config
        self.analyzer = trend_analyzer

    def generate_signal(self, pair: str, df_primary: pd.DataFrame, df_confirm: pd.DataFrame) -> TradingSignal:
        structure_h4  = self.analyzer.analyze(df_confirm)
        structure_h1  = self.analyzer.analyze(df_primary)
        current_price = df_primary["close"].iloc[-1]
        timestamp     = df_primary.index[-1]

        signal, reasons, confidence = self._evaluate_conditions(
            structure_h4, structure_h1, df_primary, current_price
        )

        if signal == "HOLD":
            return TradingSignal(
                pair=pair, direction="HOLD", entry_price=current_price,
                stop_loss=0, take_profit=0, risk_reward=0,
                confidence=confidence, timeframe=self.config.PRIMARY_TF,
                timestamp=timestamp, reasons=reasons
            )

        sl, tp = self._calculate_sl_tp(signal, df_primary, structure_h1, current_price)

        if sl == 0:
            return TradingSignal(
                pair=pair, direction="HOLD", entry_price=current_price,
                stop_loss=0, take_profit=0, risk_reward=0, confidence=0,
                timeframe=self.config.PRIMARY_TF, timestamp=timestamp,
                reasons=["SL/TP non calculable"]
            )

        rr = self._calculate_rr(signal, current_price, sl, tp)

        if rr < self.config.MIN_RR_RATIO:
            reasons.append(f"RR insuffisant: {rr:.2f} < {self.config.MIN_RR_RATIO}")
            return TradingSignal(
                pair=pair, direction="HOLD", entry_price=current_price,
                stop_loss=sl, take_profit=tp, risk_reward=rr,
                confidence=confidence * 0.5, timeframe=self.config.PRIMARY_TF,
                timestamp=timestamp, reasons=reasons
            )

        return TradingSignal(
            pair=pair, direction=signal,
            entry_price=round(current_price, 5),
            stop_loss=round(sl, 5), take_profit=round(tp, 5),
            risk_reward=round(rr, 2), confidence=round(confidence, 1),
            timeframe=self.config.PRIMARY_TF, timestamp=timestamp, reasons=reasons
        )

    def _evaluate_conditions(self, h4, h1, df, price):
        reasons, bull, bear = [], 0, 0

        if h4.trend == "BULLISH":
            bull += 3
            reasons.append("✅ H4 Tendance HAUSSIÈRE")
        elif h4.trend == "BEARISH":
            bear += 3
            reasons.append("✅ H4 Tendance BAISSIÈRE")
        else:
            reasons.append("⚠️ H4 Tendance NEUTRE")

        if h1.trend == h4.trend:
            bull += 2 if h4.trend == "BULLISH" else 0
            bear += 2 if h4.trend == "BEARISH" else 0
            reasons.append("✅ H1 aligné avec H4")

        if h1.hh_hl:
            bull += 2
            reasons.append("✅ Structure HH+HL")
        elif h1.lh_ll:
            bear += 2
            reasons.append("✅ Structure LH+LL")

        if h1.ema_signal in ("ABOVE", "CROSSING_UP"):
            bull += 1
            reasons.append("✅ EMA 50 > EMA 200")
        elif h1.ema_signal in ("BELOW", "CROSSING_DOWN"):
            bear += 1
            reasons.append("✅ EMA 50 < EMA 200")

        if bull > bear:
            if h1.rsi < 65:
                bull += 1
                reasons.append(f"✅ RSI favorable BUY: {h1.rsi:.1f}")
            else:
                reasons.append(f"⚠️ RSI en surachat: {h1.rsi:.1f}")
        elif bear > bull:
            if h1.rsi > 35:
                bear += 1
                reasons.append(f"✅ RSI favorable SELL: {h1.rsi:.1f}")
            else:
                reasons.append(f"⚠️ RSI en survente: {h1.rsi:.1f}")

        if h1.macd_bullish:
            bull += 1
            reasons.append("✅ MACD haussier")
        else:
            bear += 1
            reasons.append("✅ MACD baissier")

        total       = max(bull, bear)
        confidence  = min((total / 10) * 100, 92)

        if bull >= 6 and h4.trend == "BULLISH":
            return "BUY", reasons, confidence
        elif bear >= 6 and h4.trend == "BEARISH":
            return "SELL", reasons, confidence

        reasons.append(f"ℹ️ Score insuffisant: {total}/10")
        return "HOLD", reasons, confidence

    def _calculate_sl_tp(self, signal, df, structure, price):
        atr = self._calculate_atr(df)
        if signal == "BUY":
            sl_base = min([s["price"] for s in structure.swing_lows[-3:]]) if structure.swing_lows else price - atr * 2
            sl      = sl_base - atr * 0.5
            tp      = price + (price - sl) * self.config.MIN_RR_RATIO
        else:
            sl_base = max([s["price"] for s in structure.swing_highs[-3:]]) if structure.swing_highs else price + atr * 2
            sl      = sl_base + atr * 0.5
            tp      = price - (sl - price) * self.config.MIN_RR_RATIO
        return sl, tp

    def _calculate_atr(self, df, period=14):
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]

    def _calculate_rr(self, signal, entry, sl, tp):
        risk   = (entry - sl) if signal == "BUY" else (sl - entry)
        reward = (tp - entry) if signal == "BUY" else (entry - tp)
        return reward / risk if risk > 0 else 0
