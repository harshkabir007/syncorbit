# Global runtime state (safe for demo)
RUNTIME_MODE = "DEMO"  # or "REAL"

def set_mode(mode: str):
    global RUNTIME_MODE
    if mode in ("DEMO", "REAL"):
        RUNTIME_MODE = mode

def get_mode():
    return RUNTIME_MODE
