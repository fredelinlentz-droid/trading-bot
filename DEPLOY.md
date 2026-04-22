# 🚀 Guide de Déploiement Gratuit — Trading Bot

## Vue d'ensemble des options d'hébergement gratuit

| Plateforme | Plan gratuit | RAM | Avantages | Limites |
|---|---|---|---|---|
| **Railway** | 500h/mois | 512 MB | Simple, GitHub intégré | Dort si inactif |
| **Render** | 750h/mois | 512 MB | Très facile | Redémarre après 15min inactif |
| **Fly.io** | 3 machines | 256 MB | Persistent, rapide | Config plus technique |
| **Koyeb** | 1 service | 512 MB | Toujours actif | 1 seul service |
| **PythonAnywhere** | Limité | 512 MB | Python natif | Pas de port personnalisé |

**Recommandation : Railway ou Koyeb pour ce bot.**

---

## 🥇 Option 1 — Railway (Recommandé)

### Étapes

**1. Créer un compte**
```
https://railway.app  →  Sign Up avec GitHub
```

**2. Préparer le code sur GitHub**
```bash
# Dans le dossier trading_bot/
git init
git add .
git commit -m "Trading bot initial"

# Créer un repo sur github.com, puis :
git remote add origin https://github.com/VOTRE_USERNAME/trading-bot.git
git push -u origin main
```

**3. Déployer sur Railway**
```
1. railway.app → New Project
2. Deploy from GitHub repo
3. Sélectionner votre repo trading-bot
4. Railway détecte Python automatiquement
```

**4. Configurer les variables d'environnement**
```
Dans Railway → Variables → Add Variable :

API_SECRET       = votre-cle-secrete-ici
TELEGRAM_TOKEN   = (optionnel)
TELEGRAM_CHAT_ID = (optionnel)
PORT             = 8000
```

**5. Obtenir l'URL publique**
```
Railway → Settings → Networking → Generate Domain
→ Vous obtenez : https://trading-bot-XXXX.railway.app
```

**6. Tester**
```bash
curl https://trading-bot-XXXX.railway.app/health
```

---

## 🥈 Option 2 — Render

### Étapes

**1. Créer un compte**
```
https://render.com  →  Sign Up avec GitHub
```

**2. Nouveau service**
```
Dashboard → New → Web Service
→ Connect GitHub repo
→ Name: trading-bot
→ Branch: main
→ Build Command: pip install -r requirements.txt
→ Start Command: python main.py
→ Plan: Free
```

**3. Variables d'environnement**
```
Environment → Add Environment Variable :
API_SECRET, TELEGRAM_TOKEN, PORT=8000
```

**4. URL automatique**
```
https://trading-bot.onrender.com
```

> ⚠️ Render Free s'endort après 15 min d'inactivité.
> Solution : Utiliser UptimeRobot (gratuit) pour un ping toutes les 10 min.

---

## 🥉 Option 3 — Koyeb (Toujours actif)

### Étapes

**1. Créer un compte**
```
https://www.koyeb.com  →  Sign Up
```

**2. Déployer**
```
Create App → GitHub
→ Repo: trading-bot
→ Branch: main
→ Run command: python main.py
→ Port: 8000
→ Instance: Free (nano)
```

**3. Variables**
```
Environment Variables :
API_SECRET=...
PORT=8000
```

> ✅ Koyeb Free ne dort jamais — idéal pour un bot de trading.

---

## 🌐 Option 4 — Fly.io (Plus technique, très fiable)

```bash
# Installer flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Dans le dossier trading_bot/
fly launch
# → Suivre les instructions (choisir région Europe)

# Configurer les secrets
fly secrets set API_SECRET="votre-secret"
fly secrets set TELEGRAM_TOKEN="votre-token"

# Déployer
fly deploy

# Voir les logs
fly logs
```

---

## ⚡ Cloudflare Workers (API Gateway gratuit)

Le Worker agit comme un **proxy sécurisé** devant votre backend.

### Déploiement

```bash
# 1. Installer Wrangler
npm install -g wrangler

# 2. Login
wrangler login

# 3. Dans le dossier du projet
cd trading_bot/

# 4. Configurer les secrets
wrangler secret put API_SECRET
# Entrer : votre-cle-secrete

wrangler secret put BACKEND_URL
# Entrer : https://trading-bot-XXXX.railway.app

wrangler secret put INTERNAL_SECRET
# Entrer : meme-valeur-que-API_SECRET

# 5. Déployer
wrangler deploy

# → URL obtenue : https://trading-bot-api.VOTRE_SUBDOMAIN.workers.dev
```

### Architecture finale
```
Dashboard HTML  →  Cloudflare Worker  →  Railway/Render (Python)
(navigateur)       (proxy sécurisé)       (bot + API FastAPI)
```

---

## 🔔 Garder le bot actif (Anti-sleep)

### UptimeRobot (gratuit)

```
1. uptimerobot.com → Create Account
2. Add New Monitor :
   - Monitor Type : HTTP(s)
   - Friendly Name : Trading Bot
   - URL : https://VOTRE_URL/health
   - Monitoring Interval : Every 5 minutes
3. Save
```

Cela envoie un ping toutes les 5 minutes, empêchant le service de dormir.

---

## 📋 Checklist de déploiement

```
□ Code poussé sur GitHub (sans .env !)
□ Service créé sur Railway/Render/Koyeb
□ Variables d'environnement configurées
□ URL publique obtenue et testée (/health)
□ Cloudflare Worker déployé (optionnel)
□ UptimeRobot configuré
□ Token Telegram configuré (optionnel)
□ Test de signal : GET /signal/EURUSD avec token
```

---

## 🧪 Tester le déploiement

```bash
# 1. Health check (sans auth)
curl https://VOTRE_URL/health

# 2. Récupérer les signaux (avec auth)
curl -H "Authorization: Bearer VOTRE_API_SECRET" \
     https://VOTRE_URL/signals

# 3. Signal en temps réel pour EURUSD
curl -H "Authorization: Bearer VOTRE_API_SECRET" \
     https://VOTRE_URL/signal/EURUSD

# 4. Accéder au dashboard
# Ouvrir dans le navigateur : https://VOTRE_URL/dashboard
```

---

## 💡 Conseils de production

1. **Ne jamais commiter le fichier .env** — utiliser les variables d'environnement de la plateforme
2. **Surveiller les logs** régulièrement (Railway/Render ont des logs en temps réel)
3. **Activer les alertes email** sur la plateforme d'hébergement
4. **Faire des sauvegardes** des modèles ML entraînés
5. **Tester en paper trading** au moins 1 mois avant d'utiliser en production
