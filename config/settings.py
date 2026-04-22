"""
Configuration globale du Trading Bot.
Toutes les variables sensibles sont chargées depuis .env
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TradingConfig:
    # ══════════════════════════════════════
    # PAIRES TRADÉES
    # ══════════════════════════════════════
    PAIRS: List[str] = field(default_factory=lambda: [
        # Majeures
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
        "AUDUSD", "USDCAD", "NZDUSD",
        # Mineures
        "EURGBP", "EURJPY", "GBPJPY", "AUDJPY",
        # Métaux
        "XAUUSD",
    ])

    # ══════════════════════════════════════
    # TIMEFRAMES
    # ══════════════════════════════════════
    TIMEFRAMES: List[str] = field(default_factory=lambda: ["M1", "M5", "M15", "H1", "H4"])
    PRIMARY_TF: str  = "H1"
    CONFIRM_TF: str  = "H4"

    # ══════════════════════════════════════
    # INDICATEURS
    # ══════════════════════════════════════
    EMA_FAST: int    = 50
    EMA_SLOW: int    = 200
    RSI_PERIOD: int  = 14
    RSI_OB: float    = 70
    RSI_OS: float    = 30
    MACD_FAST: int   = 12
    MACD_SLOW: int   = 26
    MACD_SIGNAL: int = 9

    # ══════════════════════════════════════
    # GESTION DU RISQUE
    # ══════════════════════════════════════
    RISK_PER_TRADE: float  = 0.01
    MAX_RISK: float        = 0.02
    MAX_OPEN_TRADES: int   = 3
    MIN_RR_RATIO: float    = 1.5

    # ══════════════════════════════════════
    # API KEYS
    # ══════════════════════════════════════
    ALPHA_VANTAGE_KEY: str = os.getenv("ALPHA_VANTAGE_KEY", "")
    TELEGRAM_TOKEN: str    = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID: str  = os.getenv("TELEGRAM_CHAT_ID", "")
    DATABASE_URL: str      = os.getenv("DATABASE_URL", "sqlite:///trading.db")
    API_SECRET: str        = os.getenv("API_SECRET", "change-this-secret-key")
    PORT: int              = int(os.getenv("PORT", "8000"))


config = TradingConfig()
