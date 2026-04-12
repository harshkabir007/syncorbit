"""
Handover confidence estimation
ML-backed or heuristic fallback
"""

# =========================
# GLOBAL THRESHOLD
# =========================

ML_CONFIDENCE_THRESHOLD = 0.65


def handover_confidence(current, candidate):
    """
    Returns confidence score in range [0, 1]
    Works even if ML model is unavailable
    """

    if not current or not candidate:
        return 0.0

    try:
        from ml_engine.predictor import predict_handover_score

        features = {
            "current_rssi": current["rssi_db"],
            "candidate_rssi": candidate["rssi_db"],
            "current_elevation": current["elevation"],
            "candidate_elevation": candidate["elevation"],
        }

        score = predict_handover_score(features)
        return round(float(score), 3)

    except Exception:
        # -------------------------
        # Heuristic fallback
        # -------------------------
        rssi_gain = candidate["rssi_db"] - current["rssi_db"]
        elev_gain = candidate["elevation"] - current["elevation"]

        confidence = 0.5
        confidence += 0.02 * rssi_gain
        confidence += 0.005 * elev_gain

        return max(0.0, min(1.0, round(confidence, 3)))
