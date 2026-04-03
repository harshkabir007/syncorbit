from handover.runtime import get_mode

from .demo_source import DemoPacketSource
from .real_source import RealPacketSource

_demo = DemoPacketSource()
# _real = RealPacketSource()
_real = None

def get_packet_source():
    return _real if get_mode() == "REAL" else _demo
