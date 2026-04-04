# Global runtime state
# Initialised from Django settings so SYNCORBIT_MODE in settings.py is honoured
# on every server start instead of always defaulting to "DEMO".
try:
    from django.conf import settings as _settings
    RUNTIME_MODE = getattr(_settings, 'SYNCORBIT_MODE', 'DEMO')
except Exception:
    RUNTIME_MODE = 'DEMO'


def set_mode(mode: str):
    global RUNTIME_MODE
    if mode in ("DEMO", "REAL"):
        RUNTIME_MODE = mode


def get_mode():
    return RUNTIME_MODE
