"""Shared pieces for the Deck 5 room programs (tools/design_rooms.py).

A program is a dict:
  mode      "ring" (wings round the edge, big rooms in the middle), "hall" (one big hall cut into bays,
            with a support wing), "yard" or "park" (open zones with small buildings)
  floors    [(level name, storey height m, count or (lo, hi)[, "below"]), ...]
  rooms     one list of rows per floor group (same order as floors); see design_rooms.expand_rooms
  halls     [{"name", "about", "span": levels from the ground, "bays": {...}, "outdoor", "roof", "over", "inside"}]
  court     a hall used for any further middle pieces (gardens, light courts)
  wing      depth of the wing band (m); support: depth of a hall building's support wing
  zones     (yard, park) [(name, share, about, [small buildings], [fixtures]), ...]
  structure, look, entrances, capacity, services: text (or a list to vary), with {floors} {height} {area} {people}
The helpers below make the shared kinds (plants, shafts, fire stations, clinics, canteens, gardens) and take
the precinct's own details, so no two come out the same.
"""

WC = ("Toilets", 60, "Public toilets, with an accessible toilet and baby-changing room.")
WC_STAFF = ("Staff toilets and showers", 70, "Toilets, showers and changing space for the staff.")
CLEAN = ("Cleaners' room", 18, "Cleaning machines, supplies and a sink for the building's cleaning crew.")
COMMS = ("Comms room", 24, "Network switches and the building's data and radio links.")
PLANT = ("Plant room", 120, "Air handling units, pumps and electrical boards that keep this floor running.")
STORE = ("Store", 60, "Lockable store for furniture, spares and supplies.")
KITCHENETTE = ("Tea point", 20, "A small kitchen with a sink, fridge and drinks machine for staff on this floor.")
PRAYER = ("Quiet room", 30, "A small quiet room for prayer, rest or a private moment.")
FIRST_AID = ("First-aid room", 25, "A couch, first-aid kit and defibrillator for anyone taken ill.")
RECEPTION = ("Reception", 160, "The front desk where visitors sign in, get a pass and are met.")
MAIL = ("Post room", 40, "Where letters and parcels for the building are sorted and handed out.")
LOCKERS = ("Locker room", 90, "Lockers and changing benches for staff arriving for their shift.")
BREAK = ("Staff break room", 80, "A kitchen and tables where staff eat and take their breaks.")
SECURITY = ("Security desk", 40, "Guards watch the cameras and the doors from here.")

STAIRS_ABOUT = "Stairs, lifts and service risers serving every floor; also the protected escape route in a fire."


def R(name, m2, about, n=1):
    return (name, m2, about, n)


def F(name, m2, about):
    """The fill room of a floor: repeated to use whatever floor space is left."""
    return ("*" + name, m2, about)


# ------------------------------------------------------------------ kinds that repeat across precincts

