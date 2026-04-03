"""
Automatic handover decision logic
ML-gated + RSSI based
"""

from handover.controller import handover_controller
from handover.confidence import ML_CONFIDENCE_THRESHOLD

# =========================
# HANDOVER THRESHOLDS
# =========================

RSSI_MARGIN = 3        # dB
RSSI_MIN = -75         # dB
RSSI_STABLE = -65      # dB


def evaluate_handover(current, candidate, confidence):
    """
    Decide whether to start or end handover.

    Parameters:
    - current: dict
    - candidate: dict
    - confidence: float (0–1)

    Returns:
    - decision string
    """

    if not current or not candidate:
        return "NO_DATA"

    curr_rssi = current.get("rssi_db")
    cand_rssi = candidate.get("rssi_db")

    if curr_rssi is None or cand_rssi is None:
        return "NO_RSSI"

    # -------------------------------------------------
    # START HANDOVER (ML + RSSI gated)
    # -------------------------------------------------
    if (
        not handover_controller.handover_active
        and curr_rssi < RSSI_MIN
        and (cand_rssi - curr_rssi) >= RSSI_MARGIN
        and confidence >= ML_CONFIDENCE_THRESHOLD
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
        return "HANDOVER_COMPLETED"

    return "NO_ACTION"
