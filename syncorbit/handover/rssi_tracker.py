class RssiTracker:
    def __init__(self):
        self.rssi_map = {}

    def update(self, sat_name, rssi):
        self.rssi_map[sat_name] = rssi

    def get(self, sat_name):
        return self.rssi_map.get(sat_name)

    def all(self):
        return self.rssi_map