def utility_plant(precinct, extra=None, cooling="chillers", style=0):
    """Power, air and water plant for one precinct. extra: rows for what is special about this one."""
    looks = [
        "A plain louvred box in graphite panels, with yellow service doors and a steam-white plume from its cooling stacks.",
        "A low ribbed shed with yellow-striped roller doors, a bank of grey transformers behind a mesh fence and pipe bridges running to the street.",
        "A windowless plant hall clad in dark corrugated metal, with a row of round air intakes along the top and a lit yellow plant number at each door.",
        "A two-storey block of perforated metal screens, lit from inside at night so the pumps and pipes show through.",
    ]
    return {
        "mode": "hall",
        "floors": [("Plant floor", 8.0, 1), ("Upper plant deck", 6.0, 1), ("Pipe and cable basement", 5.0, 1, "below")],
        "support": 18,
        "halls": [
            {"name": "Transformer and switch hall", "span": 2,
             "about": "The precinct's main substation: transformers step the ship's grid down and switchgear sends power out to every %s building." % precinct,
             "bays": {"name": "Transformer bay", "width": 22, "max": 8,
                      "about": "One transformer in a fire-walled bay, with its own oil catch pit and cooling fans."}},
            {"name": "%s hall" % ("Chiller" if cooling == "chillers" else "Heat exchanger"), "span": 2,
             "about": "Chillers and pumps that make the cold water used to cool the air in every %s building." % precinct},
            {"name": "Air handling hall", "span": 2,
             "about": "Big fans and filters that draw stale air from the precinct's ducts, clean it and send fresh air back."},
        ],
        "rooms": [
            [R("Control room", 120, "Plant operators watch power, air and water for the whole precinct on screens here, round the clock."),
             R("Switch room", 220, "Rows of switchgear that route power to each street and building, and cut it off when there is a fault."),
             R("Battery room", 160, "Banks of batteries that keep the precinct's lights and controls on for hours if the power fails."),
             R("Water pump room", 200, "Pumps that keep the precinct's fresh water at pressure and push waste water down to the service layer."),
             R("Water treatment room", 160, "Filters and UV lamps that clean recycled water before it goes back into the pipes."),
             R("Workshop", 140, "Benches and tools where the plant crew repair pumps, valves and fans.")] + (extra or []) +
            [LOCKERS, WC_STAFF, F("Spares store", 80, "Racked spare pumps, valves, filters and fuses, so repairs never wait for parts.")],
            [R("Filter bank room", 160, "Racks of air filters that catch dust, fibres and smells before the air goes back into the buildings."),
             R("Ductwork gallery", 200, "Where the main air ducts leave the plant and turn toward the streets."),
             R("Crew rest room", 40, "A small room with a kettle and chairs for the plant crew on long shifts."),
             F("Upper plant gallery", 120, "Walkways and platforms for reaching the tops of the fans, chillers and pipes.")],
            [R("Cable vault", 200, "Where the power cables come up from the service layer and are fanned out to the switchgear."),
             F("Pipe gallery", 200, "The main water, cooling and drain pipes, with valves crew can reach from catwalks.")],
        ],
        "structure": "Reinforced concrete plant hall with fire walls between transformer bays; steel roof trusses carrying a crane rail.",
        "look": looks[style % len(looks)],
        "entrances": "Wide roller doors for lifting gear on the street side; a crew door with a card reader beside the control room.",
        "capacity": "Power, cooling, air and water for every building in %s; a crew of about 12 on each shift." % precinct,
        "services": "Transformers, switchgear, chillers, air handling, water pumps and treatment, standby batteries; overhead crane.",
        "m2_per_person": 300,
    }


