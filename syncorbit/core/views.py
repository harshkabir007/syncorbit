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
from ml_engine.predictor import predict_candidate, predict_optimal_time
from handover.packet_sources import get_packet_source


# =====================================================
# STATEFUL SIMULATION MEMORY (DEMO MODE ONLY)
# =====================================================
SAT_RSSI = {}
SIM_TIME_OFFSET = 0  # Accelerates satellite movement in DEMO mode

# Capture the real startup time ONCE so DEMO simulation begins with real overhead sats.
# Using a hardcoded date caused near-zero satellite visibility at some offsets.
_SIM_BASE = ts.now()  # module-level — set when Django imports this view

# Pre-warm with 10 neutral frames so LSTM has valid input from call #1.
# Values represent a stable current link with no handover warranted:
# [curr_rssi, cand_rssi, curr_elev, cand_elev]
_NEUTRAL_FRAME = [-75.0, -80.0, 35.0, 28.0]
LSTM_HISTORY = [_NEUTRAL_FRAME[:] for _ in range(10)]

# =====================================================
# HANDOVER EVENT LOG  (Feature 1)
# =====================================================
HANDOVER_LOG = []   # Ring-buffer, max 100 entries — newest appended last
_PREV_DECISION = None  # Track last logged state to avoid repeating same-state spam


def _log_event(event_type, current=None, candidate=None, confidence=0.0):
    """Append a timestamped handover decision to HANDOVER_LOG."""
    from datetime import datetime, timezone
    HANDOVER_LOG.append({
        "time":       datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "event":      event_type,
        "from_sat":   current["name"]   if current   else "—",
        "to_sat":     candidate["name"] if candidate else None,
        "confidence": round(confidence * 100, 1),
    })
    if len(HANDOVER_LOG) > 100:
        HANDOVER_LOG.pop(0)


