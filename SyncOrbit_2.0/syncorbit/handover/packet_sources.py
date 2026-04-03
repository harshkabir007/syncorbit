from django.conf import settings
import random
import time
import numpy as np

# =====================================================
# DEMO PACKET SOURCE
# =====================================================

class DemoPacketSource:
    def __init__(self):
        self.prev_rssi = None
        self.phase = 0.0

    def get_packet(self):
        if self.prev_rssi is None:
            rssi = random.uniform(-70, -55)
        else:
            # Reduced jitter from (-2.5, 2.5) to (-0.5, 0.5) for stability
            rssi = self.prev_rssi + random.uniform(-0.5, 0.5)

        rssi = max(-90, min(-45, rssi))

        slope = 0 if self.prev_rssi is None else rssi - self.prev_rssi
        self.prev_rssi = rssi

        return {
            "type": "DEMO",
            "rssi_db": round(rssi, 2),
            "snr_db": round(random.uniform(8, 18), 2),
            "noise_db": round(rssi - random.uniform(10, 20), 2),
            "rssi_slope": round(slope, 2),
            "timestamp": time.time(),
        }

    def get_spectrum(self, fft_size=1024):
        noise = -95 + np.random.randn(fft_size) * 2

        center = fft_size // 2 + int(40 * np.sin(self.phase))
        self.phase += 0.1

        spectrum = noise.copy()
        spectrum[max(0, center-4):min(fft_size, center+4)] += 30

        return spectrum.tolist()


# =====================================================
# RTL-SDR PACKET SOURCE
# =====================================================

def iq_to_rssi_db(samples):
    """
    Convert complex IQ samples → RSSI (dB)
    """
    power = np.mean(np.abs(samples) ** 2)
    rssi_db = 10 * np.log10(power + 1e-12)
    return round(float(rssi_db), 2)


class RtlSdrPacketSource:
    def __init__(self):
        try:
            from rtlsdr import RtlSdr
            self.sdr = RtlSdr()
            self.sdr.sample_rate = 2.4e6
            self.sdr.center_freq = 137e6   # NOAA band
            self.sdr.gain = "auto"
        except Exception:
            self.sdr = None

    def get_packet(self):
        """
        Returns REAL RSSI packet usable by ML + dashboard
        """
        if self.sdr is None:
            # Fallback jitter for testing without hardware
            return {
                "type": "RTL_SDR_FALLBACK",
                "rssi_db": round(random.uniform(-82, -78), 2),
                "timestamp": time.time(),
            }

        try:
            samples = self.sdr.read_samples(4096)
            rssi = iq_to_rssi_db(samples)

            return {
                "type": "RTL_SDR",
                "rssi_db": rssi,
                "timestamp": time.time(),
            }
        except Exception:
            return {
                "type": "RTL_SDR_ERROR",
                "rssi_db": round(random.uniform(-90, -85), 2),
                "timestamp": time.time(),
            }

    def get_spectrum(self, fft_size=1024):
        samples = self.sdr.read_samples(fft_size)
        window = np.hanning(len(samples))
        fft = np.fft.fftshift(np.fft.fft(samples * window))
        power = 20 * np.log10(np.abs(fft) + 1e-12)
        return power.tolist()


# =====================================================
# SOURCE SELECTOR
# =====================================================

_demo = DemoPacketSource()
_rtl = None

def get_packet_source():
    global _rtl
    from handover.runtime import get_mode
    mode = get_mode()

    if mode == "REAL":
        if _rtl is None:
            _rtl = RtlSdrPacketSource()
        return _rtl

    return _demo