def service_shaft(precinct, style=0):
    looks = [
        "A squat concrete drum with a ring of yellow hazard lights round the lift doors and a steel gantry crane on its roof.",
        "A square tower of ribbed grey panels with a big goods lift door on each side and pipe ducts climbing its walls.",
        "A low hangar-like headhouse over the shaft, with a yellow-and-black striped lift gate and a loading bay for trucks.",
    ]
    return {
        "mode": "hall",
        "floors": [("Lift landing", 9.0, 1), ("Winding room", 6.0, 1), ("Service layer landing", 6.0, 1, "below")],
        "support": 14,
        "halls": [{"name": "Shaft and lift landing", "span": 2,
                   "about": "The top of the shaft that drops 197 ft (60 m) to the service layer: goods lifts, a crew lift and a stair land here.",
                   "inside": [{"name": "Goods lift cage", "about": "A lift big enough for a small truck, carrying deliveries and heavy plant up and down.",
                               "at": (0.15, 0.2, 0.3, 0.6)},
                              {"name": "Crew lift and stair", "about": "The lift and stair maintenance crews use to go down to the service layer.",
                               "at": (0.6, 0.3, 0.2, 0.4)}]}],
        "rooms": [
            [R("Lift control room", 50, "Operators run the goods lifts and watch the shaft cameras from here."),
             R("Loading bay", 300, "Trucks back in here to load and unload goods going to or from the service layer."),
             R("Crew check-in", 40, "Crews going down sign out, pick up radios and gas detectors and sign back in when they return."),
             R("Tool store", 80, "Tools, harnesses and lamps for work in the service layer."),
             WC_STAFF, F("Holding store", 120, "Short-term storage for goods waiting for the lift.")],
            [R("Winding machinery", 150, "The motors, brakes and cables that drive the shaft lifts."),
             R("Shaft ventilation fans", 120, "Fans that push fresh air down the shaft and the service tunnels."),
             F("Machine gallery", 80, "Walkways around the lift machinery for inspection.")],
            [R("Service layer landing", 400, "The foot of the shaft in the service layer, where tunnels lead off to the precinct's pipes, cables and plant."),
             F("Tunnel portal", 200, "Where the service tunnels meet the shaft.")],
        ],
        "structure": "Reinforced concrete shaft, 197 ft (60 m) deep to the service layer, with a steel headframe.",
        "look": looks[style % len(looks)],
        "entrances": "Truck door into the loading bay; crew door with card access.",
        "capacity": "Goods lift for loads up to 30 tons; crew lift for 20 people.",
        "services": "Goods and crew lifts, shaft ventilation, gas detection, emergency stair.",
        "m2_per_person": 400,
    }


def fire_station(precinct, special, engines, style=0):
    """special: (room rows unique to this station's risks)."""
    looks = [
        "A long low hall of red-framed glass bay doors under a dark crew block, with a slim drill tower lit red at the top.",
        "A graphite station with tall red roller doors, a lit red stripe along the crew floor and a training tower behind.",
        "An L of glass-fronted appliance bays and a crew wing in dark panels with red trim, around a drill yard.",
        "A compact red-and-graphite station whose bay doors fold up like wings, with the crew floor glazed above.",
    ]
    return {
        "mode": "hall",
        "floors": [("Appliance floor", 7.0, 1), ("Crew floor", 4.2, 1), ("Training floor", 4.2, 1)],
        "support": [22, 24, 26],
        "halls": [{"name": "Appliance hall", "span": 2,
                   "about": "Where the fire engines stand ready, nose to the doors, so crews can be rolling within a minute of a call.",
                   "bays": {"names": engines, "width": 16, "max": len(engines) * 2,
                            "about": "One appliance bay with a hose reel, charging lead and exhaust extractor over the engine."}},
                  {"name": "Drill yard", "outdoor": True, "about": "Open yard where crews practise ladders, hoses and rescues."}],
        "rooms": [
            [R("Watch room", 60, "The duty officer takes emergency calls here and sends crews out; the station's nerve centre."),
             R("Breathing apparatus room", 80, "Air cylinders are refilled and masks cleaned and tested after every call."),
             R("Decontamination room", 60, "Crews wash smoke and chemicals off themselves and their kit before going any further into the station."),
             R("Turnout gear room", 90, "Each firefighter's helmet, coat, boots and gloves hang ready by the engine doors.")] + list(special) +
            [R("Hose store", 70, "Spare hoses, branches and couplings, and a rack for drying wet hoses."), WC_STAFF,
             F("Equipment store", 60, "Rescue tools, ladders, cutting gear and spare kit.")],
            [R("Bunk rooms", 14, "A small bedroom for a firefighter on a night watch.", (10, 16)),
             R("Kitchen", 50, "The station kitchen, where the watch cooks its meals together."),
             R("Mess room", 90, "The crew's dining and sitting room, with a television and the call speaker."),
             R("Gym", 90, "Weights and rowing machines; firefighters must stay fit to carry kit up stairs."),
             R("Laundry", 30, "Washing machines for uniforms and bedding."),
             F("Crew room", 40, "Quiet rooms for reading, study and rest between calls.")],
            [R("Station commander's office", 30, "The station commander plans the watches and keeps the station's records."),
             R("Training room", 100, "Classroom for lessons on new equipment, first aid and fire safety."),
             R("Fire safety office", 40, "Inspectors who check buildings in %s for fire risks work from here." % precinct),
             R("Records room", 25, "Incident reports, inspection files and maintenance logs."),
             F("Offices", 30, "Offices for the station's officers and fire safety staff.")],
        ],
        "structure": "Steel portal-frame appliance hall, 23 ft (7 m) clear; concrete crew and training floors over the support wing.",
        "look": looks[style % len(looks)],
        "entrances": "Appliance doors straight onto the street; crew door from the drill yard; public door to the front office.",
        "capacity": "%d appliances; about %d crew on each watch." % (len(engines), len(engines) * 4),
        "services": "Hose and foam refill points, exhaust extraction, cylinder fill station, standby generator.",
        "m2_per_person": 60,
    }


