"""Map colour legend (approved by Jordan, 27 Nov 2026): what a building is used for, by colour.

Each building stores a "category" (one of the keys below). When a building has none, the app
works one out from its name and kind with the word lists here, so a new building is never left
uncoloured. Colours are used by the 2D maps and the 3D view alike.
"""

import re

# key, label on the legend, fill, edge, label text colour
CATEGORIES = [
    ("transit", "Roads and transit", "#4a4f57", "#9aa3ad", "#e8f1fb"),
    ("keelway", "The Keelway", "#8fd3ff", "#cfefff", "#0b2140"),
    ("police", "Police and security", "#2f6fd6", "#9cc0ff", "#ffffff"),
    ("fire", "Fire and emergency", "#d23b3b", "#ffb0b0", "#ffffff"),
    ("medical", "Medical", "#f4f4f2", "#d23b3b", "#7a1010"),
    ("homes", "Homes", "#d2b48c", "#f3e2c8", "#3a2a14"),
    ("shops", "Shops and food", "#f08c2e", "#ffd2a6", "#3a1e04"),
    ("offices", "Offices and government", "#8a5cc7", "#d6c2f2", "#ffffff"),
    ("industry", "Industry, hangars and docks", "#7d8a96", "#c9d2da", "#0b1622"),
    ("utilities", "Utilities and services", "#e6c93a", "#fff1a8", "#3a3004"),
    ("parks", "Parks and plazas", "#3f9a55", "#a8e0b6", "#ffffff"),
    ("schools", "Schools and training", "#2aa8a0", "#a6ece6", "#ffffff"),
]
KEYS = [c[0] for c in CATEGORIES]

_R = lambda *w: re.compile(r"\b(" + "|".join(w) + r")", re.I)
TRANSPORT_YARDS = _R("depot", "yard", "apron", r"park\b", "tug", "truck", "siding", "cruiser gate", "gates", "berth",
                     "marina", "locks", "taxiway")
HOME_NOTES = _R("apartment", "row houses", "family homes", "homes round", "rooms for trainee", "flats", "lofts for", "houses for")
# Checked in this order; the first list with a word in the building's name wins.
RULES = [
    ("police", _R("police", "guard", "security", "marshal", r"brig\b", "jail", "patrol", "customs", "checkpoint", "sentry", "provost")),
    ("fire", _R("fire", "emergency", "rescue", "crash tender", "damage control")),
    ("medical", _R("clinic", "hospital", "medical", "health", "infirmary", "first aid", "pharmacy", "surgery", "sick bay",
                   "quarantine", "medic")),
    ("utilities", _R("utility", "utilities", "substation", r"power\b", r"water\b", "water and air", "recycl", "waste", "pump",
                     "reactor", "laundry", "service shaft", "antenna", "sensor", "air plant", "life support", "fuel",
                     "propellant", "catapult plant", "radio", "data centre", "communications", "lockers")),
    ("shops", _R("canteen", r"mess\b", "mess hall", "caf", "restaurant", "dining", "commissary", "theatre", "cinema", "arcade")),
    ("schools", _R("school", "academy", "college", "training", "simulator", "cadet", "universit", "classroom", "nursery",
                   "kindergarten", "childcare", "centrifuge", "briefing", "licensing", "exam", "library", "lecture",
                   "instruction", "museum")),
    ("parks", _R("garden", r"park\b", "lawn", r"green\b", "plaza", "square", "promenade", "overlook", "field", "sports",
                 "fitness", "forecourt", "memorial")),
    ("industry", _R("rack hall", "repair", "airframe", "engine", "turret", "weapons", "canopy", "maintenance", "avionics", "coatings", "paint",
                    r"wash\b", "armorers' hall", "armoury", "shield", "corvette service", "fuel cell")),
    ("shops", _R("shops", "market")),
    ("recreation", _R("sports", "fitness", "recreation")),
    ("homes", _R("home", "house", "apartment", r"flat\b", "flats", "residen", "barracks", r"quarters\b", "dormitor", r"dorm\b",
                 "bunkhouse", "lodg", "hostel", "hotel", r"inn\b", "suites", "housing", "cottage", "village", r"terraces?\b",
                 r"villas?\b", "lofts", "towers")),
    ("offices", _R(r"offices?\b", "admin", "control")),
    ("shops", _R("lounge", "help desk", "club", "pavilion")),
    ("transit", _R("terminal", "baggage", "gangway", "passenger", "crew gate", "transfer", "interchange", r"station\b",
                   r"stop\b", "deck lift", r"lifts\b", "lift to", "lift hall")),
    ("shops", _R("shop", "market", "food", r"bar\b", r"pub\b", "mall", "bazaar", "kiosk", "galley", "bakery", "retail",
                 "lounge", "club", "pavilion", "help desk", "chandlery")),
    ("offices", _R(r"offices?\b", "records", "council", "governor", "government", "admin", "headquarters", r"hq\b", "command",
                   "operations", r"ops\b", "control", "registry", "archive", "guild", "bank", "chief", "bureau", "dispatch",
                   "tower", "beacon", "hall of", "staff", "planning", "crews' hall", "intelligence", "logistics", "desk",
                   "ready", "rest hall", "investigation", "inspectors", "harbourmaster", "rosters", "forwarders", "liaison",
                   "visitor", "analysts", "debrief", "town hall", r"courts?\b", r"hall\b")),
    ("industry", _R("hangar", "bay", "dock", "berth", "quay", "yard", "apron", "shed", "works", "workshop", "depot",
                    "warehouse", "store", "stacks", "freight", "cargo", "crane", "magazine", "bunker", "ordnance",
                    "range", "foundry", "factory", "fabricat", "repair", "launch", "shaft", "gate", "rack", "refit",
                    "berm", "tug", "truck", "slip", "cradle", "test", "parts", "module", "fleet", "munition", r"pit\b",
                    "salvage", r"lab\b", "locks", "siding", "taxiway", "rebuild", "service")),
    ("transit", _R("walk", "keelway", "cross-line", "road", "tram", r"pod\b", "transit", "taxi", "platform", "concourse",
                   "boulevard", "bridge", "canal", "street", "lanes", "rank", "boat")),
]
KIND_DEFAULT = {"park": "parks", "plaza": "parks", "utility": "utilities", "yard": "industry", "bays": "industry",
                "hangar": "industry", "transport": "transit"}


def categorize(b):
    """The legend category for a building dict (its stored one, or one worked out from name, notes and kind)."""
    c = b.get("category")
    if c in KEYS:
        return c
    name = b.get("name") or ""
    kind = b.get("kind") or "building"
    if kind in ("park", "plaza"):
        return "parks"
    if kind == "transport":
        return "industry" if TRANSPORT_YARDS.search(name) else "transit"
    if kind == "building" and HOME_NOTES.search(b.get("notes") or "") and not re.search(r"shop|market", name, re.I):
        return "homes"
    for key, rx in RULES:
        if key == "parks" and kind in ("building", "transport"):
            continue   # a building named "Garden Apartments" is homes, a "Tug Park" is a vehicle yard
        if rx.search(name):
            return "parks" if key == "recreation" else key
    return KIND_DEFAULT.get(kind, "offices")


def legend():
    return [{"key": k, "label": l, "fill": f, "edge": e, "text": t} for k, l, f, e, t in CATEGORIES]
