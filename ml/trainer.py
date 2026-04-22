"""
Entraînement du modèle ML de classification (BUY/SELL/HOLD).
Utilise Gradient Boosting avec validation temporelle croisée.
"""

import pandas as pd
import numpy as np
import ta
import joblib
import os
import logging
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import classification_report

logger = logging.getLogger(__name__)


class MLTrainer:
    """Modèle ML de classification : BUY / SELL / HOLD."""

    LABEL_MAP = {"BUY": 0, "HOLD": 1, "SELL": 2}
    LABEL_INV = {0: "BUY", 1: "HOLD", 2: "SELL"}

    def __init__(self):
        self.model         = None
        self.scaler        = StandardScaler()
        self.feature_names = []

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule toutes les features techniques."""
        f = pd.DataFrame(index=df.index)

        f["ema_20"]       = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
        f["ema_50"]       = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()
        f["ema_200"]      = ta.trend.EMAIndicator(df["close"], 200).ema_indicator()
        f["price_vs_50"]  = (df["close"] - f["ema_50"]) / f["ema_50"]
        f["price_vs_200"] = (df["close"] - f["ema_200"]) / f["ema_200"]
        f["ema50_vs_200"] = (f["ema_50"] - f["ema_200"]) / f["ema_200"]

        f["rsi_14"]     = ta.momentum.RSIIndicator(df["close"], 14).rsi()
        f["rsi_7"]      = ta.momentum.RSIIndicator(df["close"], 7).rsi()
        f["rsi_change"] = f["rsi_14"].diff(3)

        macd            = ta.trend.MACD(df["close"])
        f["macd"]       = macd.macd()
        f["macd_signal"]= macd.macd_signal()
        f["macd_hist"]  = macd.macd_diff()
        f["macd_cross"] = (f["macd"] - f["macd_signal"]).apply(np.sign)

        bb              = ta.volatility.BollingerBands(df["close"])
        f["bb_upper"]   = bb.bollinger_hband()
        f["bb_lower"]   = bb.bollinger_lband()
        f["bb_pos"]     = (df["close"] - f["bb_lower"]) / (f["bb_upper"] - f["bb_lower"] + 1e-8)
        f["bb_width"]   = (f["bb_upper"] - f["bb_lower"]) / df["close"]

        atr             = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"])
        f["atr"]        = atr.average_true_range()
        f["atr_norm"]   = f["atr"] / df["close"]

        for n in [1, 3, 5, 10, 20]:
            f[f"return_{n}"] = df["close"].pct_change(n)

        f["body_size"]  = abs(df["close"] - df["open"]) / df["open"]
        f["is_bullish"] = (df["close"] > df["open"]).astype(int)

        return f

    def create_labels(self, df: pd.DataFrame, forward_bars: int = 10, min_return: float = 0.001) -> pd.Series:
        """Crée les labels basés sur les retours futurs."""
        future = df["close"].shift(-forward_bars) / df["close"] - 1
        labels = pd.Series(index=df.index, dtype=str)
        labels[future >  min_return] = "BUY"
        labels[future < -min_return] = "SELL"
        labels[(future >= -min_return) & (future <= min_return)] = "HOLD"
        return labels

    def train(self, df: pd.DataFrame, pair: str = "EURUSD") -> dict:
        """Entraîne le modèle sur données historiques."""
        logger.info(f"Entraînement {pair} — {len(df)} bougies")

        features = self.create_features(df)
        labels   = self.create_labels(df)
        combined = pd.concat([features, labels.rename("label")], axis=1).dropna()
        combined = combined[combined["label"] != ""]

        X = combined.drop("label", axis=1)
        y = combined["label"].map(self.LABEL_MAP)
        self.feature_names = X.columns.tolist()

        logger.info(f"Distribution: {combined['label'].value_counts().to_dict()}")

        X_scaled = self.scaler.fit_transform(X)
        tscv     = TimeSeriesSplit(n_splits=5)

        self.model = GradientBoostingClassifier(
            n_estimators=200, max_depth=4,
            learning_rate=0.05, subsample=0.8, random_state=42
        )

        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring="f1_macro")
        logger.info(f"CV F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

        self.model.fit(X_scaled, y)
        y_pred = self.model.predict(X_scaled)
        report = classification_report(y, y_pred, target_names=["BUY", "HOLD", "SELL"])
        logger.info(f"\n{report}")

        return {
            "cv_f1_mean": round(cv_scores.mean(), 3),
            "cv_f1_std":  round(cv_scores.std(), 3),
            "train_size": len(X),
            "report":     report
        }

    def predict(self, df: pd.DataFrame) -> tuple:
        """Prédit la direction pour la dernière bougie."""
        if self.model is None:
            raise ValueError("Modèle non entraîné")

        features = self.create_features(df)
        last_row = features.iloc[[-1]][self.feature_names]

        if last_row.isnull().any().any():
            return "HOLD", 0.0

        X_scaled   = self.scaler.transform(last_row)
        pred       = self.model.predict(X_scaled)[0]
        proba      = self.model.predict_proba(X_scaled)[0]
        confidence = round(max(proba) * 100, 1)

        return self.LABEL_INV[pred], confidence

    def save(self, path: str = "models/trading_model.pkl"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model, "scaler": self.scaler, "features": self.feature_names}, path)
        logger.info(f"Modèle sauvegardé: {path}")

    def load(self, path: str = "models/trading_model.pkl"):
        data               = joblib.load(path)
        self.model         = data["model"]
        self.scaler        = data["scaler"]
        self.feature_names = data["features"]
        logger.info(f"Modèle chargé: {path}")
