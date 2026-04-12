"""
Automatic handover decision logic
LSTM-gated + RSSI based
"""

import time
from handover.controller import handover_controller

# =========================
# HANDOVER THRESHOLDS
# =========================

RSSI_STABLE = -88           # dB — any satellite with usable signal can complete handover
OPTIMAL_TIME_THRESHOLD = 0.40  # LSTM confidence to trigger handover start

# =========================
# COOLDOWN (Fix #3)
# Prevents immediate re-trigger after a handover completes.
# The LSTM history still contains "optimal" conditions right after
# completion, which would otherwise fire a new handover immediately.
# =========================
HANDOVER_COOLDOWN_SECONDS = 15
_last_handover_time: float = 0.0  # epoch seconds; 0 = never triggered


def evaluate_handover(current, candidate, confidence):
    """
    Decide whether to start or end handover based on LSTM optimality score.

    Parameters:
    - current: dict
    - candidate: dict
    - confidence: float (0–1) from LSTM

    Returns:
    - decision string
    """
    global _last_handover_time

    if not current or not candidate:
        return "NO_DATA"

    curr_rssi = current.get("rssi_db")
    cand_rssi = candidate.get("rssi_db")

    if curr_rssi is None or cand_rssi is None:
        return "NO_RSSI"

    # -------------------------------------------------
    # START HANDOVER (LSTM OPTIMAL TIME DIRECTIVE)
    # Guarded by cooldown: do not re-trigger within 15s of last completion.
    # -------------------------------------------------
    cooldown_elapsed = (time.time() - _last_handover_time) >= HANDOVER_COOLDOWN_SECONDS

    if (
        not handover_controller.handover_active
        and confidence >= OPTIMAL_TIME_THRESHOLD
        and cooldown_elapsed
    ):
        handover_controller.start_handover(candidate["name"])
        return "HANDOVER_STARTED"

    # -------------------------------------------------
    # END HANDOVER
    # -------------------------------------------------
    if (
        handover_controller.handover_active
        and cand_rssi >= RSSI_STABLE
    ):
        handover_controller.end_handover()
        _last_handover_time = time.time()   # stamp cooldown clock
        return "HANDOVER_COMPLETED"

    return "NO_ACTION"
