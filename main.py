"""
Point d'entrée principal du Trading Bot.
Lance le bot + l'API FastAPI en parallèle.
"""

import time
import logging
import threading
import schedule
import uvicorn
from config.settings import config
from data.collector import DataCollector
from indicators.trend import TrendAnalyzer
from strategy.signal_generator import SignalGenerator
from strategy.risk_manager import RiskManager
from notifications.telegram_bot import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/trading_bot.log"),
    ]
)
logger = logging.getLogger("TradingBot")


class TradingBot:
    """Orchestre tous les modules du bot de trading."""

    def __init__(self):
        self.config    = config
        self.collector = DataCollector()
        self.analyzer  = TrendAnalyzer(config)
        self.generator = SignalGenerator(config, self.analyzer)
        self.risk_mgr  = RiskManager(config)
        self.notifier  = TelegramNotifier(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID)
        self.signals   = []

    def analyze_pair(self, pair: str):
        """Analyse une paire et retourne un signal."""
        df_h1 = self.collector.get_ohlcv(pair, "H1", bars=500)
        if df_h1 is None or len(df_h1) < 250:
            logger.warning(f"Données insuffisantes pour {pair}")
            return None

        df_h4 = self.collector.resample_to_h4(df_h1)
        signal = self.generator.generate_signal(pair, df_h1, df_h4)

        # Calcul du lot si signal actif
        if signal.direction != "HOLD":
            signal.lot_size = self.risk_mgr.calculate_lot_size(
                account_balance=10000,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                pair=pair
            )

        return signal

    def run_analysis_cycle(self):
        """Cycle complet sur toutes les paires configurées."""
        logger.info("═══ Nouveau cycle d'analyse ═══")

        for pair in self.config.PAIRS:
            try:
                signal = self.analyze_pair(pair)
                if signal is None:
                    continue

                if signal.direction != "HOLD":
                    can_trade, reason = self.risk_mgr.can_open_trade(pair, signal.direction)

                    if can_trade:
                        logger.info(
                            f"SIGNAL {signal.direction} {pair} | "
                            f"Entry:{signal.entry_price} SL:{signal.stop_loss} "
                            f"TP:{signal.take_profit} | Conf:{signal.confidence}%"
                        )
                        self.notifier.send_signal(signal)
                        self.signals.append(signal.to_dict())
                        if len(self.signals) > 500:
                            self.signals.pop(0)
                    else:
                        logger.debug(f"Trade bloqué — {pair}: {reason}")
                else:
                    logger.debug(f"HOLD — {pair}")

            except Exception as e:
                logger.error(f"Erreur analyse {pair}: {e}")

        logger.info(f"Cycle terminé — {len(self.signals)} signaux totaux")

    def start_scheduler(self):
        """Lance le planificateur de tâches."""
        # Analyse toutes les heures
        schedule.every().hour.at(":01").do(self.run_analysis_cycle)

        logger.info("Planificateur démarré")
        self.run_analysis_cycle()  # Première analyse immédiate

        while True:
            schedule.run_pending()
            time.sleep(30)

    def start_api(self):
        """Démarre l'API FastAPI."""
        from api.routes import app
        uvicorn.run(app, host="0.0.0.0", port=self.config.PORT, log_level="warning")

    def start(self):
        """Lance le bot complet (API + scheduler)."""
        logger.info("🤖 Trading Bot démarré")
        logger.info(f"Paires: {', '.join(self.config.PAIRS)}")
        logger.info(f"API: http://0.0.0.0:{self.config.PORT}")

        # API en thread séparé
        api_thread = threading.Thread(target=self.start_api, daemon=True)
        api_thread.start()

        time.sleep(2)
        self.start_scheduler()


# Instance globale (utilisée par l'API)
bot = TradingBot()

if __name__ == "__main__":
    bot.start()
