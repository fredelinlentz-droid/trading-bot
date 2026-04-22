"""
Démo rapide — Génère un signal pour une paire sans lancer le bot complet.
Usage : python scripts/demo_signal.py --pair EURUSD
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from data.collector import DataCollector
from indicators.trend import TrendAnalyzer
from strategy.signal_generator import SignalGenerator
from strategy.risk_manager import RiskManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair",    default="EURUSD")
    parser.add_argument("--capital", type=float, default=10000)
    args = parser.parse_args()

    print(f"\n🤖 Analyse de {args.pair}...")

    collector  = DataCollector()
    analyzer   = TrendAnalyzer(config)
    generator  = SignalGenerator(config, analyzer)
    risk_mgr   = RiskManager(config)

    df_h1 = collector.get_ohlcv(args.pair, "H1", bars=500)
    if df_h1 is None:
        print("❌ Impossible de récupérer les données")
        return

    df_h4  = collector.resample_to_h4(df_h1)
    signal = generator.generate_signal(args.pair, df_h1, df_h4)

    if signal.direction != "HOLD":
        signal.lot_size = risk_mgr.calculate_lot_size(
            args.capital, signal.entry_price, signal.stop_loss, args.pair
        )

    print(f"\n{'='*45}")
    emoji = "🟢" if signal.direction == "BUY" else ("🔴" if signal.direction == "SELL" else "⚪")
    print(f"{emoji}  SIGNAL : {signal.direction}  |  {signal.pair}")
    print(f"{'='*45}")
    if signal.direction != "HOLD":
        print(f"  Entrée    : {signal.entry_price}")
        print(f"  Stop Loss : {signal.stop_loss}")
        print(f"  Take Profit: {signal.take_profit}")
        print(f"  R/R       : 1:{signal.risk_reward}")
        print(f"  Lot Size  : {signal.lot_size}")
    print(f"  Confiance : {signal.confidence}%")
    print(f"\n  Raisons :")
    for r in signal.reasons:
        print(f"    {r}")
    print(f"{'='*45}\n")


if __name__ == "__main__":
    main()
