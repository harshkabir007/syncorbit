from django.contrib import admin
from django.urls import path , include
from core.views import buffer_status
from core.views import set_runtime_mode
from core.views import waterfall_data
from core import views






from core.views import (
    home,
    dashboard,
    satellite_map,
    satellite_positions,
    satellite_state,
    simulate_packet_flow,
    trigger_handover,
)

urlpatterns = [
    # Pages
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("map/", satellite_map, name="satellite_map"),
    path("", include("core.urls")),
    path("api/set-mode/", set_runtime_mode),
    path("api/waterfall/", views.waterfall_data),


    # Satellite APIs
    path("api/satellites/", satellite_positions, name="satellite_positions"),
    path("api/satellite-state/", satellite_state, name="satellite_state"),

    # Handover & Buffer APIs
    path("api/simulate-packet/", simulate_packet_flow, name="simulate_packet"),
    path("api/handover/", trigger_handover, name="trigger_handover"),

    # Admin
    path("admin/", admin.site.urls),
    path("api/buffer-status/", buffer_status, name="buffer_status"),

]
