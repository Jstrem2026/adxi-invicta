"""Invicta canon geometry -> graybox pieces.  Pure Python (standard library only).

Reads the Revision B CSVs in Docs/geometry_revB and turns a deck outline into
strips of floor and wall boxes that Unreal can place.  No Unreal code here, so
this file can be tested with any Python 3 (see test_invicta_geometry.py).

Ship frame (canon CSV axes):  x km from the prow tip (0) toward the stern (34),
y km across the beam (port negative), z km above the keel.

Unreal frame (this project):  origin at the ship's centre (x 17 km, y 0, z 2.05 km),
+X toward the bow, +Y to starboard, +Z up, units centimetres.
So standing on a deck facing the bow, port is on your left.
"""

import math
import csv
import os

KM_TO_CM = 100000.0
SHIP_CENTRE_X_KM = 17.0
SHIP_CENTRE_Z_KM = 2.05

# Floor and ceiling elevations above the keel, metres (canon data sheets S1-S8).
DECKS = {
    1: ("Solenne", 3540, 3920),
    2: ("Halcyon", 3100, 3480),
    3: ("Meridian", 2660, 3040),
    4: ("Bastion", 2220, 2600),
    5: ("Aerion", 1560, 2160),
    6: ("Machina", 1120, 1500),
    7: ("Claustra", 680, 1060),
    8: ("Ferrum", 240, 620),
}

# Keelway stops on Deck 5 (data sheet S5): name -> frame number (frames are 500 m apart).
AERION_KEELWAY_STOPS = {
    "Strike Hangars": 3,
    "Port": 46,
    "Atrium Central": 52,
    "Pilots' Quarter": 65,
}
FRAME_SPACING_KM = 0.5
LANES = "ABCDEFGHIJKLMNOPQRSTUVWXY"  # 25 lanes, 500 m apart, A = port edge, M = centreline


def lane_to_y_km(lane):
    return (LANES.index(lane.upper()) - 12) * 0.5


def frame_to_x_km(frame):
    return frame * FRAME_SPACING_KM


def to_unreal_cm(x_km, y_km, z_km):
    """Ship-frame km -> Unreal world centimetres (X bow, Y starboard, Z up)."""
    return (
        (SHIP_CENTRE_X_KM - x_km) * KM_TO_CM,
        y_km * KM_TO_CM,
        (z_km - SHIP_CENTRE_Z_KM) * KM_TO_CM,
    )


def read_outline(path):
    """Return a list of (x_km, y_km) points from a deck or hull-plan CSV."""
    pts = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            keys = list(row.keys())
            pts.append((float(row[keys[0]]), float(row[keys[1]])))
    return pts


def deck_csv_path(geometry_dir, deck, kind="net"):
    name = DECKS[deck][0]
    return os.path.join(geometry_dir, "deck%d_%s_%s_km_revB.csv" % (deck, name, kind))


def half_width_at(outline, x):
    """Largest |y| where the vertical line at x crosses the outline (0 if outside)."""
    best = 0.0
    n = len(outline)
    for i in range(n):
        x1, y1 = outline[i]
        x2, y2 = outline[(i + 1) % n]
        lo, hi = min(x1, x2), max(x1, x2)
        if lo <= x <= hi:
            if hi - lo < 1e-12:
                best = max(best, abs(y1), abs(y2))
            else:
                t = (x - x1) / (x2 - x1)
                best = max(best, abs(y1 + t * (y2 - y1)))
    return best


def x_extent(outline):
    xs = [p[0] for p in outline]
    return min(xs), max(xs)


