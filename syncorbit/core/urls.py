from django.urls import path
from . import views

urlpatterns = [
    # ── Pages ──────────────────────────────────────────
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("map/", views.satellite_map, name="satellite_map"),

    # ── Satellite APIs ─────────────────────────────────
    path("api/satellite-state/", views.satellite_state, name="satellite_state"),
    # Two kept for compatibility (/api/satellites/ was in the old main urls.py)
    path("api/satellites/", views.satellite_positions, name="satellite_positions"),
    path("api/satellite-positions/", views.satellite_positions),  # legacy alias

    # ── Signal / Spectrum ──────────────────────────────
    path("api/waterfall/", views.waterfall_data, name="waterfall"),

    # ── Handover & Buffer ──────────────────────────────
    path("api/simulate-packet/", views.simulate_packet_flow, name="simulate_packet"),
    # Two kept for compatibility (/api/handover/ was in the old main urls.py)
    path("api/handover/", views.trigger_handover, name="trigger_handover"),
    path("api/trigger-handover/", views.trigger_handover),  # legacy alias
    path("api/buffer-status/", views.buffer_status, name="buffer_status"),

    # ── Mode switch ────────────────────────────────────
    path("api/set-mode/", views.set_runtime_mode, name="set_mode"),

    # ── Feature 1: Live Event Log ──────────────────────
    path("api/events/", views.handover_events, name="handover_events"),

    # ── Feature 2: Zero-Loss Packet Stats ─────────────
    path("api/packet-stats/", views.packet_stats, name="packet_stats"),
]

