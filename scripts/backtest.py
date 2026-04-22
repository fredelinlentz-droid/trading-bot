"""
Script de backtesting.
Usage : python scripts/backtest.py --pair EURUSD --capital 10000
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from data.collector import DataCollector
from indicators.trend import TrendAnalyzer
from strategy.signal_generator import SignalGenerator
from ml.backtester import Backtester

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Backtest")


def main():
    parser = argparse.ArgumentParser(description="Backtest de la stratégie de trading")
    parser.add_argument("--pair",    default="EURUSD")
    parser.add_argument("--capital", type=float, default=10000)
    parser.add_argument("--bars",    type=int,   default=1000)
    parser.add_argument("--all",     action="store_true")
    args = parser.parse_args()

    collector  = DataCollector()
    analyzer   = TrendAnalyzer(config)
    generator  = SignalGenerator(config, analyzer)
    backtester = Backtester(config, generator)

    pairs = config.PAIRS if args.all else [args.pair]

    results = {}
    for pair in pairs:
        logger.info(f"\nBacktest {pair}...")
        df = collector.get_ohlcv(pair, "H1", bars=args.bars)
        if df is None or len(df) < 400:
            logger.warning(f"Données insuffisantes pour {pair}")
            continue

        result = backtester.run(df, pair, initial_capital=args.capital)
        result.print_report()
        results[pair] = result

    # Résumé global
    if len(results) > 1:
        print("\n" + "="*50)
        print("RÉSUMÉ GLOBAL")
        print("="*50)
        for pair, r in results.items():
            status = "✅" if r.total_return > 0 else "❌"
            print(f"{status} {pair:10} | WR:{r.win_rate}% | PF:{r.profit_factor} | Ret:{r.total_return}% | DD:{r.max_drawdown}%")


if __name__ == "__main__":
    main()