def polygon_area(outline):
    a = 0.0
    n = len(outline)
    for i in range(n):
        x1, y1 = outline[i]
        x2, y2 = outline[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def strips(outline, step_km=0.25):
    """Cut the outline into bow-to-stern strips.

    Each strip is (x0, x1, half_width_km).  The half width is the narrowest of
    the start, middle and end of the strip, so the floor never pokes outside
    the canon outline (it under-fills tapered ends slightly, which is safe).
    """
    x_min, x_max = x_extent(outline)
    out = []
    x0 = x_min
    while x0 < x_max - 1e-9:
        x1 = min(x0 + step_km, x_max)
        hw = min(half_width_at(outline, x0 + 1e-6),
                 half_width_at(outline, (x0 + x1) / 2.0),
                 half_width_at(outline, x1 - 1e-6))
        if hw > 0.001:
            out.append((x0, x1, hw))
        x0 = x1
    return out


def box(name, centre_km, size_km, folder, roll_deg=0.0):
    """A box piece: centre in ship km, size in km (length along x, width along y, height along z),
    optionally rolled about the ship's x axis (truss diagonals in a y-z plane)."""
    p = {"name": name, "centre_km": centre_km, "size_km": size_km, "folder": folder}
    if roll_deg:
        p["roll_deg"] = roll_deg
    return p


def wall_segments(x0, x1, z_floor, z_ceil, cutouts):
    """Split one wall strip around cutouts.

    cutouts: list of (cx0, cx1, top_km): the wall is open from the floor up to
    top_km (km above the keel) between cx0 and cx1.
    Returns (sx0, sx1, z_bottom, z_top) boxes that together form the wall.
    """
    cuts = sorted((max(a, x0), min(b, x1), top) for a, b, top in cutouts if a < x1 and b > x0)
    out = []
    x = x0
    for a, b, top in cuts:
        if a > x + 1e-9:
            out.append((x, a, z_floor, z_ceil))
        out.append((a, b, top, z_ceil))      # wall above the opening
        x = b
    if x < x1 - 1e-9:
        out.append((x, x1, z_floor, z_ceil))
    return out


def deck_graybox(geometry_dir, deck=5, step_km=0.25, floor_thickness_m=10.0,
                 wall_thickness_m=20.0, build_ceiling=False, port_cutouts=None):
    """All the boxes for one deck: floor strips, side walls, step walls, optional ceiling.

    port_cutouts: openings in the port hull wall, see wall_segments().
    """
    name, floor_m, ceil_m = DECKS[deck]
    outline = read_outline(deck_csv_path(geometry_dir, deck, "net"))
    z_floor = floor_m / 1000.0
    z_ceil = ceil_m / 1000.0
    height = z_ceil - z_floor
    ft = floor_thickness_m / 1000.0
    wt = wall_thickness_m / 1000.0
    base = "D%d_%s" % (deck, name)
    pieces = []
    s = strips(outline, step_km)
    for i, (x0, x1, hw) in enumerate(s):
        length = x1 - x0
        xc = (x0 + x1) / 2.0
        pieces.append(box("%s_Floor_%03d" % (base, i), (xc, 0.0, z_floor - ft / 2), (length, 2 * hw, ft), base + "/Floor"))
        if build_ceiling:
            pieces.append(box("%s_Ceiling_%03d" % (base, i), (xc, 0.0, z_ceil + ft / 2), (length, 2 * hw, ft), base + "/Ceiling"))
        for side, sign in (("Port", -1), ("Stbd", 1)):
            segs = wall_segments(x0, x1, z_floor, z_ceil, port_cutouts or []) if side == "Port" \
                else [(x0, x1, z_floor, z_ceil)]
            for k, (sx0, sx1, zb, zt) in enumerate(segs):
                label = "%s_Wall%s_%03d" % (base, side, i) + ("" if len(segs) == 1 else "_s%d" % k)
                pieces.append(box(label, ((sx0 + sx1) / 2.0, sign * (hw + wt / 2), (zb + zt) / 2.0),
                                  (sx1 - sx0, wt, zt - zb), base + "/Walls"))
    # End walls and step walls where the width changes between strips.
    for i in range(len(s) + 1):
        hw_before = s[i - 1][2] if i > 0 else 0.0
        hw_after = s[i][2] if i < len(s) else 0.0
        x = s[i][0] if i < len(s) else s[-1][1]
        inner, outer = sorted((hw_before, hw_after))
        if outer - inner < 0.001:
            continue
        span = outer - inner + wt
        for side, sign in (("Port", -1), ("Stbd", 1)):
            yc = sign * (inner + outer + wt) / 2.0 if inner > 0 else 0.0
            w = span if inner > 0 else 2 * outer + 2 * wt
            if inner == 0 and side == "Stbd":
                continue  # a bow or stern end wall spans the full width once
            pieces.append(box("%s_StepWall%s_%03d" % (base, side, i),
                              (x, yc, z_floor + height / 2),
                              (wt, w, height), base + "/Walls"))
    return pieces, s, outline


def keelway_and_markers(deck=5):
    """Keelway centreline strip, stop pillars and frame labels for Aerion."""
    _, floor_m, _ = DECKS[deck]
    z = floor_m / 1000.0
    out = {"keelway": [], "stops": [], "frames": []}
    first = frame_to_x_km(min(AERION_KEELWAY_STOPS.values()))
    last = frame_to_x_km(max(AERION_KEELWAY_STOPS.values()))
    out["keelway"].append(box("D5_Keelway", ((first + last) / 2, 0.0, z + 0.0001), (last - first, 0.02, 0.0002), "D5_Aerion/Keelway"))
    for stop, frame in AERION_KEELWAY_STOPS.items():
        x = frame_to_x_km(frame)
        out["stops"].append({"name": stop, "frame": frame, "x_km": x,
                             "pillar": box("D5_Stop_F%02d" % frame, (x, 0.03, z + 0.025), (0.02, 0.02, 0.05), "D5_Aerion/Keelway")})
    for frame in range(0, 69):
        out["frames"].append({"frame": frame, "x_km": frame_to_x_km(frame), "z_km": z})
    return out


def read_zones(path, deck=5):
    zones = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row["deck"]) == deck:
                zones.append({"kind": row["kind"], "name": row["name"],
                              "x_km": float(row["centroid_x_km"]), "y_km": float(row["centroid_y_km"])})
    return zones


