# handover/packet_sources/demo_source.py

import random
import time

class DemoPacketSource:
    """
    Simulated RF packet source for DEMO mode
    """

    def get_packet(self):
        return {
            "timestamp": time.time(),
            "rssi_db": round(random.uniform(-80, -50), 2),
        }

    def get_spectrum(self):
        # Fake FFT data for waterfall
        return [random.uniform(-100, -40) for _ in range(1024)]
