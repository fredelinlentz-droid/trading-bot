"""
Backtesting — Validation de la stratégie sur données historiques.
Utilise Walk-Forward pour éviter le look-ahead bias.
"""

import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    avg_rr: float

    def print_report(self):
        print(f"""
╔══════════════════════════════════════╗
║        RAPPORT BACKTEST              ║
╠══════════════════════════════════════╣
║  Trades totaux  : {self.total_trades:<18}║
║  Wins / Losses  : {self.winning_trades} / {self.losing_trades:<14}║
║  Win Rate       : {self.win_rate}%{'':<16}║
║  Profit Factor  : {self.profit_factor:<18}║
║  Retour total   : {self.total_return}%{'':<15}║
║  Max Drawdown   : {self.max_drawdown}%{'':<15}║
║  Sharpe Ratio   : {self.sharpe_ratio:<18}║
╚══════════════════════════════════════╝""")


class Backtester:
    """Backtest Walk-Forward de la stratégie de trading."""

    def __init__(self, config, signal_generator):
        self.config    = config
        self.generator = signal_generator

    def run(self, df: pd.DataFrame, pair: str, initial_capital: float = 10000) -> BacktestResult:
        """Exécute le backtest sur données historiques."""
        split_idx = int(len(df) * 0.7)
        df_test   = df.iloc[split_idx:].copy()
        capital   = initial_capital
        trades    = []
        equity    = [capital]

        logger.info(f"Backtest {pair} — {len(df_test)} bougies de test")

        window = 300
        i = window
        while i < len(df_test) - 20:
            window_df  = df_test.iloc[i-window:i]
            df_confirm = window_df.resample("4h").agg({
                "open": "first", "high": "max",
                "low": "min", "close": "last", "volume": "sum"
            }).dropna()

            try:
                signal = self.generator.generate_signal(pair, window_df, df_confirm)
            except Exception:
                i += 1
                continue

            if signal.direction == "HOLD":
                i += 1
                continue

            future = df_test.iloc[i:i+20]
            result = self._simulate_trade(signal.direction, signal.entry_price, signal.stop_loss, signal.take_profit, future)

            if result is not None:
                risk_amount = capital * self.config.RISK_PER_TRADE
                pnl         = result * risk_amount * signal.risk_reward
                capital    += pnl
                equity.append(capital)
                trades.append({"direction": signal.direction, "pnl": pnl, "won": pnl > 0})
                i += 5
            else:
                i += 1

        return self._calculate_stats(trades, equity, initial_capital)

    def _simulate_trade(self, direction, entry, sl, tp, future):
        for _, c in future.iterrows():
            if direction == "BUY":
                if c["low"] <= sl:
                    return -1
                if c["high"] >= tp:
                    return +1
            else:
                if c["high"] >= sl:
                    return -1
                if c["low"] <= tp:
                    return +1
        return None

    def _calculate_stats(self, trades, equity, initial_capital) -> BacktestResult:
        if not trades:
            logger.warning("Aucun trade exécuté")
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, 0)

        wins         = [t for t in trades if t["won"]]
        losses       = [t for t in trades if not t["won"]]
        gross_profit = sum(t["pnl"] for t in wins) if wins else 0
        gross_loss   = abs(sum(t["pnl"] for t in losses)) if losses else 1
        equity_arr   = np.array(equity)
        rolling_max  = np.maximum.accumulate(equity_arr)
        drawdowns    = (equity_arr - rolling_max) / rolling_max * 100
        pnls         = [t["pnl"] for t in trades]
        sharpe       = (np.mean(pnls) / (np.std(pnls) + 1e-8)) * np.sqrt(252)

        return BacktestResult(
            total_trades   = len(trades),
            winning_trades = len(wins),
            losing_trades  = len(losses),
            win_rate       = round(len(wins) / len(trades) * 100, 1),
            profit_factor  = round(gross_profit / gross_loss, 2),
            total_return   = round((equity_arr[-1] - initial_capital) / initial_capital * 100, 2),
            max_drawdown   = round(abs(drawdowns.min()), 2),
            sharpe_ratio   = round(sharpe, 2),
            avg_rr         = self.config.MIN_RR_RATIO
        )