# ---------------------------------------------------------------- Keelway timetable
# Canon: 230 km/h cruise (GDD). Acceleration and dwell times are our choice.
KEELWAY_SPEED_KMH = 230.0
KEELWAY_ACCEL_MS2 = 1.5        # comfortable for standing passengers
KEELWAY_DWELL_S = 30.0         # at intermediate stops
KEELWAY_TERMINUS_DWELL_S = 45.0
# One loop, starting at the stop nearest the Hall of Arrivals: sternward to the
# far end, back past Port to the bow end, then home to Port.
KEELWAY_LOOP = ["Port", "Atrium Central", "Pilots' Quarter", "Atrium Central",
                "Port", "Strike Hangars", "Port"]


def run_profile(distance_m, v_ms, a_ms2):
    """Accelerate, cruise, brake. Returns (duration_s, position_m(t) function)."""
    if distance_m <= 0:
        return 0.0, lambda t: 0.0
    if distance_m >= v_ms * v_ms / a_ms2:
        t_a = v_ms / a_ms2
        total = distance_m / v_ms + t_a
    else:  # too short to reach cruise speed
        t_a = (distance_m / a_ms2) ** 0.5
        v_ms = a_ms2 * t_a
        total = 2 * t_a

    def pos(t):
        t = min(max(t, 0.0), total)
        if t < t_a:
            return 0.5 * a_ms2 * t * t
        if t > total - t_a:
            r = total - t
            return distance_m - 0.5 * a_ms2 * r * r
        return 0.5 * a_ms2 * t_a * t_a + v_ms * (t - t_a)

    return total, pos


def keelway_timetable(speed_kmh=KEELWAY_SPEED_KMH, accel=KEELWAY_ACCEL_MS2,
                      dwell_s=KEELWAY_DWELL_S, terminus_dwell_s=KEELWAY_TERMINUS_DWELL_S,
                      loop=None, sample_s=1.0):
    """Sampled (t_s, x_km) points for one full loop, plus stop events.

    The loop starts with the train standing at loop[0] and ends arriving back
    there, so it repeats seamlessly.
    """
    loop = loop or KEELWAY_LOOP
    ends = {min(AERION_KEELWAY_STOPS, key=AERION_KEELWAY_STOPS.get),
            max(AERION_KEELWAY_STOPS, key=AERION_KEELWAY_STOPS.get)}
    v = speed_kmh / 3.6
    t = 0.0
    samples = []
    events = []
    for i, stop in enumerate(loop[:-1]):
        x0 = frame_to_x_km(AERION_KEELWAY_STOPS[stop])
        x1 = frame_to_x_km(AERION_KEELWAY_STOPS[loop[i + 1]])
        dwell = terminus_dwell_s if stop in ends else dwell_s
        events.append({"stop": stop, "arrive_s": t, "depart_s": t + dwell})
        samples.append((t, x0))
        t += dwell
        samples.append((t, x0))
        duration, pos = run_profile(abs(x1 - x0) * 1000.0, v, accel)
        sign = 1.0 if x1 > x0 else -1.0
        k = 1
        while k * sample_s < duration - 1e-6:
            samples.append((t + k * sample_s, x0 + sign * pos(k * sample_s) / 1000.0))
            k += 1
        t += duration
    samples.append((t, frame_to_x_km(AERION_KEELWAY_STOPS[loop[-1]])))
    return {"samples": samples, "events": events, "loop_s": t}


