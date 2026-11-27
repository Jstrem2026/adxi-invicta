"""Room programs for the Port of Arrivals lots that had no plan yet (written 27 Nov 2026). See tools/design_rooms.py.

The rest of the Port of Arrivals was planned earlier with tools/build_designs.py; its "What it does" sentences are
in port_of_arrivals_about.py. This file covers the Hall of Arrivals and arrival hangar (canon sizes and heights kept),
the shuttle gates, the P8 hangar rows and depot, the open berths and marina, and the parks and squares.
"""
from .common import (R, F, WC, WC_STAFF, CLEAN, COMMS, PLANT, KITCHENETTE, PRAYER, FIRST_AID, LOCKERS, BREAK,
                     SECURITY, garden)

PORT_STYLE = "Port of Arrivals style: graphite and gunmetal metal cladding, white exterior light lines."
SHED_LOOK = "Gunmetal sheds with full-width bay doors and a light strip over each door. " + PORT_STYLE

# ------------------------------------------------------------------ P2 Hall of Arrivals (canon 600 x 200 x 30 m)

HALL_OF_ARRIVALS = {
    "mode": "hall",
    "floors": [("Arrivals floor", 6.0, 1), ("Gallery floor", 6.0, 4)],   # 30 m (canon); amber lines every 6 m storey
    "support": 40,
    "support_edge": "far_y",   # the great hall keeps the Skyglass wall on the hull side; offices on the entrance side
    "room_depth": 11.0,
    "halls": [{"name": "Great Hall", "span": "all",
               "about": "The great hall itself, 98 ft (30 m) high and open to the roof, lit through the Skyglass wall that "
                        "looks out on Haven's Reach. Every arriving passenger walks through it.",
               "inside": [
                   {"name": "Skyglass wall", "at": (0.0, 0.0, 1.0, 0.03),
                    "about": "The 1,969 ft (600 m) glass wall onto space, 98 ft (30 m) tall, with mullions every 39 ft (12 m) (canon look)."},
                   {"name": "In-processing circle", "at": (0.42, 0.35, 0.16, 0.3),
                    "about": "The welcome point at the heart of the hall where new arrivals are in-processed and meet Avalon, Sentinel and Vector (canon)."},
                   {"name": "Seating island (bow)", "at": (0.12, 0.4, 0.14, 0.22),
                    "about": "Benches and planters where travellers sit, get their bearings and wait for friends."},
                   {"name": "Seating island (stern)", "at": (0.74, 0.4, 0.14, 0.22),
                    "about": "Benches and planters where travellers sit, get their bearings and wait for friends."},
                   {"name": "Arrivals boards", "at": (0.05, 0.86, 0.9, 0.04),
                    "about": "Screens listing every arriving shuttle, its gate and where its passengers go next."},
                   {"name": "Door to the arrival hangar", "at": (0.0, 0.08, 0.015, 0.13),
                    "about": "The 66 × 33 ft (20 × 10 m) door through to the arrival hangar (placeholder size, TUNE)."},
                   {"name": "Gate Concourse entry", "at": (0.985, 0.08, 0.015, 0.13),
                    "about": "Where passengers walk in from the Gate Concourse and the sixteen shuttle gates."},
               ]}],
    "rooms": [
        [R("Main entrance hall", 900, "Inside the 98 ft (30 m) wide main entrance (placeholder size), where people leave for the Arrivals Forecourt."),
         R("Information desk", 120, "Staff answer questions and hand out ship maps in every language."),
         R("Greeters' office", 150, "Base for the greeters who welcome each shuttle load of new arrivals."),
         R("Guides' room", 120, "Guides wait here to walk newcomers to customs, the terminals or the Keelway."),
         R("Porters' station", 200, "Porters and their luggage trolleys, ready to carry bags for arrivals."),
         R("Arrivals clerks' office", 200, "Clerks log every arrival and issue first passes and papers."),
         R("Customs officers' post", 180, "Customs officers watch the hall and send travellers on to customs and health screening."),
         R("Assisted travel desk", 80, "Help for travellers who need a wheelchair, a guide or extra time."),
         R("Lost and found", 80, "Things left in the hall are handed in and claimed here."),
         R("Family room", 100, "A quiet room with changing tables and play space for families after a long flight."),
         SECURITY, FIRST_AID, WC, WC, LOCKERS, CLEAN,
         F("Waiting lounge", 200, "Seats along the hall for people waiting for a connection or a friend."),
         F("Kiosk", 40, "Coffee, water and snacks for new arrivals.")],
        [R("Gallery café", 400, "A café on the gallery with views down into the great hall and out through the Skyglass wall."),
         R("Viewing gallery", 600, "An open gallery where visitors watch the hall and the shuttles outside."),
         R("Hall control room", 150, "Staff run the hall's lights, screens, doors and crowd flow."),
         R("Arrivals management office", 200, "The managers who run the Hall of Arrivals day to day."),
         R("Customs supervisors' office", 120, "Senior customs officers who oversee the hall's posts."),
         R("Translation service", 80, "Interpreters who help arrivals who don't speak the ship's languages."),
         KITCHENETTE, WC_STAFF, PLANT, COMMS, PRAYER,
         F("Staff office", 40, "Desks for the hall's greeters, guides and clerks."),
         F("Meeting room", 40, "A room for staff meetings and private talks with travellers.")],
    ],
    "structure": "Long-span roof trusses every 26 ft (8 m) over the great hall; concrete gallery floors in the office wing.",
    "look": "A vast hall of polished dark stone with amber light lines every 20 ft (6 m) storey and bronze trim, its whole hull "
            "side a 1,969 ft (600 m) Skyglass wall onto space (canon look).",
    "entrances": "Main entrance 98 ft (30 m) wide onto the Arrivals Forecourt (placeholder size); door to the arrival hangar; "
                 "Gate Concourse entry at the stern end.",
    "capacity": "About {people} people at a time at its busiest.",
    "services": "Arrivals boards, public address, Skyglass shutters, crowd sensors.",
    "m2_per_person": 6,
}

