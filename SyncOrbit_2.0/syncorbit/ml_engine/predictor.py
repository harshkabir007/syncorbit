import joblib
import numpy as np
import os

try:
    from tensorflow.keras.models import load_model as load_keras_model
except ImportError:
    load_keras_model = None  # TF not installed — LSTM will stay disabled

MODEL_DIR = os.path.dirname(__file__)
LOG_REG_PATH = os.path.join(MODEL_DIR, "logreg.pkl")
LSTM_PATH = os.path.join(MODEL_DIR, "lstm_model.h5")

_LOGREG = None
_LSTM = None

def load_models():
    global _LOGREG, _LSTM

    if _LOGREG is None and os.path.exists(LOG_REG_PATH):
        _LOGREG = joblib.load(LOG_REG_PATH)
        
    if _LSTM is None and load_keras_model is not None and os.path.exists(LSTM_PATH):
        _LSTM = load_keras_model(LSTM_PATH)

def predict_candidate(visible_sats, current_sat=None):
    """
    visible_sats: list of dicts
    Returns the sat dict that logreg thinks is best
    """
    load_models()
    
    if _LOGREG is None or not visible_sats:
        # Fallback metric (highest elevation)
        valid = [s for s in visible_sats if not current_sat or s["name"] != current_sat["name"]]
        if not valid: return None
        valid.sort(key=lambda x: x.get("elevation", 0), reverse=True)
        return valid[0]
        
    curr_rssi = current_sat.get("rssi_db", -100) if current_sat else -100
    curr_elev = current_sat.get("elevation", 0) if current_sat else 0
    
    best_sat = None
    best_prob = -1.0
    
    for sat in visible_sats:
        if current_sat and sat["name"] == current_sat["name"]:
            continue
            
        cand_rssi = sat.get("rssi_db", -100)
        cand_elev = sat.get("elevation", 0)
        
        X = np.array([[curr_rssi, cand_rssi, curr_elev, cand_elev]])
        try:
            prob = _LOGREG.predict_proba(X)[0][1]
            if prob > best_prob:
                best_prob = prob
                best_sat = sat
        except Exception:
            continue
            
    # If prob fails everywhere, fallback
    if best_sat is None:
        valid = [s for s in visible_sats if not current_sat or s["name"] != current_sat["name"]]
        if valid:
            valid.sort(key=lambda x: x.get("elevation", 0), reverse=True)
            return valid[0]
            
    return best_sat

def predict_optimal_time(history_sequence):
    """
    history_sequence: list of exactly 10 feature lists [curr_rssi, cand_rssi, curr_elev, cand_elev]
    """
    load_models()
    
    if _LSTM is None or len(history_sequence) < 10:
        return 0.0
        
    try:
        seq = np.array(history_sequence[-10:])
        X = np.expand_dims(seq, axis=0) # (1, 10, 4)
        score = _LSTM.predict(X, verbose=0)[0][0]
        return float(score)
    except Exception as e:
        print("LSTM error:", e)
        return 0.0


def predict_handover_score(features: dict) -> float:
    """
    Score a single handover candidate using the Logistic Regression model.

    Expected keys in `features`:
        current_rssi       (float, dB)
        candidate_rssi     (float, dB)
        current_elevation  (float, degrees)
        candidate_elevation (float, degrees)

    Returns:
        float in [0, 1] — probability that a handover is beneficial.
        Returns 0.5 (neutral) if the model is unavailable.
    """
    load_models()

    curr_rssi  = features.get("current_rssi", -100)
    cand_rssi  = features.get("candidate_rssi", -100)
    curr_elev  = features.get("current_elevation", 0)
    cand_elev  = features.get("candidate_elevation", 0)

    if _LOGREG is None:
        # Neutral fallback — let heuristic in confidence.py take over
        return 0.5

    try:
        X = np.array([[curr_rssi, cand_rssi, curr_elev, cand_elev]])
        prob = float(_LOGREG.predict_proba(X)[0][1])
        return round(prob, 4)
    except Exception as e:
        print("predict_handover_score error:", e)
        return 0.5
