def execute_handover(curr_rssi, next_rssi):
    if next_rssi > curr_rssi:
        return True
    return False