ARRIVAL_HANGAR = {
    "mode": "hall",
    "floors": [("Hangar floor", 5.0, 1), ("Upper floor", 5.0, 2)],   # 15 m (canon)
    "support": 16,
    "support_edge": "far_y",
    "halls": [{"name": "Arrival hangar bay", "span": "all",
               "about": "One covered bay where an arriving shuttle comes in through the hull dock door, lands on the pad and is unloaded under cover.",
               "inside": [
                   {"name": "Shuttle pad", "at": (0.25, 0.07, 0.5, 0.9),
                    "about": "The 131 ft (40 m) square landing pad (TUNE) with its touchdown lights."},
                   {"name": "Dock door", "at": (0.25, 0.0, 0.5, 0.05),
                    "about": "The 131 × 33 ft (40 × 10 m) door in the hull that the shuttle flies in through (canon)."},
                   {"name": "Door to the Hall", "at": (0.97, 0.1, 0.03, 0.45),
                    "about": "The 66 ft (20 m) wide door into the Hall of Arrivals (placeholder size, TUNE)."},
               ]}],
    "rooms": [
        [R("Unloading office", 40, "The crew chief plans each unload and signs for the cargo."),
         R("Baggage transfer room", 80, "Bags come off the shuttle and are loaded onto carts for the Hall."),
         R("Ground crew room", 60, "The hangar's ground crew wait here between arrivals."),
         R("Tool room", 40, "Tools and spares for turning the shuttle round."), WC_STAFF],
        [R("Hangar control room", 50, "Opens and closes the dock door and guides the shuttle onto the pad."),
         R("Crew rest room", 50, "Shuttle crews rest here while their craft is turned round."), PLANT, KITCHENETTE],
    ],
    "structure": "Steel portal frame with a 131 ft (40 m) dock door set in the hull wall.",
    "look": "A gunmetal hangar against the hull beside the Hall, with an orange-lit dock door and a marked pad inside. " + PORT_STYLE,
    "entrances": "Dock door in the hull for the shuttle; door into the Hall of Arrivals.",
    "capacity": "One shuttle at a time.",
    "services": "Ground power, fuel point, baggage carts.",
    "m2_per_person": 150,
}

