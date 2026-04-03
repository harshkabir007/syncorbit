"""
GS-B Packet Buffer
Stores packets during handover window
"""

from collections import deque
import time

class PacketBuffer:
    def __init__(self, max_packets=5000):
        self.buffer = deque(maxlen=max_packets)

    def store_packet(self, packet):
        """
        packet = dict or bytes
        """
        self.buffer.append({
            "timestamp": time.time(),
            "data": packet
        })

    def replay_packets(self):
        """
        Return all buffered packets in order
        """
        packets = list(self.buffer)
        self.buffer.clear()
        return packets

    def size(self):
        return len(self.buffer)


# Global GS-B buffer instance
gs_b_buffer = PacketBuffer()
