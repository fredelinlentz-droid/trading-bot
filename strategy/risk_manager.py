"""
Gestion du risque — Module critique.
Calcul des lots, protection anti-overtrading, corrélations.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class RiskManager:
    """Gère le risque par trade et la taille des positions."""

    CORRELATIONS = {
        "EURUSD": ["GBPUSD", "AUDUSD", "NZDUSD"],
        "GBPUSD": ["EURUSD", "EURGBP"],
        "USDJPY": ["EURJPY", "GBPJPY", "AUDJPY"],
        "XAUUSD": ["EURUSD"],
    }

    PIP_VALUES = {
        "EURUSD": 10.0, "GBPUSD": 10.0, "AUDUSD": 10.0,
        "NZDUSD": 10.0, "USDJPY": 9.1,  "USDCHF": 11.0,
        "USDCAD": 7.5,  "EURGBP": 13.0, "EURJPY": 9.1,
        "GBPJPY": 9.1,  "AUDJPY": 9.1,  "XAUUSD": 10.0,
    }

    def __init__(self, config):
        self.config      = config
        self.open_trades = []

    def calculate_lot_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        pair: str,
        risk_percent: Optional[float] = None
    ) -> float:
        """Calcule la taille de lot en fonction du risque."""
        risk_pct    = min(risk_percent or self.config.RISK_PER_TRADE, self.config.MAX_RISK)
        risk_amount = account_balance * risk_pct
        sl_distance = abs(entry_price - stop_loss)

        if sl_distance == 0:
            logger.error("Distance SL = 0")
            return 0.01

        pip_value = self.PIP_VALUES.get(pair, 10.0)
        lot_size  = risk_amount / (sl_distance * pip_value * 10000)
        lot_size  = round(max(0.01, min(lot_size, 10.0)), 2)

        logger.info(f"Lot {pair}: {lot_size} | Risque: ${risk_amount:.2f} | SL: {sl_distance:.5f}")
        return lot_size

    def can_open_trade(self, pair: str, direction: str) -> Tuple[bool, str]:
        """Vérifie si un nouveau trade peut être ouvert."""
        if len(self.open_trades) >= self.config.MAX_OPEN_TRADES:
            return False, f"Maximum {self.config.MAX_OPEN_TRADES} trades atteint"

        if any(t["pair"] == pair for t in self.open_trades):
            return False, f"Trade déjà ouvert sur {pair}"

        open_pairs = [t["pair"] for t in self.open_trades]
        for corr_pair in self.CORRELATIONS.get(pair, []):
            if corr_pair in open_pairs:
                existing = [t for t in self.open_trades if t["pair"] == corr_pair]
                if existing and existing[0]["direction"] == direction:
                    return False, f"Double exposition: {pair} corrélé avec {corr_pair}"

        return True, "OK"

    def add_trade(self, signal):
        self.open_trades.append({
            "pair": signal.pair, "direction": signal.direction,
            "entry": signal.entry_price, "sl": signal.stop_loss, "tp": signal.take_profit,
        })

    def remove_trade(self, pair: str):
        self.open_trades = [t for t in self.open_trades if t["pair"] != pair]

    def get_summary(self) -> dict:
        return {
            "open_trades": len(self.open_trades),
            "max_trades": self.config.MAX_OPEN_TRADES,
            "trades": self.open_trades,
        }
