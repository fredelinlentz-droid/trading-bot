"""
Script d'entraînement du modèle ML.
Usage : python scripts/train_model.py --pair EURUSD --bars 2000
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from data.collector import DataCollector
from ml.trainer import MLTrainer
from notifications.telegram_bot import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainModel")


def main():
    parser = argparse.ArgumentParser(description="Entraîner le modèle ML de trading")
    parser.add_argument("--pair",  default="EURUSD", help="Paire à entraîner (défaut: EURUSD)")
    parser.add_argument("--bars",  type=int, default=2000, help="Nombre de bougies historiques")
    parser.add_argument("--tf",    default="H1", help="Timeframe (défaut: H1)")
    parser.add_argument("--all",   action="store_true", help="Entraîner sur toutes les paires")
    args = parser.parse_args()

    collector = DataCollector()
    trainer   = MLTrainer()
    notifier  = TelegramNotifier(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID)

    pairs = config.PAIRS if args.all else [args.pair]

    for pair in pairs:
        logger.info(f"\n{'='*50}")
        logger.info(f"Entraînement sur {pair} [{args.tf}] — {args.bars} bougies")
        logger.info(f"{'='*50}")

        df = collector.get_ohlcv(pair, args.tf, bars=args.bars)
        if df is None or len(df) < 500:
            logger.error(f"Données insuffisantes pour {pair}")
            continue

        metrics = trainer.train(df, pair=pair)

        logger.info(f"\nRésultats {pair}:")
        logger.info(f"  CV F1-Score : {metrics['cv_f1_mean']} ± {metrics['cv_f1_std']}")
        logger.info(f"  Taille train: {metrics['train_size']} exemples")

        model_path = f"models/{pair}_{args.tf}_model.pkl"
        trainer.save(model_path)
        logger.info(f"Modèle sauvegardé : {model_path}")

        notifier.send_alert(
            f"✅ Modèle entraîné — {pair}",
            f"F1: {metrics['cv_f1_mean']} ± {metrics['cv_f1_std']}\nTaille: {metrics['train_size']}"
        )

    logger.info("\nEntraînement terminé !")


if __name__ == "__main__":
    main()
