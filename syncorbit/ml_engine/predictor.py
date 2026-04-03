import joblib
import numpy as np
import os

# MODEL PATH (SAFE & RELATIVE)

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "model.pkl"
)

_MODEL = None

# LOAD MODEL (LAZY, SINGLETON)

def load_model():
    global _MODEL

    if _MODEL is None:
        if os.path.exists(MODEL_PATH):
            _MODEL = joblib.load(MODEL_PATH)
        else:
            _MODEL = None

    return _MODEL

# ML PREDICTION

def predict_handover_score(features: dict) -> float:
    """
    Predict probability that handover should occur.

    Expected features:
    {
        "current_rssi": float,
        "candidate_rssi": float,
        "current_elevation": float,
        "candidate_elevation": float
    }

    Returns:
        float in range [0, 1]
    """

    model = load_model()


    # SAFETY FALLBACK

    if model is None:
        return 0.0

    try:
        X = np.array([[
            float(features["current_rssi"]),
            float(features["candidate_rssi"]),
            float(features["current_elevation"]),
            float(features["candidate_elevation"]),
        ]])

        # Binary classifier → probability of class 1
        score = model.predict_proba(X)[0][1]
        return float(score)

    except Exception as e:
        # Any unexpected issue → no handover
        return 0.0
