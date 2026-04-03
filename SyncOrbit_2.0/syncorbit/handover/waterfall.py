import numpy as np

def compute_waterfall(samples, fft_size=512):
    """
    Convert IQ samples → power spectrum (dB)
    """
    window = np.hanning(len(samples))
    spectrum = np.fft.fftshift(np.fft.fft(samples * window, fft_size))
    power = 20 * np.log10(np.abs(spectrum) + 1e-9)

    return power.tolist()
