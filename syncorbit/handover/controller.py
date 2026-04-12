"""
Handover State Machine
Controls GS-A ↔ GS-B coordination and satellite role transitions
"""

from handover.buffer import gs_b_buffer


class HandoverController:
    def __init__(self):
        # Satellite state
        self.current_satellite = None      # Active / connected satellite
        self.candidate_satellite = None    # Next best satellite

        # Handover state
        self.handover_active = False

    # -------------------------------------------------
    # INITIAL LINK SETUP / UPDATE
    # -------------------------------------------------

    def update_links(self, current_sat, candidate_sat=None):
        """
        Update current and candidate satellite names
        """
        self.current_satellite = current_sat
        self.candidate_satellite = candidate_sat

    # -------------------------------------------------
    # START HANDOVER
    # -------------------------------------------------

    def start_handover(self, candidate_name=None):
        """
        Begin handover process.
        Candidate satellite is connected in parallel.
        """
        if self.handover_active:
            return  # avoid duplicate triggers

        print("🔁 Handover started")

        self.handover_active = True
        self.candidate_satellite = candidate_name

    # -------------------------------------------------
    # END HANDOVER
    # -------------------------------------------------

    def end_handover(self):
        """
        Complete handover:
        - Promote candidate to current
        - Replay buffered packets
        - Clear buffer and reset state
        """
        if not self.handover_active:
            return []

        print("✅ Handover completed")

        self.handover_active = False

        # Promote candidate → current
        if self.candidate_satellite:
            print(
                f"🔄 Switching active satellite: "
                f"{self.current_satellite} → {self.candidate_satellite}"
            )
            self.current_satellite = self.candidate_satellite

        # Clear candidate
        self.candidate_satellite = None

        # Replay buffered packets to GS-A
        packets = gs_b_buffer.replay_packets()
        print(f"📦 Replayed {len(packets)} packets to GS-A")

        return packets


# -------------------------------------------------
# GLOBAL CONTROLLER INSTANCE
# -------------------------------------------------

handover_controller = HandoverController()
