import numpy as np

def compute_rssi_db(iq_samples):
    """
    Compute RSSI in dB from IQ samples
    iq_samples: complex numpy array
    """
    power = np.mean(np.abs(iq_samples) ** 2)

    if power <= 0:
        return -100.0  # noise floor fallback

    rssi_db = 10 * np.log10(power)
    return round(rssi_db, 2)
