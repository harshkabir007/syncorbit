import numpy as np

def extract_rf_features(samples, prev_rssi=None):
    # Power & RSSI
    power = np.mean(np.abs(samples) ** 2)
    rssi_db = 10 * np.log10(power + 1e-12)

    # Noise estimate (lower percentile)
    noise_power = np.percentile(np.abs(samples) ** 2, 20)
    noise_db = 10 * np.log10(noise_power + 1e-12)

    snr_db = rssi_db - noise_db

    rssi_slope = 0.0
    if prev_rssi is not None:
        rssi_slope = rssi_db - prev_rssi

    return {
        "rssi_db": float(rssi_db),
        "noise_db": float(noise_db),
        "snr_db": float(snr_db),
        "rssi_slope": float(rssi_slope),
    }