# ------------------------------------------------------------------ rows of bays (gates, hangars, berths)

def bay_row(label, bay, about, gap_name, gap_about, n=None, pitch=None, covered=True, fixtures=(), huts=(), first=1):
    """Zones for a row of equal bays along the lot. n: bays in the whole lot; or pitch: one bay every pitch metres
    (for a lot in several pieces). Numbers carry on from piece to piece."""
    def zones(ctx):
        L = ctx["ring_len"]
        if pitch:
            k = max(1, int((L + pitch - bay) // pitch))
            gap = pitch - bay
            end = (L - k * bay - (k - 1) * gap) / 2
        else:
            k = n
            gap = (L - k * bay) / (k - 1) if k > 1 else 0
            end = 0
        z = []
        if end > 1:
            z.append(("Row end", end, "Open ground at the end of the row, kept clear for walkways and fire access."))
        for i in range(k):
            no = ctx.get(label, first - 1) + 1
            ctx[label] = no
            z.append((label % no if "%" in label else "%s %d" % (label, no), bay, about, list(huts), list(fixtures),
                      {"covered": covered}))
            if i < k - 1 and gap > 1:
                z.append((gap_name, gap, gap_about))
        if end > 1:
            z.append(("Row end", end, "Open ground at the end of the row, kept clear for walkways and fire access."))
        return z
    return zones


def row_program(zones, h, look, structure, entrances, capacity, services, floors_text, m2pp=400):
    return {"mode": "yard", "floors": [("Bay floor", h, 1)], "height_extra": 0.0, "zones": zones,
            "floors_text": floors_text, "structure": structure, "look": look, "entrances": entrances,
            "capacity": capacity, "services": services, "m2_per_person": m2pp}


SHED_FIX = [("Craft door", "The full-width door the craft rolls in and out through.", (0.0, 0.94, 1.0, 0.06)),
            ("Tool room", "A small tool room at the back of the bay.", (0.0, 0.0, 0.2, 0.18)),
            ("Staff door", "The staff door at the back of the bay.", (0.45, 0.0, 0.1, 0.05))]

SHUTTLE_GATES = row_program(
    bay_row("Gate G%d", 80, "A covered gate where one passenger shuttle docks; its passengers step off and walk to the Hall of Arrivals.",
            "Gate gap", "A 66 ft (20 m) gap between two gate sheds, kept clear for walkways, fire access and service cables.",
            pitch=100, fixtures=SHED_FIX),
    15.0, SHED_LOOK,
    "Steel portal frame per bay, one full-width door to the apron (matches the canon Arrival hangar, 80 × 60 × 15 m).",
    "One full-width craft door per bay on the apron side; a staff door at the back.",
    "Sixteen shuttles at a time.", "Ground power, fuel and air at each gate.", "1 (single high bay each)", m2pp=600)

HANGAR_ROW = lambda row, n: row_program(
    bay_row("Bay %s%%d" % row, 40, "A public hangar bay for one small craft, rented by the day or the month.",
            "Bay wall", "The fire wall between two hangar bays.", n=n, fixtures=SHED_FIX),
    10.0, SHED_LOOK, "Steel portal frame per bay, one full-width door to the apron.",
    "One full-width craft door per bay on the apron side; a staff door at the back.",
    "%d small craft, one to a bay." % n, "Power and data in every bay.", "1 (single high bay each)")

SHUTTLE_DEPOT = row_program(
    bay_row("Depot bay %d", 80, "A covered bay where one of the port's own passenger shuttles is kept, cleaned and readied between flights.",
            "Bay wall", "The fire wall between two depot bays.", n=16, fixtures=SHED_FIX),
    15.0, SHED_LOOK, "Steel portal frame per bay, one full-width door to the apron (same size as the arrival gates).",
    "One full-width craft door per bay on the apron side; a staff door at the back.",
    "16 passenger shuttles.", "Ground power, fuel, water and cleaning points in every bay.", "1 (single high bay each)", m2pp=600)

BERTH_FIX = [("Mooring arms", "Arms that grip the ship's hull and hold it steady at the berth.", (0.02, 0.15, 0.06, 0.7)),
             ("Mooring arms (far side)", "Arms on the other side of the ship.", (0.92, 0.15, 0.06, 0.7)),
             ("Shore connection post", "Where shore power, water, air and data plug into the ship.", (0.4, 0.88, 0.2, 0.1))]


def berths(label, bay, n, what, h_extra=0.0):
    return {"mode": "yard", "floors": [("Berth floor", 4.0, 1)], "height_extra": h_extra,
            "zones": bay_row(label, bay, "An open berth for one %s, with mooring arms and shore connections." % what,
                             "Berth walkway", "A railed walkway between two berths, used by line handlers and inspectors.",
                             n=n, covered=False, fixtures=BERTH_FIX),
            "floors_text": "Open berths (no roof)", "structure": "Reinforced deck with mooring-arm foundations; fuel, power and water lines in trenches.",
            "look": "A row of open floodlit berths along the hull, striped at the edges, each with yellow mooring arms.",
            "entrances": "From space through the dock doors in the hull; service roads behind.",
            "capacity": "%d %ss." % (n, what), "services": "Shore power, water, air and data at every berth.", "m2_per_person": 4000}


def skiff_marina():
    slips = [("Slip %d" % (i + 1), "A 131 ft (40 m) square slip for one skiff or private craft.",
              (i * 50 / 1240, 0.0, 40 / 1240, 1.0)) for i in range(25)]
    office = [{"size": (30, 12), "rooms": [("Marina office", 2, "Books slips and welcomes visiting skiffs."),
                                           ("Skiff fuel point", 1, "Fuel for small craft.")]}]
    return {"mode": "yard", "floors": [("Marina floor", 4.0, 1)], "height_extra": 0.0, "split": "across",
            "zones": [("Skiff slips", 40, "The row of 25 slips where skiffs and private craft tie up.", [], slips),
                      ("Taxi lane", 40, "The lane skiffs taxi along between the slips and the dock doors."),
                      ("Skiff apron", 160, "Open apron where skiffs wait, are washed and are serviced."),
                      ("Marina walk", 60, "A walkway along the marina, with the marina office and fuel point.", office)],
            "floors_text": "Open marina; one small office", "structure": "Reinforced deck with tie-down points.",
            "look": "A floodlit marina of small craft in neat numbered slips, with a little lit office at the back.",
            "entrances": "From space through the bow dock doors; walkway from the street.",
            "capacity": "25 skiffs.", "services": "Power and water at every slip; a fuel point.", "m2_per_person": 4000}

# ------------------------------------------------------------------ squares and parks

def plaza(focus, look, pav):
    return {"mode": "park", "floors": [("Ground", 4.0, 1)], "height_extra": 6.0, "shuffle_zones": True,
            "zones": [("Paved square", 3, "Open paving where people cross, meet and gather.", pav)] + list(focus) + [
                ("Tree-lined edge", 1, "A row of trees and benches along the edge of the square.")],
            "floors_text": "Open ground; one small kiosk", "edge": ("Kerb and bollards", "A low kerb and bollards that keep vehicles out of the square."),
            "structure": "Paving over the deck with drainage and power for lights and screens underneath.",
            "look": look, "entrances": "Open on every side.", "capacity": "Open to everyone; about {people} people at busy times.",
            "services": "Lighting, wayfinding screens, drinking fountains, waste bins.", "m2_per_person": 10}


KIOSK = [{"size": (20, 10), "rooms": [("Kiosk", 1, "Sells coffee, drinks and snacks."), ("Toilets", 1, "Public toilets.")]}]

ARRIVALS_FORECOURT = plaza(
    [("Meeting point", 1, "Where travellers coming out of the Hall's main doors meet friends and family.", [],
      [("Welcome map", "A big lit map of the ship for people just off their shuttle.", (0.3, 0.3, 0.4, 0.2))]),
     ("Pod waiting area", 1, "Benches and shelters beside the pickup lanes for people waiting for a pod or taxi.")],
    "A wide square of pale paving in front of the Hall's main doors, with a lit ship map and rows of young trees.", KIOSK)
TERMINAL_PLAZA = plaza(
    [("Wayfinding court", 1, "Signs and screens pointing to every terminal, the Keelway and the concourse."),
     ("Fountain court", 1, "A fountain with seating round it, a landmark meeting place between connections.")],
    "A busy square between the terminals, with a round fountain and tall lit signposts.", KIOSK)
KEELWAY_SQUARE = plaza(
    [("Station steps", 1, "Wide steps and ramps up to the Keelway Port Station entrance."),
     ("Event lawn", 1, "Grass for markets, music and gatherings in the square."),
     ("Bike and scooter racks", 1, "Racks and charging points for bikes and scooters.")],
    "A large square in front of the station, with broad steps, a lawn in the middle and lights strung between the trees.", KIOSK)

MARINA_PARK = garden("park beside the bow docks", [
    ("Dock view lawn", 2, "A lawn looking out over the bow docks and the ships coming in."),
    ("Outdoor gym", 1, "Exercise bars and machines for dock workers on their breaks.")])
DOCK_PARK = garden("park beside the stern docks", [
    ("Picnic lawn", 2, "Picnic tables on the grass for crews and dock workers."),
    ("Ball court", 1, "A hard court for football and basketball after shifts.")])
PROMENADE_PARK = garden("park through the concourse", [
    ("Promenade", 2, "A wide tree-lined walk through the park for travellers stretching their legs between flights."),
    ("Children's playground", 1, "Swings, slides and climbing frames for children waiting to travel."),
    ("Water garden", 1, "Shallow pools and fountains with stepping stones.")])
ATRIUM_EDGE_PARK = garden("long park at the edge of the Atrium Plaza", [
    ("Buffer woodland", 3, "Dense trees that screen the shuttle yards' noise and lights from the Atrium Plaza."),
    ("Yard workers' lawn", 1, "A lawn where shuttle yard crews take their breaks."),
    ("Plaza walk", 1, "A path linking the shuttle yards to the Atrium Plaza.")])
FORECOURT_GARDENS = garden("forecourt garden", [
    ("Welcome lawn", 2, "A lawn where travellers sit after their flight and wait for friends."),
    ("Flower borders", 1, "Long beds of flowers along the boulevard.")])

PROGRAMS = [
    (r"^Hall of Arrivals$", HALL_OF_ARRIVALS),
    (r"^Arrival hangar$", ARRIVAL_HANGAR),
    (r"^Shuttle gates", SHUTTLE_GATES),
    (r"^Hangar Row A$", HANGAR_ROW("A", 31)),
    (r"^Hangar Row B$", HANGAR_ROW("B", 62)),
    (r"^Shuttle Depot$", SHUTTLE_DEPOT),
    (r"^Medium Berths$", berths("Medium berth", 120, 15, "medium-sized civilian or private ship")),
    (r"^Corvette Berths$", berths("Corvette berth", 160, 8, "corvette")),
    (r"^Frigate Berths$", berths("Frigate berth", 400, 5, "frigate")),
    (r"^Skiff Marina$", skiff_marina()),
    (r"^Arrivals Forecourt$", ARRIVALS_FORECOURT),
    (r"^Terminal Plaza$", TERMINAL_PLAZA),
    (r"^Keelway Square$", KEELWAY_SQUARE),
    (r"^Marina Park$", MARINA_PARK),
    (r"^Dock Park$", DOCK_PARK),
    (r"^Promenade Park$", PROMENADE_PARK),
    (r"^Atrium Edge Park$", ATRIUM_EDGE_PARK),
    (r"^Bow Garden / Stern Garden$", FORECOURT_GARDENS),
]
