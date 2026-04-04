from skyfield.api import load, wgs84
from pathlib import Path

TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
TLE_FILE = str(Path(__file__).resolve().parent / "active.tle")

GROUND_STATION = wgs84.latlon(
    latitude_degrees=28.6139,
    longitude_degrees=77.2090,
    elevation_m=216
)

ts = load.timescale()
_satellites = None


import time
import urllib.request

def load_satellites():
    global _satellites

    file_path = Path(TLE_FILE)
    
    # Needs download if file doesn't exist or is older than 12 hours
    needs_download = True
    if file_path.exists():
        age = time.time() - file_path.stat().st_mtime
        if age <= 43200: # 43200 seconds = 12 hours
            needs_download = False
            
    if needs_download:
        # print("⬇️ Downloading TLEs from CelesTrak (updated every 12h)...")
        try:
            urllib.request.urlretrieve(TLE_URL, TLE_FILE)
            # Re-load from modified file
            _satellites = load.tle_file(TLE_FILE)
            # print(f"✅ Loaded {len(_satellites)} satellites dynamically")
        except Exception as e:
            print(f"⚠️ Failed to download TLE: {e}")
            if _satellites is None and file_path.exists():
                _satellites = load.tle_file(TLE_FILE)
    elif _satellites is None:
        if file_path.exists():
            _satellites = load.tle_file(TLE_FILE)
        else:
            print("⚠️ No TLE file exists and download skipped.")

    return _satellites


def get_visible_satellites(min_elevation=10):
    sats = load_satellites()
    t = ts.now()
    visible = []

    for sat in sats:
        difference = sat - GROUND_STATION
        topocentric = difference.at(t)
        alt, az, distance = topocentric.altaz()

        if alt.degrees >= min_elevation:
            visible.append({
                "name": sat.name,
                "elevation": round(alt.degrees, 2),
                "azimuth": round(az.degrees, 2),
                "distance": round(distance.km, 2)
            })

    return visible
