from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path("dashboard/", views.dashboard),
    path("map/", views.satellite_map),

    # APIs
    path("api/satellite-state/", views.satellite_state),
    path("api/satellite-positions/", views.satellite_positions),
    path("api/buffer-status/", views.buffer_status),
    path("api/simulate-packet/", views.simulate_packet_flow),
    path("api/trigger-handover/", views.trigger_handover),
    path("api/set-mode/", views.set_runtime_mode),
]