# ---------------------------------------------------------------- Arrival (M2)
# Jordan, 21 Nov 2026: the Hall of Arrivals sits on the PORT HULL WALL at frame F43,
# with a skyglass wall to space (05 §2); the arrival hangar is a flank dock beside it
# (04 §7.3: civilian ships dock at the Port of Arrivals flank docks).
# Canon: Hall 600 x 200 m (05). Sizes marked "Jordan 21 Nov" were made canon on
# 21 Nov 2026 (hangar sized for a ~30-40 m passenger shuttle). TUNE = placeholder; settled = kept as is by Jordan.
ARRIVAL = {
    "frame": 43,                 # Hall centred on F43 (x 21.5 km)
    "hall_length_m": 600.0,      # canon (05): along the hull
    "hall_depth_m": 200.0,       # canon (05): inward from the hull wall
    "hall_height_m": 30.0,       # canon, Jordan 21 Nov (5 civic storeys of 6 m)
    "hall_entrance_m": 30.0,     # settled (Jordan): doorway from the Hall into the Port of Arrivals
    "hall_entrance_height_m": 20.0,  # settled (Jordan)
    "hall_to_hangar_door_m": 20.0,   # settled (Jordan)
    "hall_to_hangar_door_height_m": 10.0,  # settled (Jordan; below the 15 m hangar roof)
    "hangar_length_m": 80.0,     # canon, Jordan 21 Nov: on the bow side of the Hall
    "hangar_depth_m": 60.0,      # canon, Jordan 21 Nov
    "hangar_height_m": 15.0,     # canon, Jordan 21 Nov
    "dock_door_length_m": 40.0,  # canon, Jordan 21 Nov: opening in the hull for the shuttle
    "dock_door_height_m": 10.0,  # canon, Jordan 21 Nov
    "wall_m": 2.0,               # graybox wall / roof thickness
    # Shuttle pad in the hangar (05 §2 canon look: burnt-orange markings, a ring of
    # orange guide lights round the pad). Sizes are settled (Jordan).
    "pad_m": 40.0,               # settled (Jordan): square pad for a ~30-40 m shuttle
    "stripe_m": 0.4,             # settled (Jordan): painted line width
    "cross_arm_m": 8.0,          # settled (Jordan): centre cross, each arm
    "hold_line_m": 0.6,          # settled (Jordan): hold line across the dock door
    "hold_line_inset_m": 2.0,    # settled (Jordan): hold line distance in from the hull face
    "guide_light_spacing_m": 4.0,  # 06 module grid (4 m)
    "guide_light_m": 0.3,        # settled (Jordan): flush floor light, square
    # Hall of Arrivals finish (05 section 2 canon look: polished dark stone, amber light
    # lines, bronze trims). Sizes are settled (Jordan).
    "hall_storey_m": 6.0,        # light line at every civic storey (06 section 3: civic storey 6 m)
    "light_line_m": 0.15,        # settled (Jordan): height of a light line
    "skirting_m": 0.3,           # settled (Jordan): bronze skirting along the walls
    "door_trim_m": 0.4,          # settled (Jordan): bronze frame round each doorway
    "guide_light_offset_m": 2.0,
    # Hangar structure (TUNE): steel roof trusses spanning the 60 m depth, columns,
    # a kick plate, the dock-door frame and high-bay lights.
    "truss_spacing_m": 8.0,      # two 06 modules
    "truss_depth_m": 2.0,        # top chord to bottom chord
    "truss_bay_m": 4.0,          # 06 module grid
    "chord_m": 0.35,
    "web_m": 0.2,
    "purlin_spacing_m": 4.0,
    "column_m": 0.6,
    "kick_plate_m": 1.2,
    "door_jamb_m": 1.5,          # hazard-striped jambs either side of the dock door
    "door_jamb_d_m": 0.8,
    "high_bays_per_truss": 3,
    "high_bay_m": 0.8,
    "high_bay_lux": 400.0,       # settled (Jordan): working hangar floor (06 interiors EV100 6-9)   # settled: outside the pad line (keeps the 4 m spacing exact)
}


def arrival_layout(geometry_dir, deck=5):
    """Ship-frame km extents of the hangar, Hall and the two hull cutouts."""
    a = ARRIVAL
    outline = read_outline(deck_csv_path(geometry_dir, deck, "net"))
    z0 = DECKS[deck][1] / 1000.0
    xc = frame_to_x_km(a["frame"])
    hall_x0 = xc - a["hall_length_m"] / 2000.0
    hall_x1 = xc + a["hall_length_m"] / 2000.0
    hangar_x1 = hall_x0
    hangar_x0 = hangar_x1 - a["hangar_length_m"] / 1000.0
    hw = min(half_width_at(outline, x) for x in (hangar_x0, hall_x1, (hangar_x0 + hall_x1) / 2))
    wall_y = -hw  # inner face of the port hull wall
    dock_c = (hangar_x0 + hangar_x1) / 2.0
    return {
        "z_floor": z0, "wall_y": wall_y, "hull_half_width": hw,
        "hall": (hall_x0, hall_x1, wall_y, wall_y + a["hall_depth_m"] / 1000.0, z0, z0 + a["hall_height_m"] / 1000.0),
        "hangar": (hangar_x0, hangar_x1, wall_y, wall_y + a["hangar_depth_m"] / 1000.0, z0, z0 + a["hangar_height_m"] / 1000.0),
        # (x0, x1, top_km): skyglass along the whole Hall, the shuttle door in the hangar
        "cutouts": [(hall_x0, hall_x1, z0 + a["hall_height_m"] / 1000.0),
                    (dock_c - a["dock_door_length_m"] / 2000.0, dock_c + a["dock_door_length_m"] / 2000.0,
                     z0 + a["dock_door_height_m"] / 1000.0)],
        "player_start": (dock_c, wall_y + a["hangar_depth_m"] / 2000.0, z0 + 0.002),
    }


