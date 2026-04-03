from django.shortcuts import render
from django.http import JsonResponse
import random

# Satellite / orbit
from satellites.orbit import load_satellites, ts, GROUND_STATION

# Runtime mode
from handover.runtime import get_mode, set_mode

# Handover system
from handover.buffer import gs_b_buffer
from handover.controller import handover_controller
from handover.auto_handover import evaluate_handover
from handover.confidence import handover_confidence
from handover.packet_sources import get_packet_source


# =====================================================
# STATEFUL SIMULATION MEMORY (DEMO MODE ONLY)
# =====================================================
SAT_RSSI = {}
SIM_TIME_OFFSET = 0 # To accelerate satellite movement in DEMO mode


# =====================================================
# BASIC PAGES
# =====================================================
def home(request):
    return render(request, "core/home.html")


def dashboard(request):
    return render(request, "core/dashboard.html")


def satellite_map(request):
    return render(request, "core/map.html")


# =====================================================
# MODE SWITCH API
# =====================================================
def set_runtime_mode(request):
    """
    /api/set-mode/?mode=DEMO | REAL
    """
    mode = request.GET.get("mode")

    if mode not in ("DEMO", "REAL"):
        return JsonResponse({"error": "Invalid mode"}, status=400)

    set_mode(mode)
    return JsonResponse({"mode": get_mode()})


# =====================================================
# SATELLITE STATE API
# =====================================================
def satellite_state(request):
    sats = load_satellites()
    # Use global timescale for efficiency
    from satellites.orbit import ts as ts_global
    from datetime import timedelta
    
    mode = get_mode()
    
    # ---------------------------------------------
    # TIME CALCULATION (ACCELERATED IN DEMO MODE)
    # ---------------------------------------------
    global SIM_TIME_OFFSET
    if mode == "DEMO":
        SIM_TIME_OFFSET += 30 # Reduced from 120 to 30 for smoother movement
        # Use a fixed start time for the simulation so it's reproducible and consistently moves
        # instead of jumping relative to 'now' which changes every second
        from datetime import datetime, timezone
        start_time = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        t = ts_global.from_datetime(start_time + timedelta(seconds=SIM_TIME_OFFSET))
    else:
        t = ts_global.now()
    
    visible = []

    # ---------------------------------------------
    # Find visible satellites (scan more for better variety)
    # ---------------------------------------------
    for sat in sats[:200]:
        topo = (sat - GROUND_STATION).at(t)
        alt, az, dist = topo.altaz()

        if alt.degrees < 10:
            continue

        sp = sat.at(t).subpoint()

        visible.append({
            "name": sat.name,
            "lat": sp.latitude.degrees,
            "lon": sp.longitude.degrees,
            "alt_km": round(sp.elevation.km, 2),
            "elevation": round(alt.degrees, 4), # Higher precision for smoother tracking
        })

    if not visible:
        return JsonResponse({
            "satellites": [],
            "handover_active": False,
            "decision": "NO_SATELLITES",
            "confidence": 0.0,
        })

    # ---------------------------------------------
    # Sort by elevation (highest first)
    # ---------------------------------------------
    visible.sort(key=lambda x: x["elevation"], reverse=True)

    # ---------------------------------------------
    # RSSI ASSIGNMENT
    # ---------------------------------------------
    packet_source = get_packet_source()

    real_rssi = None
    if mode == "REAL":
        pkt = packet_source.get_packet()
        real_rssi = pkt.get("rssi_db", -80.0)

    for sat in visible:
        sat["role"] = "available"

        if mode == "DEMO":
            name = sat["name"]

            # Base RSSI on elevation to make it dynamic
            # Max RSSI at 90 deg elevation, Min at 10 deg
            elev = sat["elevation"]
            base_rssi = -80 + (elev - 10) * (40 / 80) # Range -80 to -40
            
            # Add reduced jitter for stability
            jitter = random.uniform(-0.5, 0.5)
            sat["rssi_db"] = round(base_rssi + jitter, 2)
            SAT_RSSI[name] = sat["rssi_db"]
        else:
            sat["rssi_db"] = round(real_rssi, 2)

    # ---------------------------------------------
    # Initialize CURRENT satellite if none or lost
    # ---------------------------------------------
    current_name = handover_controller.current_satellite
    current = next((s for s in visible if s["name"] == current_name), None)
    
    if current is None and visible:
        current = visible[0]
        handover_controller.current_satellite = current["name"]

    # ---------------------------------------------
    # CANDIDATE satellite (next best)
    # ---------------------------------------------
    candidate = None
    for sat in visible:
        if current and sat["name"] != current["name"]:
            candidate = sat
            break

    # ---------------------------------------------
    # CONFIDENCE
    # ---------------------------------------------
    confidence = (
        handover_confidence(current, candidate)
        if current and candidate else 0.0
    )

    # ---------------------------------------------
    # AUTO HANDOVER (FIXED CALL)
    # ---------------------------------------------
    decision = (
    evaluate_handover(current, candidate, confidence)
    if current and candidate else "NO_CANDIDATE"
)


    # ---------------------------------------------
    # ROLE ASSIGNMENT (CRITICAL)
    # ---------------------------------------------
    for sat in visible:
        if current and sat["name"] == current["name"]:
            sat["role"] = "current"
        elif candidate and sat["name"] == candidate["name"]:
            sat["role"] = "candidate"

    # ---------------------------------------------
    # Promote candidate after handover
    # ---------------------------------------------
    if decision == "HANDOVER_COMPLETED" and candidate:
        handover_controller.current_satellite = candidate["name"]

    response = JsonResponse({
        "timestamp": t.utc_iso(),
        "satellites": visible,
        "handover_active": handover_controller.handover_active,
        "buffer_size": gs_b_buffer.size(),
        "decision": decision,
        "confidence": round(confidence * 100, 2),  # percent for UI
    })
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# =====================================================
# WATERFALL DATA API
# =====================================================
def waterfall_data(request):
    source = get_packet_source()

    if hasattr(source, "get_spectrum"):
        spectrum = source.get_spectrum()
    else:
        spectrum = [random.uniform(-100, -40) for _ in range(1024)]

    return JsonResponse({"spectrum": spectrum})


