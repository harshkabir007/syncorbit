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


def load_satellites():
    global _satellites

    if _satellites is None:
        if not Path(TLE_FILE).exists():
            print("⬇️ Downloading TLEs from CelesTrak...")
            load.download(TLE_URL, TLE_FILE)

        _satellites = load.tle_file(TLE_FILE)
        print(f"✅ Loaded {len(_satellites)} satellites")

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