def _room(name, x0, x1, y0, y1, z0, z1, t, doors, folder):
    """Walls (not the hull side) and roof of a box room. y0 is the hull side (open).

    doors: {"inner"|"bow"|"stern": (width_km, height_km, centre_km or None)}: a doorway
    from the floor up to height_km, centred at centre_km along that wall (None = middle).
    """
    out = []
    zc, h = (z0 + z1) / 2.0, z1 - z0
    out.append(box(name + "_Roof", ((x0 + x1) / 2, (y0 + y1) / 2, z1 + t / 2), (x1 - x0, y1 - y0, t), folder))

    def wall(tag, along_x, fixed, a0, a1, door):
        if not door:
            c = ((a0 + a1) / 2, fixed) if along_x else (fixed, (a0 + a1) / 2)
            s = (a1 - a0, t) if along_x else (t, a1 - a0)
            out.append(box(name + "_" + tag, (c[0], c[1], zc), (s[0], s[1], h), folder))
            return
        door, dz, centre = door
        mid = (a0 + a1) / 2 if centre is None else centre
        for k, (b0, b1) in enumerate(((a0, mid - door / 2), (mid + door / 2, a1))):
            c = ((b0 + b1) / 2, fixed) if along_x else (fixed, (b0 + b1) / 2)
            s = (b1 - b0, t) if along_x else (t, b1 - b0)
            out.append(box("%s_%s_%d" % (name, tag, k), (c[0], c[1], zc), (s[0], s[1], h), folder))
        c = (mid, fixed) if along_x else (fixed, mid)
        s = (door, t) if along_x else (t, door)
        out.append(box("%s_%s_Lintel" % (name, tag), (c[0], c[1], z0 + dz + (h - dz) / 2), (s[0], s[1], h - dz), folder))

    wall("Inner", True, y1 + t / 2, x0, x1, doors.get("inner"))
    wall("Bow", False, x0 - t / 2, y0, y1, doors.get("bow"))
    wall("Stern", False, x1 + t / 2, y0, y1, doors.get("stern"))
    return out


def arrival_pieces(geometry_dir, deck=5):
    """Graybox boxes for the arrival hangar, the Hall and its skyglass panel."""
    a = ARRIVAL
    L = arrival_layout(geometry_dir, deck)
    t = a["wall_m"] / 1000.0
    base = "D%d_%s" % (deck, DECKS[deck][0])
    folder = base + "/Arrival"
    hx0, hx1, hy0, hy1, hz0, hz1 = L["hall"]
    gx0, gx1, gy0, gy1, gz0, gz1 = L["hangar"]
    pieces = []
    pieces += _room(base + "_HallOfArrivals", hx0, hx1, hy0, hy1, hz0, hz1, t,
                    {"inner": (a["hall_entrance_m"] / 1000.0, a["hall_entrance_height_m"] / 1000.0, None),
                     # into the hangar: centred on the hangar's depth, not the Hall's
                     "bow": (a["hall_to_hangar_door_m"] / 1000.0, a["hall_to_hangar_door_height_m"] / 1000.0,
                             (gy0 + gy1) / 2)}, folder)
    # The hangar shares the Hall's bow wall, so it has no stern wall of its own.
    hangar = _room(base + "_ArrivalHangar", gx0, gx1, gy0, gy1, gz0, gz1, t, {}, folder)
    pieces += [p for p in hangar if not p["name"].endswith("_Stern")]
    zc = L["z_floor"] + (FLOOR_PROUD_M - FLOOR_PLATE_M / 2) / 1000.0
    for room, (x0, x1, y0, y1, _, _) in (("HallOfArrivals", L["hall"]), ("ArrivalHangar", L["hangar"])):
        pieces.append(box("%s_%s_Floor" % (base, room), ((x0 + x1) / 2, (y0 + y1) / 2, zc),
                          (x1 - x0, y1 - y0, FLOOR_PLATE_M / 1000.0), folder))
    # Skyglass: a thin panel in the hull opening along the Hall (glass material in Unreal).
    wt = 0.020  # hull wall thickness used by deck_graybox
    # Flush with the INNER face of the hull wall: the floor stops there, so a panel set
    # deeper into the 20 m-thick wall would leave a floorless gap to fall through.
    panel_y = L["wall_y"] - 0.00025
    pieces.append(box(base + "_Skyglass_HallOfArrivals", ((hx0 + hx1) / 2, panel_y, (hz0 + hz1) / 2),
                      (hx1 - hx0, 0.0005, hz1 - hz0), folder))
    # Dock field: an invisible barrier in the shuttle door so nobody walks out into space.
    # Graybox stand-in (TUNE) until the real door / atmosphere field is designed.
    dx0, dx1, dtop = L["cutouts"][1]
    pieces.append(box(base + "_DockField_ArrivalHangar", ((dx0 + dx1) / 2, panel_y, (L["z_floor"] + dtop) / 2),
                      (dx1 - dx0, 0.0005, dtop - L["z_floor"]), folder))
    pieces += skyglass_frame(L, base, folder)
    pieces += hangar_markings(L, base, folder)
    pieces += hall_finishes(L, base, folder)
    pieces += hangar_structure(L, base, folder)[0]
    return pieces


