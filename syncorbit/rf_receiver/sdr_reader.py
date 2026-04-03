import numpy as np

try:
    from rtlsdr import RtlSdr
    sdr = RtlSdr()
    sdr.sample_rate = 2.048e6
    sdr.center_freq = 1.6e9   # example L-band
    sdr.gain = 'auto'
except Exception:
    sdr = None

def read_rssi():
    samples = sdr.read_samples(256*1024)
    power = np.mean(np.abs(samples)**2)
    return 10 * np.log10(power)
