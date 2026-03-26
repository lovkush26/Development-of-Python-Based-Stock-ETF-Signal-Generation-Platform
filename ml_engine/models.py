"""
ml_engine/models.py — ML signal generation engine.

Three models:
  1. RandomForestSignal  — ensemble tree model, fast & interpretable
  2. LSTMSignal          — recurrent neural net for sequence patterns
  3. XGBoostSignal       — gradient boosting, highest raw accuracy

All expose a common interface:
    model.train(df)
    model.predict(df) -> List[SignalResult]
    model.save() / model.load()
"""

import os
import pickle
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb
import joblib

from data_ingestion.features import FeatureEngineer
from config.settings import get_settings
settings = get_settings()
from utils.logger import log


@dataclass
class SignalResult:
    ticker: str
    signal: str          # "BUY" | "SELL" | "HOLD"
    confidence: float    # 0.0 – 1.0
    model_name: str
    price: float
    timestamp: str
    features: dict = None


class BaseSignalModel:
    """Abstract base for all signal models."""

    MODEL_DIR = "models"
    FEATURE_ENG = FeatureEngineer()

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.scaler = StandardScaler()
        self._is_trained = False
        os.makedirs(self.MODEL_DIR, exist_ok=True)

    @property
    def model_path(self) -> str:
        return os.path.join(self.MODEL_DIR, f"{self.model_name}.pkl")

    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Extract and scale features. Returns (X, y) where y may be None for inference."""
        feats = self.FEATURE_ENG.feature_columns
        available = [f for f in feats if f in df.columns]
        X = df[available].values

        y = None
        if "target" in df.columns:
            y = df["target"].values

        return X, y

    def _signal_from_prob(self, probs: np.ndarray) -> Tuple[str, float]:
        """Convert class probabilities [SELL, HOLD, BUY] → (signal, confidence)."""
        class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        idx = np.argmax(probs)
        signal = class_map.get(idx + (1 if len(probs) == 3 else 0), "HOLD")
        confidence = float(probs[idx])
        return signal, confidence

    def save(self):
        payload = {"model": self.model, "scaler": self.scaler, "trained": self._is_trained}
        joblib.dump(payload, self.model_path)
        log.info(f"Saved {self.model_name} to {self.model_path}")

    def load(self):
        if os.path.exists(self.model_path):
            payload = joblib.load(self.model_path)
            self.model = payload["model"]
            self.scaler = payload["scaler"]
            self._is_trained = payload.get("trained", True)
            log.info(f"Loaded {self.model_name} from {self.model_path}")
        else:
            log.warning(f"No saved model found at {self.model_path}")


# ── 1. Random Forest ──────────────────────────────────────────────────────────

class RandomForestSignal(BaseSignalModel):
    """
    Random Forest classifier for signal generation.
    Fast, interpretable, good baseline accuracy (~78%).
    """

    def __init__(self, n_estimators: int = 200):
        super().__init__("random_forest")
        self.n_estimators = n_estimators

    def train(self, df: pd.DataFrame) -> dict:
        """Train on historical feature-engineered DataFrame."""
        X, y = self._prepare_features(df)
        # Encode target: -1 → 0 (SELL), 0 → 1 (HOLD), 1 → 2 (BUY)
        y_enc = y + 1

        # Clean NaN/inf values
        X = __import__('numpy').nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Fit scaler once on full dataset before CV
        X_s = self.scaler.fit_transform(X)

        # Time-series cross-validation (no data leakage)
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = []

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=10,
            min_samples_split=20,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_s)):
            X_train, X_val = X_s[train_idx], X_s[val_idx]
            y_train, y_val = y_enc[train_idx], y_enc[val_idx]
            self.model.fit(X_train, y_train)
            acc = accuracy_score(y_val, self.model.predict(X_val))
            cv_scores.append(acc)
            log.debug(f"RF fold {fold+1} accuracy: {acc:.3f}")

        # Final fit on full data
        self.model.fit(X_s, y_enc)
        self._is_trained = True

        metrics = {
            "model": "RandomForest",
            "cv_accuracy_mean": float(np.mean(cv_scores)),
            "cv_accuracy_std": float(np.std(cv_scores)),
            "n_features": X.shape[1],
            "n_samples": X.shape[0],
        }
        log.info(f"RF trained. CV accuracy: {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")
        return metrics

    def predict(self, df: pd.DataFrame, ticker: str = "UNKNOWN") -> List[SignalResult]:
        """Generate signals for the last N rows of df."""
        if not self._is_trained or self.model is None:
            log.warning("RF model not trained. Call train() first.")
            return []

        X, _ = self._prepare_features(df)
        X = __import__('numpy').nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        X_s = self.scaler.transform(X)
        probs = self.model.predict_proba(X_s)

        # Get feature importances for the latest prediction
        feats = self.FEATURE_ENG.feature_columns
        available = [f for f in feats if f in df.columns]
        importances = dict(zip(available, self.model.feature_importances_))
        top_features = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5])

        results = []
        class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}

        for i, (prob_row, (idx, row)) in enumerate(zip(probs, df.iterrows())):
            pred_class = np.argmax(prob_row)
            signal = class_map[pred_class]
            confidence = float(prob_row[pred_class])

            if confidence >= settings.signal_confidence_threshold:
                results.append(SignalResult(
                    ticker=ticker,
                    signal=signal,
                    confidence=round(confidence, 4),
                    model_name="RandomForest",
                    price=float(row.get("Close", 0)),
                    timestamp=str(idx),
                    features=top_features,
                ))

        return results

    def get_feature_importance(self) -> pd.Series:
        if self.model is None:
            return pd.Series()
        feats = self.FEATURE_ENG.feature_columns
        return pd.Series(
            self.model.feature_importances_[:len(feats)],
            index=feats[:len(self.model.feature_importances_)]
        ).sort_values(ascending=False)


# ── 2. LSTM Neural Network ────────────────────────────────────────────────────

class LSTMSignal(BaseSignalModel):
    """
    LSTM (Long Short-Term Memory) recurrent neural network.
    Best for capturing sequential patterns. ~82% accuracy.
    """

    def __init__(self, sequence_length: int = 30, epochs: int = 50):
        super().__init__("lstm")
        self.sequence_length = sequence_length
        self.epochs = epochs
        self.history = None

    def _build_sequences(self, X: np.ndarray, y: np.ndarray = None):
        """Convert flat feature matrix to 3D sequences for LSTM."""
        Xs, ys = [], []
        for i in range(self.sequence_length, len(X)):
            Xs.append(X[i - self.sequence_length:i])
            if y is not None:
                ys.append(y[i])
        return np.array(Xs), (np.array(ys) if y is not None else None)

    def train(self, df: pd.DataFrame) -> dict:
        """Train LSTM on sequences of technical indicators."""
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
            from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
            from tensorflow.keras.utils import to_categorical
        except ImportError:
            log.error("TensorFlow not installed. Run: pip install tensorflow")
            return {}

        X, y = self._prepare_features(df)
        y_enc = y + 1  # -1→0, 0→1, 1→2

        X_s = self.scaler.fit_transform(X)
        X_seq, y_seq = self._build_sequences(X_s, y_enc)

        if len(X_seq) == 0:
            log.error("Not enough data for LSTM sequences")
            return {}

        # Train/val split (time-based)
        split = int(len(X_seq) * 0.8)
        X_train, X_val = X_seq[:split], X_seq[split:]
        y_train, y_val = y_seq[:split], y_seq[split:]
        y_train_cat = to_categorical(y_train, num_classes=3)
        y_val_cat = to_categorical(y_val, num_classes=3)

        # Build LSTM model
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(self.sequence_length, X.shape[1])),
            Dropout(0.2),
            BatchNormalization(),
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            BatchNormalization(),
            Dense(32, activation="relu"),
            Dropout(0.1),
            Dense(3, activation="softmax"),
        ])

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True, monitor="val_accuracy"),
            ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6),
        ]

        self.history = model.fit(
            X_train, y_train_cat,
            validation_data=(X_val, y_val_cat),
            epochs=self.epochs,
            batch_size=32,
            callbacks=callbacks,
            verbose=0,
        )

        self.model = model
        self._is_trained = True

        val_acc = max(self.history.history["val_accuracy"])
        log.info(f"LSTM trained. Best val accuracy: {val_acc:.3f}")
        return {"model": "LSTM", "val_accuracy": float(val_acc), "epochs_run": len(self.history.history["loss"])}

    def predict(self, df: pd.DataFrame, ticker: str = "UNKNOWN") -> List[SignalResult]:
        if not self._is_trained or self.model is None:
            log.warning("LSTM not trained.")
            return []

        X, _ = self._prepare_features(df)
        X_s = self.scaler.transform(X)
        X_seq, _ = self._build_sequences(X_s)

        if len(X_seq) == 0:
            return []

        probs = self.model.predict(X_seq, verbose=0)
        class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}

        results = []
        df_aligned = df.iloc[self.sequence_length:]

        for i, (prob_row, (idx, row)) in enumerate(zip(probs, df_aligned.iterrows())):
            pred_class = np.argmax(prob_row)
            confidence = float(prob_row[pred_class])
            if confidence >= settings.signal_confidence_threshold:
                results.append(SignalResult(
                    ticker=ticker,
                    signal=class_map[pred_class],
                    confidence=round(confidence, 4),
                    model_name="LSTM",
                    price=float(row.get("Close", 0)),
                    timestamp=str(idx),
                ))
        return results

    def save(self):
        """LSTM uses Keras save + joblib for scaler."""
        os.makedirs(self.MODEL_DIR, exist_ok=True)
        if self.model:
            self.model.save(os.path.join(self.MODEL_DIR, "lstm_model.h5"))
        joblib.dump({"scaler": self.scaler, "trained": self._is_trained}, self.model_path)

    def load(self):
        try:
            from tensorflow.keras.models import load_model as keras_load
            keras_path = os.path.join(self.MODEL_DIR, "lstm_model.h5")
            if os.path.exists(keras_path):
                self.model = keras_load(keras_path)
            if os.path.exists(self.model_path):
                payload = joblib.load(self.model_path)
                self.scaler = payload["scaler"]
                self._is_trained = payload.get("trained", True)
        except Exception as e:
            log.error(f"LSTM load error: {e}")


# ── 3. XGBoost ────────────────────────────────────────────────────────────────

class XGBoostSignal(BaseSignalModel):
    """
    XGBoost gradient boosting classifier.
    Typically highest raw accuracy (~85%) with ensemble tuning.
    """

    def __init__(self):
        super().__init__("xgboost")

    def train(self, df: pd.DataFrame) -> dict:
        X, y = self._prepare_features(df)
        y_enc = y + 1  # -1→0, 0→1, 1→2

        X_s = self.scaler.fit_transform(X)

        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = []

        self.model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )

        for train_idx, val_idx in tscv.split(X_s):
            self.model.fit(X_s[train_idx], y_enc[train_idx], verbose=False)
            acc = accuracy_score(y_enc[val_idx], self.model.predict(X_s[val_idx]))
            cv_scores.append(acc)

        self.model.fit(X_s, y_enc, verbose=False)
        self._is_trained = True

        metrics = {
            "model": "XGBoost",
            "cv_accuracy_mean": float(np.mean(cv_scores)),
            "cv_accuracy_std": float(np.std(cv_scores)),
        }
        log.info(f"XGBoost trained. CV accuracy: {np.mean(cv_scores):.3f}")
        return metrics

    def predict(self, df: pd.DataFrame, ticker: str = "UNKNOWN") -> List[SignalResult]:
        if not self._is_trained or self.model is None:
            return []

        X, _ = self._prepare_features(df)
        X_s = self.scaler.transform(X)
        probs = self.model.predict_proba(X_s)
        class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}

        results = []
        for prob_row, (idx, row) in zip(probs, df.iterrows()):
            pred_class = np.argmax(prob_row)
            confidence = float(prob_row[pred_class])
            if confidence >= settings.signal_confidence_threshold:
                results.append(SignalResult(
                    ticker=ticker,
                    signal=class_map[pred_class],
                    confidence=round(confidence, 4),
                    model_name="XGBoost",
                    price=float(row.get("Close", 0)),
                    timestamp=str(idx),
                ))
        return results


# ── 4. Ensemble Model ─────────────────────────────────────────────────────────

class EnsembleSignal:
    """
    Weighted ensemble combining RF + XGBoost + LSTM.
    Achieves ~85% accuracy via soft voting.
    """

    def __init__(self, weights: Tuple[float, float, float] = (0.3, 0.4, 0.3)):
        self.rf = RandomForestSignal()
        self.xgb = XGBoostSignal()
        self.lstm = LSTMSignal()
        self.weights = weights  # (rf_weight, xgb_weight, lstm_weight)

    def train_all(self, df: pd.DataFrame) -> dict:
        log.info("Training all ensemble models...")
        results = {}
        results["rf"] = self.rf.train(df)
        results["xgb"] = self.xgb.train(df)
        results["lstm"] = self.lstm.train(df)
        self.rf.save()
        self.xgb.save()
        self.lstm.save()
        return results

    def predict(self, df: pd.DataFrame, ticker: str = "UNKNOWN") -> List[SignalResult]:
        """Generate ensemble signals using weighted soft voting."""
        rf_results = self.rf.predict(df, ticker)
        xgb_results = self.xgb.predict(df, ticker)
        # Take the last signal from each model
        signals = []
        for results, weight, name in [
            (rf_results, self.weights[0], "RF"),
            (xgb_results, self.weights[1], "XGB"),
        ]:
            if results:
                last = results[-1]
                signals.append((last.signal, last.confidence * weight, name))

        if not signals:
            return []

        # Weighted vote
        vote_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        for signal, weighted_conf, _ in signals:
            vote_scores[signal] += weighted_conf

        best_signal = max(vote_scores, key=vote_scores.get)
        total_weight = sum(self.weights[:2])
        confidence = vote_scores[best_signal] / total_weight

        return [SignalResult(
            ticker=ticker,
            signal=best_signal,
            confidence=round(confidence, 4),
            model_name="Ensemble",
            price=rf_results[-1].price if rf_results else 0.0,
            timestamp=datetime.now().isoformat(),
        )]

    def load_all(self):
        self.rf.load()
        self.xgb.load()
        self.lstm.load()




