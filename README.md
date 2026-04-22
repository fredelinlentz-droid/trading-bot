# 🤖 Trading Bot — Signaux Algorithmiques Forex & Or

Bot de trading intelligent basé sur la **continuation de tendance** avec analyse multi-timeframe, indicateurs techniques et modèle Machine Learning.

## ✨ Fonctionnalités

- 📊 **13 paires** : EUR/USD, XAU/USD, GBP/USD et toutes les majeures/mineures
- 🔍 **Analyse multi-timeframe** : H4 (tendance) + H1 (entrée)
- 📈 **Indicateurs** : EMA 50/200, RSI, MACD, Bollinger, ATR
- 🧠 **ML** : Gradient Boosting avec validation temporelle croisée
- 🛡️ **Gestion du risque** : 1-2% par trade, anti-corrélation, anti-overtrading
- 📱 **Notifications** : Telegram
- 🌐 **API REST** : FastAPI + Dashboard HTML
- ☁️ **Déploiement** : Railway, Render, Fly.io (gratuit)

## 🚀 Démarrage rapide

### 1. Installation

```bash
git clone https://github.com/VOTRE_USERNAME/trading-bot.git
cd trading-bot
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
# Éditer .env avec vos clés API
```

### 3. Test rapide (un seul signal)

```bash
python scripts/demo_signal.py --pair EURUSD
```

### 4. Backtest

```bash
python scripts/backtest.py --pair EURUSD --capital 10000
# Toutes les paires :
python scripts/backtest.py --all
```

### 5. Entraîner le modèle ML

```bash
python scripts/train_model.py --pair EURUSD --bars 2000
```

### 6. Lancer le bot complet

```bash
python main.py
# Dashboard : http://localhost:8000/dashboard
# API docs  : http://localhost:8000/docs
```

## 📁 Structure du projet

```
trading_bot/
├── config/settings.py          # Configuration globale
├── data/collector.py           # Collecte OHLCV (Yahoo Finance / MT5)
├── indicators/trend.py         # EMA, RSI, MACD, structure HH/HL
├── strategy/
│   ├── signal_generator.py     # Logique de signal
│   └── risk_manager.py         # Calcul lots, protection
├── ml/
│   ├── trainer.py              # Entraînement Gradient Boosting
│   └── backtester.py           # Walk-Forward backtest
├── api/routes.py               # API FastAPI
├── notifications/telegram_bot.py
├── dashboard/index.html        # Dashboard web
├── cloudflare_worker/index.js  # Proxy Cloudflare
├── scripts/
│   ├── demo_signal.py          # Test rapide
│   ├── backtest.py             # Backtesting
│   └── train_model.py          # Entraînement ML
├── Dockerfile
├── railway.json                # Config Railway
├── render.yaml                 # Config Render
└── DEPLOY.md                   # Guide déploiement complet
```

## 🌐 Déploiement gratuit

Voir **[DEPLOY.md](DEPLOY.md)** pour le guide complet.

Options disponibles :
- **Railway** — 500h/mois gratuit (recommandé)
- **Render** — 750h/mois gratuit
- **Koyeb** — Toujours actif, plan gratuit
- **Fly.io** — 3 machines gratuites
- **Cloudflare Workers** — API Gateway gratuit (100k req/jour)

## ⚠️ Avertissement

Ce bot est un **outil d'aide à la décision**, pas un système autonome garanti. Le trading comporte des risques de perte en capital. Toujours :
- Tester en paper trading avant utilisation réelle
- Ne jamais risquer plus de 1-2% par trade
- Vérifier les signaux manuellement
- Désactiver pendant les annonces économiques majeures (NFP, FOMC)

## 📜 Licence

MIT — Usage personnel et éducatif.