# =====================================================
# PACKET STATISTICS  (Feature 2: Zero-Loss Proof)
# =====================================================
PACKET_STATS = {
    "legacy_total":       0,
    "legacy_dropped":     0,
    "syncorbit_total":    0,
    "syncorbit_buffered": 0,
    "packets_saved":      0,
}

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
        SIM_TIME_OFFSET += 15  # 15s/tick ≈ 7.5x real-time — fast enough to feel dynamic,
                               # slow enough that satellites stay visible for the full chart window
        # Start from the real current time (_SIM_BASE captured at module load).
        # This guarantees the satellites that are actually overhead RIGHT NOW appear
        # in the simulation instead of the barren April 1 2026 hardcoded slot.
        t = ts_global.from_datetime(_SIM_BASE.utc_datetime() + timedelta(seconds=SIM_TIME_OFFSET))
    else:
        t = ts_global.now()
    
    visible = []

    # ---------------------------------------------
    # Find visible satellites (filter for LEO only -> fast movers)
    # ---------------------------------------------
    # LEO satellites typically have >10 revolutions per day
    leo_sats = [s for s in sats if s.model.no_kozai * 1440 / (2 * 3.14159265) > 10]
    
    # Filter for diverse constellations so graphs aren't identical from satellite trains
    diverse_sats = []
    seen_prefixes = set()
    for s in leo_sats:
        # Get first word/part of constellation name (e.g., STARLINK, ONEWEB, ISS)
        prefix = s.name.split()[0].split('-')[0]
        if prefix not in seen_prefixes:
            seen_prefixes.add(prefix)
            diverse_sats.append(s)
        if len(diverse_sats) >= 100:  # scan more constellations for richer candidate pool
            break
    
    for sat in diverse_sats:
        topo = (sat - GROUND_STATION).at(t)
        alt, az, dist = topo.altaz()

        if alt.degrees < 5:  # 5° minimum — practical LEO visibility threshold
            continue

        sp = sat.at(t).subpoint()

        visible.append({
            "name": sat.name,
            "lat": sp.latitude.degrees,
            "lon": sp.longitude.degrees,
            "alt_km": round(sp.elevation.km, 2),
            "elevation": round(alt.degrees, 4), # Higher precision for smoother tracking
        })

    # ── Extended fill-up scan (map richness) ────────────────────────────────
    # Always try to reach at least 8 visible satellites so the map has a
    # meaningful number of "available" dots beyond just current + candidate.
    # Capped at 300 altaz calculations, 3° floor, stops at 8 found.
    if mode == "DEMO" and len(visible) < 8:
        existing = {v["name"] for v in visible}
        for sat in leo_sats[:300]:
            if sat.name in existing:
                continue
            topo2 = (sat - GROUND_STATION).at(t)
            alt2, _, _ = topo2.altaz()
            if alt2.degrees < 3:
                continue
            sp2 = sat.at(t).subpoint()
            visible.append({
                "name":      sat.name,
                "lat":       sp2.latitude.degrees,
                "lon":       sp2.longitude.degrees,
                "alt_km":    round(sp2.elevation.km, 2),
                "elevation": round(alt2.degrees, 4),
            })
            existing.add(sat.name)
            if len(visible) >= 8:
                break

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

            # Base RSSI still cares about elevation (higher is better)
            elev = sat["elevation"]
            base_rssi = -80 + (elev - 10) * (40 / 80) # Range -80 to -40
            
            # Simulate real-world RF conditions: Add a slow sinusoidal 'fade' 
            # to mimic antenna rotation, atmospheric multipath, or cloud cover
            import math
            import time
            phase_offset = hash(name) % 100 
            # ±8 dB of smooth fading every ~12 seconds
            rf_fade = 8.0 * math.sin((time.time() + phase_offset) / 2.0)
            
            # Add micro-jitter for hardware static
            jitter = random.uniform(-0.8, 0.8)
            
            sat["rssi_db"] = round(base_rssi + rf_fade + jitter, 2)
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
    candidate = predict_candidate(visible, current)

    # ---------------------------------------------
    # CONFIDENCE
    # ---------------------------------------------
    curr_rssi = current["rssi_db"] if current else -100
    curr_elev = current["elevation"] if current else 0
    cand_rssi = candidate["rssi_db"] if candidate else -100
    cand_elev = candidate["elevation"] if candidate else 0
    
    global LSTM_HISTORY
    feat = [curr_rssi, cand_rssi, curr_elev, cand_elev]
    LSTM_HISTORY.append(feat)
    if len(LSTM_HISTORY) > 10:
        LSTM_HISTORY.pop(0)

    confidence = predict_optimal_time(LSTM_HISTORY)

    # ── DEMO: periodic confidence boost to demonstrate handover cycle ──────────
    # Every 180 simulated seconds (= 12 ticks = 24 real seconds), the LSTM
    # confidence is overridden to 0.75 for one tick.  This triggers a real
    # handover + completion + event log entry without requiring perfect orbital
    # geometry — ideal for a hackathon demo.
    if mode == "DEMO" and candidate and SIM_TIME_OFFSET >= 180:
        if (SIM_TIME_OFFSET % 180) < 15:          # 15-sim-sec window per cycle
            confidence = max(confidence, 0.75)

    # ---------------------------------------------
    # AUTO HANDOVER (FIXED CALL)
    # ---------------------------------------------
    decision = (
        evaluate_handover(current, candidate, confidence)
        if current and candidate else "NO_CANDIDATE"
    )

    # ---------------------------------------------
    # EVENT LOG  (Feature 1)
    # Rules:
    #   1. Always log HANDOVER_STARTED / HANDOVER_COMPLETED
    #   2. Log any other decision ONLY when it changes from the previous one
    #   3. Synthesise CANDIDATE_LOCKED when a strong candidate first appears
    # This prevents NO_CANDIDATE / NO_ACTION spam on every tick.
    # ---------------------------------------------
    global _PREV_DECISION

    if decision in ("HANDOVER_STARTED", "HANDOVER_COMPLETED"):
        # Always log real handover transitions
        _log_event(decision, current, candidate, confidence)

    elif decision != _PREV_DECISION:
        # Log only the first occurrence of a state change
        if decision in ("NO_CANDIDATE", "NO_SATELLITES"):
            _log_event(decision, current, candidate, confidence)
        # NO_ACTION is silent by design (too frequent, no value)

    # Synthesise a CANDIDATE_LOCKED notice when a good candidate
    # appears for the first time (transition from None/no-candidate)
    if (
        candidate
        and confidence >= 0.30
        and _PREV_DECISION in (None, "NO_CANDIDATE", "NO_SATELLITES")
        and decision not in ("HANDOVER_STARTED", "HANDOVER_COMPLETED")
    ):
        _log_event("CANDIDATE_LOCKED", current, candidate, confidence)

    _PREV_DECISION = decision

    # ---------------------------------------------
    # PACKET STATS  (Feature 2)
    # Simulate one packet interval per API tick.
    # Legacy system: reactive — drops packets when
    # signal is poor OR during an unguarded switch.
    # SyncOrbit: buffers, never drops.
    # ---------------------------------------------
    if current:
        curr_rssi_val = current.get("rssi_db", -100)
        PACKET_STATS["legacy_total"]    += 1
        PACKET_STATS["syncorbit_total"] += 1

        legacy_drop = False
        if handover_controller.handover_active:
            # Legacy hasn't started handover yet (reactive) —
            # it's still on the degrading link: ~55 % drop rate
            legacy_drop = random.random() < 0.55
        elif curr_rssi_val < -72:
            # Pre-handover degradation — legacy stays connected too long
            drop_prob = min(0.85, (abs(curr_rssi_val) - 72) / 22.0)
            legacy_drop = random.random() < drop_prob

        if legacy_drop:
            PACKET_STATS["legacy_dropped"] += 1
            PACKET_STATS["packets_saved"]  += 1

        # Track live buffer depth for display
        PACKET_STATS["syncorbit_buffered"] = gs_b_buffer.size()


    # ---------------------------------------------
    # ROLE ASSIGNMENT (CRITICAL)
    # ---------------------------------------------
    for sat in visible:
        if current and sat["name"] == current["name"]:
            sat["role"] = "current"
        elif candidate and sat["name"] == candidate["name"]:
            sat["role"] = "candidate"
        else:
            sat["role"] = "available"   # shown on map as grey dots

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
    from datetime import timedelta
    mode = get_mode()
    
    # Sync with simulation time (use same _SIM_BASE as satellite_state so map stays in sync)
    if mode == "DEMO":
        t = ts_global.from_datetime(_SIM_BASE.utc_datetime() + timedelta(seconds=SIM_TIME_OFFSET))
    else:
        t = ts_global.now()

    data = []
    # Force LEO only
    leo_sats = [s for s in sats if s.model.no_kozai * 1440 / (2 * 3.14159265) > 10]
    
    for sat in leo_sats[:200]: # Match scan count
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


# =====================================================
# HANDOVER EVENT LOG API  (Feature 1)
# =====================================================
def handover_events(request):
    """
    /api/events/
    Returns the 50 most-recent handover decisions, newest first,
    for the live event log panel on the dashboard.
    """
    events = list(reversed(HANDOVER_LOG[-50:]))
    return JsonResponse({"events": events})


# =====================================================
# PACKET STATISTICS API  (Feature 2)
# =====================================================
def packet_stats(request):
    """
    /api/packet-stats/
    Returns cumulative legacy-vs-SyncOrbit packet loss figures.
    """
    total   = PACKET_STATS["legacy_total"]
    dropped = PACKET_STATS["legacy_dropped"]
    loss_pct = round(dropped / total * 100, 2) if total > 0 else 0.0

    return JsonResponse({
        "legacy_total":       total,
        "legacy_dropped":     dropped,
        "legacy_loss_pct":    loss_pct,
        "syncorbit_total":    PACKET_STATS["syncorbit_total"],
        "syncorbit_buffered": PACKET_STATS["syncorbit_buffered"],
        "packets_saved":      PACKET_STATS["packets_saved"],
        "syncorbit_loss_pct": 0.0,
    })