# Skyglass frame (canon look, Jordan 21 Nov 2026): tall panes in heavy gunmetal mullions
# with amber ribbons along the frame. Pane width: 3 modules of the 06 4 m grid.
# Floor plates: the hangar and the Hall get their own finished floor (worn deck plate,
# polished dark stone) laid on the deck slab, standing FLOOR_PROUD_M above it so the
# two surfaces never flicker. Thin enough that nobody trips on the edge.
FLOOR_PLATE_M = 0.02
FLOOR_PROUD_M = 0.002
SKYGLASS_PANE_M = 12.0
MULLION_W_M = 0.6      # TUNE: along the wall
MULLION_D_M = 0.8      # TUNE: standing out into the Hall
RIBBON_W_M = 0.15      # TUNE: amber strip on each mullion's face
RIBBON_D_M = 0.05


MARKING_M = 0.004   # paint and light pieces stand 2 mm proud of the floor plate


def hangar_markings(L, base, folder):
    """Burnt-orange pad outline, centre cross and dock-door hold line, plus the ring of
    orange guide lights round the pad (one every guide_light_spacing_m)."""
    a = ARRIVAL
    km = lambda m: m / 1000.0
    (cx, cy, _), z0 = L["player_start"], L["z_floor"]
    zc = z0 + km(FLOOR_PROUD_M + MARKING_M / 2)   # bottom sits on the plate top
    h, s, half = km(MARKING_M), km(a["stripe_m"]), km(a["pad_m"]) / 2
    out = []
    mk = lambda tag, c, size: out.append(box("%s_ArrivalHangar_Marking_%s" % (base, tag), (c[0], c[1], zc),
                                             (size[0], size[1], h), folder))
    for tag, dy in (("PadNear", -half + s / 2), ("PadFar", half - s / 2)):
        mk(tag, (cx, cy + dy), (2 * half, s))
    for tag, dx in (("PadBow", -half + s / 2), ("PadStern", half - s / 2)):
        mk(tag, (cx + dx, cy), (s, 2 * half - 2 * s))
    arm = km(a["cross_arm_m"])
    mk("CrossX", (cx, cy), (2 * arm, s))
    mk("CrossY", (cx, cy), (s, 2 * arm))
    hl = km(a["hold_line_m"])
    mk("HoldLine", (cx, L["wall_y"] + km(a["hold_line_inset_m"]) + hl / 2),
       (km(a["dock_door_length_m"]), hl))
    step, g = km(a["guide_light_spacing_m"]), km(a["guide_light_m"])
    r = half + km(a["guide_light_offset_m"])
    n = int(round(2 * r / step))
    k = 0
    for i in range(n):              # walk each side, corners included once
        t = -r + i * 2 * r / n
        for px, py in ((t, -r), (r, t), (-t, r), (-r, -t)):
            out.append(box("%s_ArrivalHangar_GuideLight_%03d" % (base, k), (cx + px, cy + py, zc), (g, g, h), folder))
            k += 1
    return out


TRIM_D_M = 0.04      # light lines and trims stand this far off the wall face


def _split(a0, a1, door, z_top):
    """Runs along a wall from a0 to a1, minus a doorway (lo, hi, top) where the run is below its top."""
    if door and z_top <= door[2] + 1e-12:
        return [(a0, door[0]), (door[1], a1)]
    return [(a0, a1)]