# =====================================================
# PACKET FLOW / BUFFER
# =====================================================
def simulate_packet_flow(request):
    source = get_packet_source()
    packet = source.get_packet()

    if handover_controller.handover_active:
        gs_b_buffer.store_packet(packet)
        return JsonResponse({
            "status": "buffered",
            "buffer_size": gs_b_buffer.size(),
            "rssi_db": packet.get("rssi_db"),
        })

    return JsonResponse({
        "status": "received",
        "rssi_db": packet.get("rssi_db"),
    })


# =====================================================
# BUFFER STATUS
# =====================================================
def buffer_status(request):
    return JsonResponse({
        "mode": get_mode(),
        "handover_active": handover_controller.handover_active,
        "buffer_size": gs_b_buffer.size(),
    })


# =====================================================
# SATELLITE POSITIONS (MAP)
# =====================================================
def satellite_positions(request):
    sats = load_satellites()
    from satellites.orbit import ts as ts_global
    from datetime import timedelta, datetime, timezone
    mode = get_mode()
    
    # Sync with simulation time
    if mode == "DEMO":
        start_time = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        t = ts_global.from_datetime(start_time + timedelta(seconds=SIM_TIME_OFFSET))
    else:
        t = ts_global.now()

    data = []
    for sat in sats[:200]: # Match scan count
        sp = sat.at(t).subpoint()
        data.append({
            "name": sat.name,
            "lat": sp.latitude.degrees,
            "lon": sp.longitude.degrees,
            "alt_km": round(sp.elevation.km, 2),
        })

    return JsonResponse(data, safe=False)


# =====================================================
# MANUAL HANDOVER (DEBUG)
# =====================================================
def trigger_handover(request):
    action = request.GET.get("action")

    if action == "start":
        handover_controller.start_handover()
        return JsonResponse({"status": "handover_started"})

    if action == "end":
        packets = handover_controller.end_handover()
        return JsonResponse({
            "status": "handover_completed",
            "replayed_packets": len(packets),
        })

    return JsonResponse({
        "error": "Invalid action. Use ?action=start or ?action=end"
    })
