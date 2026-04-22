"""
API REST FastAPI — Endpoints pour le dashboard et les signaux.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Bot API",
    description="Signaux de trading algorithmique — Continuation de tendance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

security  = HTTPBearer(auto_error=False)
API_SECRET = os.getenv("API_SECRET", "change-this-secret-key")

# Stockage en mémoire des derniers signaux (remplacer par DB en prod)
signals_store: List[dict] = []


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    if not credentials or credentials.credentials != API_SECRET:
        raise HTTPException(status_code=401, detail="Token invalide")
    return credentials.credentials


class SignalResponse(BaseModel):
    pair: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    timeframe: str
    timestamp: str
    reasons: List[str]
    lot_size: float


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirige vers le dashboard."""
    return """
    <html><head><meta http-equiv="refresh" content="0; url=/dashboard" /></head>
    <body><a href="/dashboard">Dashboard</a></body></html>
    """


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "signals_count": len(signals_store)
    }


@app.get("/signals", response_model=List[SignalResponse])
async def get_signals(
    pair: Optional[str] = None,
    direction: Optional[str] = None,
    token: str = Depends(verify_token)
):
    """Retourne les derniers signaux (filtrables par paire/direction)."""
    result = signals_store[-50:]  # 50 derniers signaux
    if pair:
        result = [s for s in result if s["pair"] == pair.upper()]
    if direction:
        result = [s for s in result if s["direction"] == direction.upper()]
    return result


@app.post("/signals")
async def add_signal(signal: SignalResponse, token: str = Depends(verify_token)):
    """Ajoute un signal (appelé par le bot)."""
    signals_store.append(signal.dict())
    if len(signals_store) > 500:
        signals_store.pop(0)
    return {"status": "ok", "count": len(signals_store)}


@app.get("/signal/{pair}")
async def get_pair_signal(pair: str, token: str = Depends(verify_token)):
    """Génère un signal en temps réel pour une paire."""
    from main import bot
    try:
        signal = bot.analyze_pair(pair.upper())
        if signal is None:
            raise HTTPException(status_code=404, detail=f"Paire {pair} non trouvée")
        return signal.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/risk")
async def get_risk_summary(token: str = Depends(verify_token)):
    """Résumé de la gestion du risque."""
    from main import bot
    return bot.risk_mgr.get_summary()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard HTML intégré."""
    try:
        with open("dashboard/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Dashboard non trouvé — vérifier dashboard/index.html</h1>"