def hangar_structure(L, base, folder):
    """Roof trusses (chords, verticals, diagonals), purlins, wall columns, kick plate,
    the dock-door jambs and header, and high-bay light housings. Returns (pieces, lights)
    where lights are (x, y, z) km points just under each high-bay housing."""
    a = ARRIVAL
    km = lambda m: m / 1000.0
    gx0, gx1, gy0, gy1, z0, z1 = L["hangar"]
    t = km(a["wall_m"])
    gx1_face = gx1 - t                      # the Hall's bow wall closes the hangar's stern side
    out, lights = [], []
    nm = lambda tag: "%s_ArrivalHangar_%s" % (base, tag)
    ch, wb, bay, dep = km(a["chord_m"]), km(a["web_m"]), km(a["truss_bay_m"]), km(a["truss_depth_m"])
    z_top = z1 - ch / 2
    z_bot = z1 - dep - ch / 2
    span = gy1 - gy0
    nb = int(round(span / bay))
    n_tr = int(round((gx1_face - gx0) / km(a["truss_spacing_m"])))
    xs = [gx0 + (i + 0.5) * (gx1_face - gx0) / n_tr for i in range(n_tr)]
    door_c = L["player_start"][0]
    door_half = km(a["dock_door_length_m"]) / 2
    jamb = km(a["door_jamb_m"])
    for i, x in enumerate(xs):
        out.append(box(nm("Truss_%02d_Top" % i), (x, (gy0 + gy1) / 2, z_top), (ch, span, ch), folder))
        out.append(box(nm("Truss_%02d_Bottom" % i), (x, (gy0 + gy1) / 2, z_bot), (ch, span, ch), folder))
        for j in range(nb + 1):
            y = gy0 + j * span / nb
            out.append(box(nm("Truss_%02d_V%02d" % (i, j)), (x, y, (z_top + z_bot) / 2), (wb, wb, z_top - z_bot), folder))
        diag = math.hypot(bay, z_top - z_bot)
        ang = math.degrees(math.atan2(z_top - z_bot, bay))
        for j in range(nb):
            y = gy0 + (j + 0.5) * span / nb
            sign = 1 if j < nb / 2 else -1     # Pratt pattern, diagonals falling to mid-span
            out.append(box(nm("Truss_%02d_D%02d" % (i, j)), (x, y, (z_top + z_bot) / 2), (wb, diag, wb), folder,
                           roll_deg=sign * ang))
        # columns under both ends, except where the dock door opens in the hull wall
        hull_free = abs(x - door_c) > door_half + jamb + km(a["column_m"])
        for tag, y, ok in (("Hull", gy0 + km(a["column_m"]) / 2, hull_free), ("Inner", gy1 - km(a["column_m"]) / 2, True)):
            if ok:
                out.append(box(nm("Column_%s_%02d" % (tag, i)), (x, y, (z0 + z1) / 2),
                               (km(a["column_m"]), km(a["column_m"]), z1 - z0), folder))
        hb = km(a["high_bay_m"])
        n_hb = a["high_bays_per_truss"]
        for j in range(n_hb):
            y = gy0 + (j + 0.5) * span / n_hb
            zc = z_bot - ch / 2 - hb * 0.2
            out.append(box(nm("HighBay_%02d_%d" % (i, j)), (x, y, zc), (hb, hb, hb * 0.4), folder))
            out.append(box(nm("HighBayLens_%02d_%d" % (i, j)), (x, y, zc - hb * 0.2 - km(0.01)),
                           (hb * 0.85, hb * 0.85, km(0.02)), folder))
            lights.append((x, y, zc - hb * 0.2 - km(0.05)))
    n_p = int(round(span / km(a["purlin_spacing_m"])))
    for k in range(1, n_p):
        y = gy0 + k * span / n_p
        out.append(box(nm("Purlin_%02d" % k), ((gx0 + gx1_face) / 2, y, z1 - ch - km(0.15)),
                       (gx1_face - gx0, km(0.2), km(0.3)), folder))
    # Bow wall pilasters every truss bay
    for j in range(1, int(round(span / km(a["truss_spacing_m"])))):
        y = gy0 + j * km(a["truss_spacing_m"])
        out.append(box(nm("Column_Bow_%02d" % j), (gx0 + km(a["column_m"]) / 2, y, (z0 + z1) / 2),
                       (km(a["column_m"]), km(a["column_m"]), z1 - z0), folder))
    # Kick plate along the three solid walls (split at the Hall doorway on the stern side)
    kp, kd = km(a["kick_plate_m"]), km(0.05)
    yc, wd = (gy0 + gy1) / 2, km(a["hall_to_hangar_door_m"]) / 2
    for tag, c, s in (("Inner", ((gx0 + gx1_face) / 2, gy1 - kd / 2), (gx1_face - gx0, kd)),
                      ("Bow", (gx0 + kd / 2, (gy0 + gy1) / 2), (kd, span)),
                      ("Stern_0", (gx1_face - kd / 2, (gy0 + yc - wd) / 2), (kd, yc - wd - gy0)),
                      ("Stern_1", (gx1_face - kd / 2, (yc + wd + gy1) / 2), (kd, gy1 - yc - wd))):
        out.append(box(nm("Kick_%s" % tag), (c[0], c[1], z0 + kp / 2), (s[0], s[1], kp), folder))
    # Dock door: hazard-striped jambs, and a steel header girder from the door top to the roof
    dz = km(a["dock_door_height_m"])
    jd = km(a["door_jamb_d_m"])
    for tag, x in (("L", door_c - door_half - jamb / 2), ("R", door_c + door_half + jamb / 2)):
        out.append(box(nm("DoorJamb_%s" % tag), (x, gy0 + jd / 2, z0 + dz / 2), (jamb, jd, dz), folder))
    out.append(box(nm("DoorHeader"), (door_c, gy0 + jd / 2, (z0 + dz + z_bot - ch / 2) / 2),
                   (2 * (door_half + jamb), jd, z_bot - ch / 2 - z0 - dz), folder))
    # Door reveal: the hull is 20 m thick, and its bare cut faces sit outside the hangar in the
    # deck sun, so they glowed white (Jordan 21 Nov). Line both sides and the lintel underside
    # in dark steel, 1 cm proud of the cut faces.
    hull_t, lin = 0.020, km(0.01)
    for tag, x in (("L", door_c - door_half + lin / 2), ("R", door_c + door_half - lin / 2)):
        out.append(box(nm("DoorReveal_%s" % tag), (x, gy0 - hull_t / 2, z0 + dz / 2), (lin, hull_t, dz), folder))
    out.append(box(nm("DoorReveal_Top"), (door_c, gy0 - hull_t / 2, z0 + dz - lin / 2), (2 * door_half, hull_t, lin), folder))
    out.append(box(nm("DoorBand"), (door_c, gy0 + jd / 2, z0 + dz + km(0.4)), (2 * door_half, jd + km(0.02), km(0.8)), folder))
    return out, lights


