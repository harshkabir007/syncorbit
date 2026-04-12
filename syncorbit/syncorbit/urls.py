from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # All pages + APIs are owned by the core app
    path("", include("core.urls")),

    # Handover simulation sub-app
    path("simulation/", include("handover.urls")),

    # Admin
    path("admin/", admin.site.urls),
]