def clinic(precinct, special, size="small", style=0):
    looks = [
        "A white clinic with a red edge to its roof and a lit red cross over a glass entrance.",
        "A low white building with deep window reveals, a covered ambulance bay and a red stripe at the eaves.",
        "A two-storey white clinic around a small healing garden, with frosted glass and red signs.",
    ]
    floors = [("Ground floor", 4.8, 1), ("Upper floor", 4.2, 1 if size == "small" else (2, 3))]
    return {
        "mode": "ring",
        "floors": floors,
        "wing": 26,
        "halls": [{"name": "Healing garden", "outdoor": True,
                   "about": "A planted courtyard where patients wait in quiet and recover in fresh air."}],
        "court": {"name": "Light court", "outdoor": True, "about": "A planted court that brings light into the middle of the clinic."},
        "rooms": [
            [R("Entrance and reception", 120, "Patients check in at the front desk and are directed to the right room."),
             R("Waiting area", 150, "Seats, water and a children's corner for patients waiting to be seen."),
             R("Triage room", 20, "A nurse checks each patient first and decides how urgently they need treatment.", 2),
             R("Treatment room", 25, "A room with a couch, lights and supplies for treating injuries and illnesses.", (3, 5)),
             R("Resuscitation bay", 40, "A fully equipped bay for patients in a life-threatening state."),
             R("Pharmacy", 60, "Medicines are dispensed to patients after their visit."),
             R("Ambulance bay", 80, "A covered bay where ambulances drop off and pick up patients.")] + list(special) +
            [WC, R("Clean utility", 20, "Sterile supplies and dressings ready for use."),
             R("Dirty utility", 15, "Where used equipment is cleaned and clinical waste is sealed for removal."),
             F("Consulting room", 18, "A doctor's room for appointments and check-ups.")],
            [R("Observation ward", 120, "A few beds where patients are watched for some hours before going home or to hospital."),
             R("Nurses' station", 30, "The nurses' desk, with views of the ward beds."),
             R("X-ray room", 40, "Takes X-ray images of broken bones and chests."),
             R("Staff room", 40, "Where clinic staff take their breaks."),
             R("Clinic manager's office", 20, "The clinic manager runs rotas, supplies and records from here."),
             WC_STAFF, F("Consulting room", 18, "A doctor's room for appointments and check-ups.")],
        ],
        "structure": "Concrete frame on a 26 ft (8 m) grid, with sealed, filtered air in the clinical rooms.",
        "look": looks[style % len(looks)],
        "entrances": "Walk-in entrance from the street; separate covered ambulance entrance.",
        "capacity": "About {people} patient visits a day at peak.",
        "services": "Medical gases, filtered air, standby power, clinical waste store.",
        "m2_per_person": 10,
    }