def hall_finishes(L, base, folder):
    """Amber light lines at each storey and bronze trims (skirting, door frames) on the
    Hall's three built walls: Inner (the city side), Bow (onto the hangar) and Stern."""
    a = ARRIVAL
    km = lambda m: m / 1000.0
    hx0, hx1, hy0, hy1, hz0, hz1 = L["hall"]
    gy0, gy1 = L["hangar"][2:4]
    d = km(TRIM_D_M)
    y_start = hy0 + km(MULLION_D_M)            # clear of the skyglass mullions
    xc, w_in = (hx0 + hx1) / 2, km(a["hall_entrance_m"])
    yc, w_bow = (gy0 + gy1) / 2, km(a["hall_to_hangar_door_m"])
    walls = {   # name: (along x?, face coordinate, inward sign, run start, run end, doorway)
        "Inner": (True, hy1, -1, hx0, hx1, (xc - w_in / 2, xc + w_in / 2, hz0 + km(a["hall_entrance_height_m"]))),
        "Bow": (False, hx0, +1, y_start, hy1, (yc - w_bow / 2, yc + w_bow / 2, hz0 + km(a["hall_to_hangar_door_height_m"]))),
        "Stern": (False, hx1, -1, y_start, hy1, None),
    }
    out = []

    def strip(tag, along_x, face, sign, b0, b1, zc, h):
        f = face + sign * d / 2
        c = ((b0 + b1) / 2, f) if along_x else (f, (b0 + b1) / 2)
        s = (b1 - b0, d) if along_x else (d, b1 - b0)
        out.append(box("%s_HallOfArrivals_%s" % (base, tag), (c[0], c[1], zc), (s[0], s[1], h), folder))

    n_storeys = int(round((hz1 - hz0) * 1000.0 / a["hall_storey_m"]))
    lh, sk, dt = km(a["light_line_m"]), km(a["skirting_m"]), km(a["door_trim_m"])
    for wname, (ax, face, sign, a0, a1, door) in walls.items():
        for k in range(1, n_storeys):            # 6, 12, 18, 24 m: not the floor, not the roof
            z = hz0 + k * km(a["hall_storey_m"])
            for j, (b0, b1) in enumerate(_split(a0, a1, door, z + lh / 2)):
                strip("LightLine_%s_%02d_%d" % (wname, k, j), ax, face, sign, b0, b1, z, lh)
        for j, (b0, b1) in enumerate(_split(a0, a1, door, hz0 + sk)):
            strip("Trim_Skirting_%s_%d" % (wname, j), ax, face, sign, b0, b1, hz0 + sk / 2, sk)
        if door:
            lo, hi, top = door
            for tag, b in (("L", lo - dt / 2), ("R", hi + dt / 2)):
                strip("Trim_Door_%s_%s" % (wname, tag), ax, face, sign, b - dt / 2, b + dt / 2, (hz0 + top) / 2, top - hz0)
            strip("Trim_Door_%s_Head" % wname, ax, face, sign, lo - dt, hi + dt, top + dt / 2, dt)
    return out


def skyglass_frame(L, base, folder):
    """Mullions every SKYGLASS_PANE_M along the skyglass, an amber ribbon down each,
    and amber ribbons along the top and bottom of the whole wall."""
    hx0, hx1, _, _, hz0, hz1 = L["hall"]
    y_face = L["wall_y"]                        # mullions stand on the hull's inner face
    md, mw = MULLION_D_M / 1000.0, MULLION_W_M / 1000.0
    rw, rd = RIBBON_W_M / 1000.0, RIBBON_D_M / 1000.0
    n = int(round((hx1 - hx0) * 1000.0 / SKYGLASS_PANE_M))
    out = []
    for i in range(n + 1):
        x = hx0 + i * (hx1 - hx0) / n
        out.append(box("%s_Skyglass_Mullion_%03d" % (base, i), (x, y_face + md / 2, (hz0 + hz1) / 2),
                       (mw, md, hz1 - hz0), folder))
        out.append(box("%s_Skyglass_Ribbon_%03d" % (base, i), (x, y_face + md + rd / 2, (hz0 + hz1) / 2),
                       (rw, rd, hz1 - hz0), folder))
    for tag, z in (("Top", hz1 - rw / 2), ("Bottom", hz0 + rw / 2 + 0.0002)):
        out.append(box("%s_Skyglass_Ribbon_%s" % (base, tag), ((hx0 + hx1) / 2, y_face + md + rd / 2, z),
                       (hx1 - hx0, rd, rw), folder))
    return out
