# handover/packet_sources/real_source.py
import numpy as np
import time
try:
    from rtlsdr import RtlSdr
except Exception:
    RtlSdr = None

class RealPacketSource:
    def __init__(self):
        self.sdr = RtlSdr()
        self.sdr.sample_rate = 2.4e6
        self.sdr.center_freq = 137.62e6
        self.sdr.gain = "auto"

        self.prev_rssi = None

    def get_spectrum(self, fft_size=1024):
        samples = self.sdr.read_samples(fft_size)
        window = np.hanning(len(samples))
        fft = np.fft.fftshift(np.fft.fft(samples * window))
        power_db = 20 * np.log10(np.abs(fft) + 1e-12)
        return power_db.tolist()

    def get_packet(self):
        spectrum = self.get_spectrum()

        if not spectrum:
            return None

        rssi = max(spectrum)
        slope = 0 if self.prev_rssi is None else rssi - self.prev_rssi
        self.prev_rssi = rssi

        return {
            "type": "RTL_SDR",
            "timestamp": time.time(),
            "rssi_db": round(rssi, 2),
            "rssi_slope": round(slope, 2),
        }