def canteen(who, special, style=0):
    looks = [
        "A glass-fronted dining hall with a deep canopy, warm light spilling out and a lit menu wall inside.",
        "A long low canteen in orange-trimmed dark panels, with big windows onto a terrace of tables.",
        "A two-storey food hall with a glazed dining floor upstairs and kitchen doors and delivery bay at the back.",
    ]
    return {
        "mode": "ring",
        "floors": [("Dining floor", 5.4, 1), ("Upper dining and staff floor", 4.2, (0, 1))],
        "wing": 22,
        "halls": [{"name": "Dining hall", "span": 1,
                   "about": "The main dining hall, with long tables, booths and a counter where %s collect their meals." % who}],
        "court": {"name": "Terrace court", "outdoor": True, "about": "An open court with tables for eating outside."},
        "hall_required": True,
        "min_hall": 300,
        "rooms": [
            [R("Serving counter", 120, "Hot meals, salads and drinks are served here in a fast-moving line."),
             R("Main kitchen", 300, "Cooks prepare thousands of meals a day here on big ranges, ovens and kettles."),
             R("Cold room", 60, "A walk-in fridge for fresh meat, vegetables and dairy."),
             R("Freezer room", 40, "A walk-in freezer for frozen stores."),
             R("Dry store", 80, "Shelves of flour, rice, tins and other dry food."),
             R("Dishwash room", 80, "Conveyor dishwashers clean trays, plates and cutlery."),
             R("Goods-in bay", 60, "Food deliveries arrive and are checked here."),
             R("Waste and recycling room", 30, "Food waste goes to the digester; packaging is sorted for recycling.")] + list(special) +
            [WC, F("Grab-and-go kiosk", 40, "Sandwiches, snacks and coffee for people in a hurry.")],
            [R("Upper dining room", 300, "A quieter dining room with tables for groups."),
             R("Kitchen staff changing room", 50, "Kitchen crews change into whites and wash before their shift."),
             R("Catering manager's office", 20, "Where menus are planned and food is ordered."),
             WC_STAFF, F("Meeting and dining room", 50, "A small room that can be booked for working lunches.")],
        ],
        "structure": "Concrete frame with a long-span steel roof over the dining hall.",
        "look": looks[style % len(looks)],
        "entrances": "Main doors from the street into the dining hall; goods door at the back for deliveries.",
        "capacity": "About {people} seats.",
        "services": "Kitchen extraction, grease traps, cold rooms, food-waste line to the digester.",
        "m2_per_person": 2.0,
    }


def garden(kind, focus, style=0, pavilion=True):
    """kind: plain words for the garden; focus: zone rows special to this garden (name, share, about)."""
    pav = [{"size": (24, 12), "rooms": [("Kiosk", 1, "Sells drinks, ice cream and snacks."),
                                       ("Toilets", 1, "Public toilets for garden visitors."),
                                       ("Gardeners' store", 1, "Tools and mowers for the garden crew.")]}] if pavilion else []
    zones = [("Lawn", 3, "Open grass for sitting, picnics and games.", pav)] + list(focus) + [
        ("?Tree grove", 2, "Shady trees with benches underneath."),
        ("Paths and benches", 1, "Paved paths with benches and lamps that lead through the %s." % kind),
    ]
    return {
        "mode": "park",
        "floors": [("Ground", 4.0, 1)],
        "zones": zones,
        "shuffle_zones": True,
        "height_extra": 8.0,
        "floors_text": "Open ground; one small pavilion" if pavilion else "Open ground",
        "edge": ("Planted edge", "Low shrubs and flower beds along the edge of the %s." % kind),
        "structure": "Soil beds 3 ft (1 m) deep over the deck, with drainage and irrigation pipes underneath.",
        "look": "A %s of lawns and trees under the deck's daylight panels, with lamp posts along the paths." % kind,
        "entrances": "Open on every side from the surrounding streets.",
        "capacity": "Open to everyone; about {people} people at busy times.",
        "services": "Irrigation, path lighting, drinking fountains, waste bins.",
        "m2_per_person": 40,
    }
