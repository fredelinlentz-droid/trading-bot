"""
Notifications Telegram — Envoi des signaux et rapports.
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envoie les signaux de trading via Telegram."""

    def __init__(self, token: str, chat_id: str):
        self.token    = token
        self.chat_id  = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.enabled  = bool(token and chat_id)

    def send_signal(self, signal) -> bool:
        if not self.enabled or signal.direction == "HOLD":
            return True

        emoji = "🟢" if signal.direction == "BUY" else "🔴"
        message = (
            f"{emoji} *SIGNAL {signal.direction}* — `{signal.pair}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Entrée*    : `{signal.entry_price}`\n"
            f"🛑 *Stop Loss* : `{signal.stop_loss}`\n"
            f"🎯 *Take Profit*: `{signal.take_profit}`\n"
            f"📊 *R/R*       : `1:{signal.risk_reward}`\n"
            f"🎲 *Confiance* : `{signal.confidence}%`\n"
            f"📦 *Lot*       : `{signal.lot_size}`\n"
            f"⏱️ *Timeframe* : `{signal.timeframe}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        for r in signal.reasons[:5]:
            message += f"  {r}\n"

        message += f"\n⚠️ _Toujours vérifier avant d'entrer_\n"
        message += f"🕐 _{datetime.now().strftime('%H:%M — %d/%m/%Y')}_"

        return self._send_message(message)

    def send_alert(self, title: str, body: str) -> bool:
        message = f"*{title}*\n━━━━━━━━━━━━━━━\n{body}"
        return self._send_message(message)

    def send_backtest_report(self, result, pair: str) -> bool:
        trend_emoji = "📈" if result.total_return > 0 else "📉"
        message = (
            f"📊 *RAPPORT BACKTEST — {pair}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Trades    : `{result.total_trades}`\n"
            f"✅ Win Rate  : `{result.win_rate}%`\n"
            f"⚖️ Prof. F.  : `{result.profit_factor}`\n"
            f"{trend_emoji} Retour    : `{result.total_return}%`\n"
            f"📉 Drawdown : `{result.max_drawdown}%`\n"
            f"📐 Sharpe   : `{result.sharpe_ratio}`"
        )
        return self._send_message(message)

    def _send_message(self, text: str) -> bool:
        if not self.enabled:
            logger.info(f"[Telegram désactivé] {text[:100]}")
            return True
        try:
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Erreur Telegram: {e}")
            return False
