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
# STATEFUL RSSI MEMORY (DEMO MODE ONLY)
# =====================================================
SAT_RSSI = {}


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
    t = ts.now()
    mode = get_mode()

    visible = []

    # ---------------------------------------------
    # Find visible satellites
    # ---------------------------------------------
    for sat in sats[:50]:
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
            "elevation": round(alt.degrees, 2),
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

            if name not in SAT_RSSI:
                SAT_RSSI[name] = random.uniform(-85, -55)

            SAT_RSSI[name] += random.uniform(-1.0, 1.0)
            SAT_RSSI[name] = max(-95, min(-40, SAT_RSSI[name]))

            sat["rssi_db"] = round(SAT_RSSI[name], 2)
        else:
            sat["rssi_db"] = round(real_rssi, 2)

    # ---------------------------------------------
    # Initialize CURRENT satellite once
    # ---------------------------------------------
    if handover_controller.current_satellite is None:
        handover_controller.current_satellite = visible[0]["name"]

    # ---------------------------------------------
    # CURRENT satellite
    # ---------------------------------------------
    current = next(
        (s for s in visible if s["name"] == handover_controller.current_satellite),
        None
    )

    # ---------------------------------------------
    # CANDIDATE satellite (next best, ALWAYS)
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

    return JsonResponse({
        "satellites": visible,
        "handover_active": handover_controller.handover_active,
        "decision": decision,
        "confidence": round(confidence * 100, 2),  # percent for UI
    })


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
    t = ts.now()

    data = []
    for sat in sats[:50]:
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
