"""Room programs for Flight Control (Deck 5 Aerion), written 27 Nov 2026. See tools/design_rooms.py."""
from .common import (R, F, WC, WC_STAFF, CLEAN, COMMS, PLANT, KITCHENETTE, PRAYER, FIRST_AID, RECEPTION,
                     LOCKERS, BREAK, SECURITY, utility_plant, service_shaft, fire_station, canteen, garden)

LIGHT_COURT = {"name": "Light court", "outdoor": True,
               "about": "An open court in the middle of the block that brings light and air to the inner rooms."}
SITUATION_WALL = "A curved wall of screens showing every craft in the sector, its height, speed and track."


def approach_control(side, what, extra):
    return {
        "mode": "ring",
        "floors": [("Equipment floor", 5.0, 1), ("Control floor", 7.0, 1), ("Support floor", 4.2, (1, 2))],
        "wing": 26,
        "hall_required": True,
        "halls": [{"name": "%s approach control room" % side, "span": 2,
                   "about": "Rows of controller desks facing a wall of traffic screens. Controllers here talk to every pilot %s "
                            "and give each one a path, a height and a slot to land." % what,
                   "inside": [{"name": "Situation wall", "about": SITUATION_WALL, "at": (0.05, 0.05, 0.9, 0.08)},
                              {"name": "Supervisor's platform", "about": "A raised desk where the shift supervisor watches every controller and steps in when traffic gets heavy.",
                               "at": (0.4, 0.7, 0.2, 0.15)}]}],
        "rooms": [
            [R("Equipment room", 300, "Racks of radar processors, radio sets and computers that feed the control room."),
             R("Uninterruptible power room", 160, "Batteries that keep every screen and radio running for an hour if the power fails."),
             R("Engineers' workshop", 120, "Technicians test and repair radios and screens here, around the clock."),
             R("Entrance and security", 80, "Staff badge in; visitors are signed in and escorted."), LOCKERS, WC_STAFF] + extra[0] +
            [F("Equipment room", 200, "More racks of radar, radio and data equipment.")],
            [R("Flow management desk", 80, "Plans how many craft can arrive each hour and holds the rest in queues out in space."),
             R("Watch manager's office", 30, "The watch manager runs the shift and handles emergencies."),
             R("Quiet room", 25, "A dark room where a controller can step away for a few minutes after a hard session.", 2),
             KITCHENETTE] + extra[1] + [F("Assistants' room", 40, "Flight data assistants who prepare flight strips and update the plans.")],
            [R("Briefing room", 60, "Controllers are briefed on weather, closures and special flights before each watch."),
             R("Training simulator room", 120, "A copy of the control desks where controllers practise rare emergencies."),
             R("Rest lounge", 80, "Chairs, a kitchen and a view of the deck for controllers on break."),
             R("Records and tapes room", 40, "Every radio call and radar picture is recorded and kept here."),
             WC_STAFF, F("Offices", 30, "Offices for planners, managers and the safety officer.")],
        ],
        "structure": "Concrete frame with a long-span steel roof over the control room; raised floors for cables; blast-resistant glazing.",
        "look": "A long low control block in dark graphite with a band of blue-lit screens visible through tall tinted windows, "
                "and radio masts along its roof.",
        "entrances": "Staff entrance with security gate; equipment door at the back.",
        "capacity": "About 40 controller desks; {people} staff over three watches.",
        "services": "Duplicate power feeds, battery back-up, dual data links to the Traffic Control Centre and the Beacon.",
        "m2_per_person": 25,
    }


def sensor_hall(side):
    return {
        "mode": "hall",
        "floors": [("Array floor", 12.0, 1), ("Gallery floor", 5.0, 1)],
        "support": [22, 26],
        "halls": [{"name": "Sensor array hall", "span": 2,
                   "about": "Tall racks of radar transmitters, receivers and processors, linked by cable trays to the antennas on the hull above the %s approaches." % side,
                   "bays": {"name": "Radar bay", "width": 36, "max": 10,
                            "about": "One radar set: its transmitter, receiver and cooling, behind a screened wall."}},
                  {"name": "Cooling plant hall", "span": 1, "share": 0.35,
                   "about": "Chillers and pumps that carry heat away from the radar electronics."}],
        "rooms": [
            [R("Sensor control room", 120, "Engineers watch the health of every radar and sensor and switch to spares when one fails."),
             R("Calibration lab", 100, "Test equipment that checks each radar reads distance and speed exactly."),
             R("Waveguide workshop", 80, "Where the metal ducts that carry radar signals are made and repaired."),
             R("Spares cage", 120, "Spare transmitters, processors and boards, ready to swap in."), LOCKERS, WC_STAFF,
             F("Electronics bench room", 60, "Benches where technicians repair circuit boards.")],
            [R("Engineers' office", 60, "The engineering team plans maintenance and upgrades."),
             R("Data room", 80, "Merges the radar pictures and sends them to the control rooms."),
             KITCHENETTE, F("Inspection gallery", 60, "A walkway over the radar bays for checking equipment.")],
        ],
        "structure": "Steel portal-frame hall with screened walls to stop radio leaks; concrete support wing.",
        "look": "A tall windowless hall in ribbed dark metal, crowned with radomes and cable masts, with yellow service doors.",
        "entrances": "Equipment doors big enough for a truck; staff door by the control room.",
        "capacity": "Radar and sensor coverage of the %s approaches; a crew of about 20 per shift." % side,
        "services": "Radio-screened walls, chilled water, duplicate power.",
        "m2_per_person": 200,
    }


def controllers_lodge(side):
    return {
        "mode": "ring",
        "floors": [("Lounge floor", 4.5, 1), ("Rest floor", 3.4, (2, 3))],
        "wing": 22,
        "court": {"name": "Quiet garden", "outdoor": True, "about": "A walled garden where controllers unwind in silence between shifts."},
        "rooms": [
            [R("Lounge", 200, "Sofas, books and soft light; no screens, so controllers' eyes can rest."),
             R("Dining room", 150, "Hot meals at any hour for controllers coming off shift."),
             R("Kitchen", 100, "Cooks for the dining room around the clock."),
             R("Gym", 120, "Exercise bikes and weights to shake off a long shift."),
             R("Front desk", 40, "Books rest rooms and wakes controllers in time for their next shift."),
             WC, F("Reading room", 50, "A silent room with armchairs and lamps.")],
            [R("Rest room", 14, "A small, dark, soundproof bedroom where a controller sleeps between shifts.", (16, 30)),
             R("Shower room", 25, "Showers and changing space.", 2),
             R("Linen room", 15, "Clean sheets and towels."),
             F("Rest room", 14, "A small, dark, soundproof bedroom where a controller sleeps between shifts.")],
        ],
        "structure": "Concrete frame with heavy sound insulation between rooms.",
        "look": "A quiet %s lodge in warm tan panels with small deep windows and a walled garden." % side,
        "entrances": "Front door from the street, a short walk from the control room.",
        "capacity": "About {people} rest rooms.",
        "services": "Blackout blinds, wake-up call system, quiet ventilation.",
        "m2_per_person": 30,
    }


ANTENNA_FIELD = {
    "mode": "yard",
    "floors": [("Field", 4.0, 1)],
    "height_extra": 36.0,
    "zones": lambda ctx: _antenna_zones(ctx),
    "edge": ("Security fence line", "A fenced strip around the field; the antennas are sensitive and dangerous to stand near."),
    "floors_text": "Open field; one small equipment hut",
    "structure": "Antenna masts on concrete pads, with buried cable trenches and earthing grids.",
    "look": ["A fenced field of slim white masts and lattice towers, with red lights at their tips.",
             "Rows of grey dish antennas and wire aerials on a gravel field, linked by cable trays.",
             "A field of tall masts and squat radomes, lit by low blue lamps along the cable paths."],
    "entrances": "A locked gate for engineers; a track for the mast crane.",
    "capacity": "Unmanned; engineers visit for checks.",
    "services": "Power and data cables to the sensor halls; lightning earthing.",
    "m2_per_person": 5000,
}


def _antenna_zones(ctx):
    rng = ctx["rng"]
    hut = [{"size": (14, 8), "rooms": [("Equipment hut", 2, "Receivers, power units and fibre links for the antennas in this field."),
                                       ("Engineers' shelter", 1, "Shelter with a desk and kit for engineers working in the field.")]}]
    pool = [("Mast row", 3, "Tall masts carrying traffic-radio aerials that talk to craft on approach."),
            ("Dish array", 3, "Steerable dishes that track craft far out on the approach paths."),
            ("Direction-finding ring", 2, "A ring of small aerials that tells controllers which direction a radio call came from."),
            ("Beacon antennas", 2, "Transmit the homing signals craft steer by on their way in."),
            ("Weather sensors", 1, "Sensors that measure radiation and debris near the hull."),
            ("Spare mast pads", 1, "Concrete pads with cables ready for new antennas.")]
    rng.shuffle(pool)
    return [(pool[0][0], pool[0][1], pool[0][2], hut)] + pool[1:rng.randint(3, 5)] + [("Cable path", 1, "Gravel path over the cable trench, used by engineers and the mast crane.")]


def briefing_annex(ctx):
    rng = ctx["rng"]
    extra = rng.sample([
        R("Map table room", 80, "A big screen table where crews walk through their route before flying."),
        R("Weather briefing room", 60, "Forecasters brief crews on radiation, debris and storms along their route."),
        R("Squadron office", 40, "A desk for squadron staff booking rooms and printing briefing packs."),
        R("Video link room", 50, "Crews are briefed live by the Traffic Control Centre or the cruisers."),
        R("Crew lounge", 80, "Crews wait here between briefing and boarding."),
        R("Print room", 30, "Prints briefing packs and charts."),
    ], 3)
    return [R("Lobby and room board", 80, "A lobby with a screen showing which crew is briefed in which room."), WC] + extra + [
        F("Briefing room", 60, "A room with a screen, a map wall and seats for one crew or a small squadron."),
         F("Route planning room", 40, "A crew plots its route on a big table screen and checks fuel and timings."),
         F("Crew ready room", 50, "Crews wait here in flight kit after their briefing, until they are called to board.")]


BRIEFING_ANNEX = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Briefing floor", 4.2, (1, 3))],
    "wing": 24,
    "rooms": [briefing_annex, [R("Debrief room", 40, "Crews go over a finished flight and what went wrong or right.", (2, 4)), KITCHENETTE, WC,
                               F("Briefing room", 60, "A room with a screen, a map wall and seats for one crew or a small squadron."),
         F("Route planning room", 40, "A crew plots its route on a big table screen and checks fuel and timings."),
         F("Crew ready room", 50, "Crews wait here in flight kit after their briefing, until they are called to board.")]],
    "structure": "Concrete frame on a 26 ft (8 m) grid.",
    "look": ["A plain teal-trimmed block of briefing rooms with a lit room board in its glass lobby.",
             "A long three-storey annex in grey panels with a teal stripe and rows of small windows.",
             "A compact annex with a glazed stair tower and teal-framed windows."],
    "entrances": "Lobby entrance from the street.",
    "capacity": "About {people} crew being briefed at once.",
    "services": "Screens and briefing network in every room.",
    "m2_per_person": 6,
}


def dispatch_annex(ctx):
    rng = ctx["rng"]
    extra = rng.sample([
        R("Slot desk", 60, "Hands out departure slots when the main Dispatch Centre is busy."),
        R("Crew roster desk", 60, "Finds crews to fill flights at short notice."),
        R("Charter desk", 50, "Books one-off flights for companies and visitors."),
        R("Cargo flight desk", 60, "Plans freight flights to the cruisers and the docks."),
        R("Delay desk", 50, "Re-plans flights held up by weather, faults or traffic."),
    ], 3)
    return [R("Entrance", 60, "Staff entrance and reception."), WC] + extra + [F("Dispatch room", 120, "Rows of dispatch desks with screens showing flights, crews and slots."),
         F("Team office", 50, "A dispatch team's own office, where they plan the next day's flights."),
         F("Call desk room", 60, "Dispatchers phone crews and craft operators about changes to their flights.")]


DISPATCH_ANNEX = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Dispatch floor", 4.2, (1, 3))],
    "wing": 24,
    "rooms": [dispatch_annex, [R("Meeting room", 40, "Small meeting room.", 2), KITCHENETTE, WC_STAFF,
                               F("Dispatch room", 120, "Rows of dispatch desks with screens showing flights, crews and slots."),
         F("Team office", 50, "A dispatch team's own office, where they plan the next day's flights."),
         F("Call desk room", 60, "Dispatchers phone crews and craft operators about changes to their flights.")]],
    "structure": "Concrete frame with raised floors for cables.",
    "look": ["A plain purple-trimmed office block, its windows lit by rows of screens.",
             "A grey annex with a glass stair and a lit flight board in the lobby.",
             "A narrow block in dark panels with purple light lines at each floor."],
    "entrances": "Staff entrance from the street.",
    "capacity": "About {people} desks.",
    "services": "Raised floors, data links to the Dispatch Centre.",
    "m2_per_person": 10,
}

THE_BEACON = {
    "mode": "ring",
    "floors": [("Base hall", 8.0, 1), ("Equipment floor", 5.0, 3), ("Tower shaft floor", 5.0, 6), ("Visual control cab", 7.0, 1)],
    "wing": 30,
    "halls": [{"name": "Beacon Hall", "span": 1,
               "about": "The tower's entrance hall, with a model of Deck 5 showing every flight live; visitors can watch from the gallery."}],
    "rooms": [
        [R("Security lobby", 100, "Everyone entering the tower is checked here."),
         R("Visitors' gallery", 200, "Visitors watch the flight deck on big screens and learn how traffic control works."),
         R("Lift lobby", 80, "Express lifts to the control cab at the top."), WC,
         F("Tower offices", 60, "Offices for the tower's managers.")],
        [R("Radio equipment room", 200, "Radios that talk to every craft on the flight deck."),
         R("Battery room", 120, "Keeps the tower running if the power fails."),
         R("Cooling plant", 120, "Cools the equipment floors."),
         F("Equipment room", 150, "Racks of radio, radar and data equipment.")],
        [R("Rest room", 30, "Rest rooms for tower controllers.", 2), KITCHENETTE,
         F("Equipment room", 150, "Racks of radio, radar and data equipment.")],
        [R("Visual control cab", 300, "The glass room at the top of the Beacon. Controllers look straight out over the flight deck and clear craft to launch and land."),
         R("Tower supervisor's desk", 40, "The supervisor's raised desk in the cab."),
         F("Cab gallery", 60, "The walkway round the cab glass.")],
    ],
    "height_extra": 20.0,
    "structure": "A reinforced concrete core rising through every floor, with a steel and glass control cab on top.",
    "look": "Aerion's landmark: the tallest block in Flight Control, eleven storeys of dark glass ribs, its top floor a band of lit blue glass "
            "where the controllers sit looking out over the deck; a red beacon light pulses on the roof.",
    "entrances": "Public entrance to the Beacon Hall from Beacon Plaza; staff entrance with security; equipment door at the back.",
    "capacity": "About 30 controllers in the cab; the hall takes 400 visitors.",
    "services": "Duplicate power and data, express lifts, beacon light, lightning protection.",
    "m2_per_person": 40,
}

TRAFFIC_CONTROL = {
    "mode": "ring",
    "floors": [("Equipment floor", 5.0, 1), ("Master traffic floor", 9.0, 1), ("Operations floor", 4.4, 2), ("Plant floor", 5.0, 1)],
    "wing": 30,
    "halls": [{"name": "Master traffic room", "span": 3,
               "about": "The deck's master traffic room: tiers of controller desks facing a two-storey wall of screens. Every craft on Deck 5 "
                        "is followed here from launch to landing.",
               "inside": [{"name": "Main screen wall", "about": SITUATION_WALL, "at": (0.05, 0.05, 0.9, 0.06)},
                          {"name": "Duty director's gallery", "about": "A glass gallery where the duty director oversees the whole room.",
                           "at": (0.35, 0.78, 0.3, 0.12)}]},
              {"name": "Training mirror room", "span": 2, "share": 0.3,
               "about": "A full copy of the master room, used for training and as a spare if the main room must be cleared."}],
    "rooms": [
        [R("Computer hall", 600, "The flight data computers that track every craft and every flight plan."),
         R("Power room", 300, "Duplicate supplies and batteries that keep the centre running through any fault."),
         R("Engineering control", 150, "Engineers who keep the computers, radios and screens working."),
         R("Security entrance", 120, "Staff pass two checks; the centre is a secure building."), LOCKERS, WC_STAFF,
         F("Equipment room", 200, "More computer and radio racks.")],
        [R("Sector desks", 400, "Controllers each handling one slice of the deck's airspace."),
         R("Supervisors' room", 80, "Shift supervisors plan staffing and breaks."),
         R("Quiet room", 25, "Controllers rest their eyes for a few minutes.", 3), WC_STAFF,
         F("Flight data room", 100, "Assistants who keep flight plans and strips up to date.")],
        [R("Director's office", 60, "The director of traffic control."),
         R("Planning office", 200, "Plans new routes, procedures and changes to the deck's airspace."),
         R("Incident room", 100, "Used to manage a major incident alongside the Rescue Coordination Centre."),
         R("Staff restaurant", 300, "Meals for controllers at any hour."), KITCHENETTE, WC_STAFF,
         F("Offices", 40, "Offices for managers, planners and the safety team."),
         F("Procedures office", 60, "Writes the rules and procedures every controller follows."),
         F("Rostering office", 50, "Plans controllers' watches so nobody works too long.")],
        [PLANT, F("Plant room", 300, "Air handling and chillers for the centre.")],
    ],
    "structure": "Hardened concrete frame; the master room spans 98 ft (30 m) on steel trusses; raised floors throughout.",
    "look": "A broad, low, hardened block of dark concrete with a single long window of blue light across its front, "
            "and a forest of aerials on the roof.",
    "entrances": "One secure staff entrance; equipment door at the back.",
    "capacity": "About 120 controller desks; {people} staff over three watches.",
    "services": "Three independent power feeds, battery and generator back-up, duplicate data links.",
    "m2_per_person": 25,
}

BACKUP_CONTROL = {
    "mode": "ring",
    "floors": [("Standby control floor", 6.0, 1), ("Bunker level", 4.5, 1, "below")],
    "wing": 24,
    "hall_required": True,
    "halls": [{"name": "Standby control room", "span": 1,
               "about": "A smaller copy of the master traffic room, kept switched on and staffed, ready to take over within a minute if the Traffic Control Centre fails."}],
    "rooms": [
        [R("Blast door lobby", 60, "A double blast door; the building is hardened against explosions."),
         R("Standby crew room", 80, "The standby crew wait here, ready to take the desks."),
         R("Equipment room", 200, "Its own computers and radios, separate from the main centre."),
         R("Generator room", 150, "Its own generators and fuel, so it runs even if the deck's power fails."),
         WC_STAFF, F("Rest room", 20, "Bunks for a crew that may have to stay for days.")],
        [R("Air filter room", 100, "Filters that keep the air clean if the deck outside is filled with smoke."),
         R("Water tank room", 80, "Water for a week."),
         R("Food store", 60, "Food for the crew for a week."),
         F("Bunk room", 20, "Bunks for the standby crew.")],
    ],
    "structure": "Hardened reinforced concrete with blast doors and its own air supply.",
    "look": "A squat, windowless concrete block with rounded edges, a single blast door and a ring of short aerials.",
    "entrances": "One blast door with an air lock.",
    "capacity": "20 controller desks; a crew of 30 can live inside for a week.",
    "services": "Own generators, air filters, water and food stores.",
    "m2_per_person": 40,
}

BEACON_PLAZA = {
    "mode": "park",
    "floors": [("Ground", 4.0, 1)],
    "height_extra": 10.0,
    "zones": [
        ("Plaza", 3, "The paved square at the foot of the Beacon, the open heart of Flight Control, where staff and visitors cross.",
         [{"size": (16, 10), "rooms": [("Coffee kiosk", 1, "Coffee for controllers going on shift."), ("Information point", 1, "Maps and visitor tours of the Beacon.")]}],
         [("Compass rose", "A huge compass set in the paving, pointing to the bow, the stern, port and starboard.", (0.4, 0.4, 0.2, 0.2))]),
        ("Tree avenue", 2, "Two rows of trees leading to the Beacon's doors."),
        ("Fountain court", 1, "A low fountain whose jets rise and fall with the deck's traffic."),
        ("Pod stop kerb", 1, "Kerb where pods drop off controllers and visitors."),
    ],
    "edge": ("Planted edge", "Low planting along the plaza edge."),
    "floors_text": "Open square; a kiosk",
    "structure": "Stone paving over the deck, with planters and a fountain basin.",
    "look": "A wide stone square with a compass rose set in the paving and an avenue of trees leading to the Beacon.",
    "entrances": "Open on all sides.",
    "capacity": "About {people} people at shift change.",
    "services": "Lighting, fountain pumps, drinking fountains.",
    "m2_per_person": 5,
}

REST_HALL = {
    "mode": "ring",
    "floors": [("Lounge floor", 4.5, 1), ("Rest floor", 3.4, 2)],
    "wing": 22,
    "court": {"name": "Rest garden", "outdoor": True, "about": "A sheltered garden where controllers sit under daylight panels between shifts."},
    "rooms": [
        [R("Silent lounge", 250, "Reclining chairs in dim light; talking is not allowed."),
         R("Café", 120, "Light meals and drinks."), R("Massage room", 20, "Massage for tired necks and shoulders.", 3),
         R("Front desk", 30, "Books nap rooms and wakes controllers on time."), WC,
         F("Lounge", 80, "Sofas and soft light.")],
        [R("Nap room", 12, "A tiny, dark, soundproof room for a 20-minute nap between sessions.", (20, 40)), R("Showers", 30, "Showers."),
         F("Nap room", 12, "A tiny, dark, soundproof room for a 20-minute nap between sessions.")],
    ],
    "structure": "Concrete frame with heavy sound insulation.",
    "look": "A low, quiet building in muted purple panels with deep-set windows onto a garden.",
    "entrances": "Front door from the Beacon precinct.",
    "capacity": "About {people} nap rooms and lounge seats.",
    "services": "Quiet ventilation, blackout blinds.",
    "m2_per_person": 15,
}

DISPATCH_CENTRE = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Dispatch floor", 6.0, 2), ("Office floor", 4.2, 1)],
    "wing": 28,
    "halls": [{"name": "Dispatch hall", "span": 3,
               "about": "A great open hall of dispatch desks. Dispatchers here match every flight with a craft, a crew and a time slot, "
                        "and watch the boards for delays.",
               "inside": [{"name": "Departures board", "about": "A giant board listing every flight of the day, its craft, crew and slot.",
                           "at": (0.05, 0.05, 0.9, 0.06)}]}],
    "rooms": [
        [R("Entrance hall", 200, "Staff entrance with a live departures board."), R("Crew desk", 80, "Crews collect their flight papers here."),
         R("Craft desk", 80, "Matches craft to flights and tracks which are in repair."), LOCKERS, WC_STAFF,
         F("Dispatch office", 100, "Desks for dispatchers who handle one kind of flight each."),
         F("Crew scheduling office", 80, "Draws up crew rosters weeks ahead, balancing rest and training."),
         F("Craft availability office", 80, "Tracks which craft are ready, in repair or due for checks.")],
        [R("Shift lead's desk", 40, "The shift lead balances work between the dispatch teams."),
         R("Slot planning room", 120, "Plans departure slots for the next day."), KITCHENETTE, WC_STAFF,
         F("Dispatch office", 100, "Desks for dispatchers who handle one kind of flight each."),
         F("Crew scheduling office", 80, "Draws up crew rosters weeks ahead, balancing rest and training."),
         F("Craft availability office", 80, "Tracks which craft are ready, in repair or due for checks.")],
        [R("Head of dispatch's office", 50, "Runs the Dispatch precinct."), R("Data team room", 120, "Keeps the flight and crew databases correct."),
         R("Training room", 100, "New dispatchers are trained here."), R("Staff restaurant", 250, "Meals for dispatch staff."),
         WC_STAFF, F("Offices", 40, "Offices for managers and planners.")],
    ],
    "structure": "Concrete frame with a long-span roof over the dispatch hall; raised floors.",
    "look": "A big four-storey block in dark panels with purple light lines, and a glass front showing the lit departures board inside.",
    "entrances": "Main staff entrance from the street; crew desk entrance at the side.",
    "capacity": "About 300 dispatch desks; {people} staff over the day.",
    "services": "Raised floors, duplicate power and data.",
    "m2_per_person": 12,
}

SHUTTLE_SCHEDULES = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Office floor", 4.2, 3)],
    "wing": 24,
    "rooms": [
        [R("Public timetable desk", 80, "Anyone can ask about shuttle times and services here."),
         R("Printing and signs room", 80, "Prints timetables and sends updates to every departure board on the ship."),
         R("Reception", 50, "Visitors and operators sign in."), WC, F("Timetable office", 100, "Planners who draw up shuttle timetables."),
         F("Passenger feedback room", 40, "Reads complaints and ideas from shuttle passengers.")],
        [R("Operators' liaison room", 60, "Meets the shuttle companies to agree services."),
         R("Modelling room", 100, "Computer models test new timetables before they go live."), KITCHENETTE, WC_STAFF,
         F("Timetable office", 100, "Planners who draw up shuttle timetables."),
         F("Passenger feedback room", 40, "Reads complaints and ideas from shuttle passengers.")],
    ],
    "structure": "Concrete frame.",
    "look": "A slim office block with a lit timetable board running up its glass stair tower.",
    "entrances": "Public entrance for the timetable desk; staff entrance at the side.",
    "capacity": "About {people} staff.",
    "services": "Links to every departure board on the ship.",
    "m2_per_person": 12,
}

CRUISER_LIAISON = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Office floor", 4.2, 2)],
    "wing": 22,
    "rooms": [
        [R("Secure entrance", 60, "Visitors from the cruisers are checked and escorted."),
         R("Liaison room", 120, "Officers from Flight Control and the escort cruisers sit side by side and agree movements."),
         R("Secure communications room", 60, "Encrypted links to each escort cruiser's bridge."), WC,
         F("Liaison office", 40, "Desks for cruiser officers on attachment."),
         F("Secure planning room", 40, "A screened room where cruiser movements are planned in secret.")],
        [R("Conference room", 80, "Planning meetings for big movements, such as a cruiser coming in to dock."),
         R("Duty officer's office", 30, "The duty officer on call for cruiser movements."), KITCHENETTE, WC_STAFF,
         F("Liaison office", 40, "Desks for cruiser officers on attachment."),
         F("Secure planning room", 40, "A screened room where cruiser movements are planned in secret.")],
    ],
    "structure": "Concrete frame with screened, secure rooms.",
    "look": "A small dark block with the escort fleet's emblem over a guarded door and narrow lit windows.",
    "entrances": "One guarded entrance.",
    "capacity": "About {people} staff, half of them cruiser officers.",
    "services": "Encrypted links, secure document store.",
    "m2_per_person": 15,
}

ANALYSTS = {
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Office floor", 4.2, 3)],
    "wing": 24,
    "halls": [{"name": "Data wall room", "span": 1, "about": "A room with a wall of charts showing traffic, delays and near-misses, updated live."}],
    "rooms": [
        [R("Reception", 50, "Staff and visitors sign in."), R("Incident replay room", 80, "Analysts replay radar and radio recordings of incidents step by step."),
         WC, F("Analysts' office", 80, "Analysts who study traffic data to make flying safer and smoother."),
         F("Delay study room", 50, "A team that traces why flights ran late and how to stop it."),
         F("Safety report desk", 40, "Reads every safety report sent in by pilots and controllers.")],
        [R("Statistics room", 100, "Produces the monthly safety and delay figures for the whole deck."),
         R("Meeting room", 40, "Meeting room.", 2), KITCHENETTE, WC_STAFF, F("Analysts' office", 80, "Analysts who study traffic data to make flying safer and smoother."),
         F("Delay study room", 50, "A team that traces why flights ran late and how to stop it."),
         F("Safety report desk", 40, "Reads every safety report sent in by pilots and controllers.")],
    ],
    "structure": "Concrete frame.",
    "look": "A grey office block with long strip windows and a glowing chart wall visible on the ground floor.",
    "entrances": "Entrance from the street.",
    "capacity": "About {people} analysts.",
    "services": "Data links to the traffic recordings.",
    "m2_per_person": 12,
}

CONTROLLER_TRAINING = {
    "mode": "ring",
    "floors": [("Simulator floor", 6.0, 1), ("Classroom floor", 4.2, 2)],
    "wing": 26,
    "halls": [{"name": "Tower simulator", "span": 2,
               "about": "A round room with a 360-degree screen that recreates the view from the Beacon's cab, so trainees practise clearing craft to launch and land."},
              {"name": "Radar simulator hall", "span": 1, "share": 0.8,
               "about": "Rows of radar desks where trainees control simulated traffic while instructors play the pilots."}],
    "rooms": [
        [R("Entrance and reception", 80, "Trainees and visitors sign in."), R("Pseudo-pilot room", 120, "Instructors pretend to be pilots, talking to trainees by radio."),
         R("Simulator equipment room", 150, "Computers that run the simulators."), WC, F("Debrief room", 30, "Instructor and trainee go over a session.")],
        [R("Lecture theatre", 200, "Lessons on rules, radar and radio for whole classes."), R("Library", 120, "Manuals, charts and study desks."),
         KITCHENETTE, WC, F("Classroom", 60, "A classroom for 20 trainees."),
         F("Study room", 30, "Trainees revise rules and charts in small groups."),
         F("Instructors' office", 40, "Instructors plan lessons and mark tests.")],
    ],
    "structure": "Concrete frame; the tower simulator has a domed screen.",
    "look": "A teal-trimmed training centre with a white domed roof over the tower simulator.",
    "entrances": "Main entrance from the street.",
    "capacity": "About 200 trainees.",
    "services": "Simulator computers and screens.",
    "m2_per_person": 15,
}

RADIO_HUB = {
    "mode": "hall",
    "floors": [("Radio hall floor", 8.0, 1), ("Upper floor", 4.5, 1)],
    "support": 24,
    "halls": [{"name": "Radio equipment hall", "span": 2,
               "about": "Rows of radio transmitters, receivers and data switches carrying every flight radio call and data link on the ship.",
               "bays": {"name": "Radio rack row", "width": 30, "max": 10, "about": "A row of radio racks with its own cooling."}}],
    "rooms": [
        [R("Network control room", 120, "Engineers watch every radio channel and data link across the ship."),
         R("Fibre room", 100, "Where the fibre cables to the control rooms and the hull antennas meet."),
         R("Battery room", 150, "Keeps the radios on through any power failure."), LOCKERS, WC_STAFF,
         F("Workshop", 80, "Repairs radios and boards.")],
        [R("Engineers' office", 80, "Plans channels and upgrades."), KITCHENETTE, F("Spares store", 80, "Spare radios and boards.")],
    ],
    "structure": "Concrete hall with radio-screened walls.",
    "look": "A blank yellow-trimmed equipment hall with a cluster of masts and dishes on its roof.",
    "entrances": "Equipment door and staff door.",
    "capacity": "Every flight radio and data link on the ship; about 15 engineers per shift.",
    "services": "Screened walls, duplicate power, cooling.",
    "m2_per_person": 200,
}

GATE_TRAFFIC_DESK = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Office floor", 4.2, 2)],
    "wing": 22,
    "rooms": [
        [R("Gate slot desk", 120, "Books time slots for cruisers to pass through each of the three Cruiser Gates."),
         R("Gate status board room", 80, "Live views of the three gates and their berths."), R("Reception", 40, "Visitors sign in."), WC,
         F("Slot office", 50, "Planners who arrange cruiser movements days ahead."),
         F("Berth planning room", 50, "Matches each arriving cruiser to a berth in the Cruiser Docks.")],
        [R("Meeting room", 40, "Meeting room.", 2), KITCHENETTE, WC_STAFF, F("Slot office", 50, "Planners who arrange cruiser movements days ahead."),
         F("Berth planning room", 50, "Matches each arriving cruiser to a berth in the Cruiser Docks.")],
    ],
    "structure": "Concrete frame.",
    "look": "A small purple-trimmed office with a big window facing the cruiser gates.",
    "entrances": "Entrance from the street.",
    "capacity": "About {people} staff.",
    "services": "Links to Starboard Approach Control and the Cruiser Gate Control.",
    "m2_per_person": 12,
}

RESCUE_CENTRE = {
    "mode": "ring",
    "floors": [("Operations floor", 6.0, 1), ("Support floor", 4.2, 2)],
    "wing": 26,
    "halls": [{"name": "Rescue operations room", "span": 2,
               "about": "Coordinators run every search and rescue and evacuation flight from here, with screens linked to rescue craft, "
                        "fire stations and hospitals."}],
    "rooms": [
        [R("Emergency calls room", 120, "Distress calls from craft and from the deck come in here."),
         R("Rescue craft desk", 60, "Sends rescue craft and tracks them."), R("Evacuation planning room", 120, "Plans for flying people out of any part of the ship."),
         R("Medical liaison desk", 40, "Links to hospitals to take casualties."), R("Kit store", 100, "Survival kits, beacons and medical packs."),
         LOCKERS, WC_STAFF, F("Duty room", 40, "Duty coordinators' room.")],
        [R("Rest room", 15, "Bunks for coordinators on long incidents.", 8), R("Mess", 100, "Kitchen and tables."), R("Training room", 80, "Rescue exercises are planned and practised."),
         WC_STAFF, F("Offices", 30, "Offices for planners and managers."),
         F("Exercise planning room", 50, "Plans the regular drills for rescue crews and the deck's evacuation.")],
    ],
    "structure": "Hardened concrete frame with back-up power.",
    "look": "A red-trimmed operations block with a lit red stripe and a rescue-craft pad marked on its roof.",
    "entrances": "Staff entrance; ambulance and equipment entrance at the back.",
    "capacity": "About {people} staff over three watches.",
    "services": "Own generators, links to every fire station, hospital and rescue craft.",
    "m2_per_person": 20,
}

EVAC_HANGAR = {
    "mode": "hall",
    "floors": [("Hangar floor", 22.0, 1), ("Gallery floor", 5.0, 1)],
    "support": [26, 30],
    "halls": [{"name": "Evacuation craft hangar", "span": 2,
               "about": "Aerion's evacuation craft stand here fuelled and ready, nose to the doors, so they can fly people out within minutes of an alarm.",
               "bays": {"name": "Evacuation craft bay", "width": 60, "max": 12,
                        "about": "One evacuation craft on its stand, with fuel, power and boarding steps connected."}},
              {"name": "Boarding hall", "span": 1, "share": 0.25,
               "about": "Where evacuees are counted and led to their craft in an emergency."}],
    "rooms": [
        [R("Readiness room", 80, "Pilots on standby wait here, ready to fly at a moment's notice."),
         R("Craft maintenance shop", 200, "Keeps every evacuation craft in working order."),
         R("Fuel control room", 50, "Controls the fuel lines to every craft."), R("Survival kit store", 150, "Blankets, water, oxygen and first-aid kits loaded onto the craft."),
         LOCKERS, WC_STAFF, F("Parts store", 80, "Spare parts for the craft.")],
        [R("Crew rest rooms", 15, "Bunks for standby crews.", 10), R("Mess", 100, "Kitchen and tables for standby crews."), KITCHENETTE,
         F("Offices", 30, "Offices for the hangar's managers.")],
    ],
    "structure": "Long-span steel hangar, 72 ft (22 m) clear, with fast-opening doors along one side.",
    "look": "A huge steel-grey hangar with a row of tall doors striped orange and white, and readiness lights over each door.",
    "entrances": "A fast-opening door for each craft; staff entrance at the support wing.",
    "capacity": "Aerion's evacuation craft; a standby crew of {people}.",
    "services": "Fuel lines, power, oxygen and air at every bay; alarm links to the Rescue Coordination Centre.",
    "m2_per_person": 150,
}

ACCIDENT_BOARD = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Office floor", 4.2, 2)],
    "wing": 26,
    "halls": [{"name": "Wreckage hall", "span": 2,
               "about": "Investigators lay out the wreckage of crashed craft here, piece by piece, to find the cause of an accident."}],
    "rooms": [
        [R("Flight recorder lab", 120, "Reads the flight recorders recovered from craft after an incident."),
         R("Materials lab", 150, "Tests broken parts to find metal fatigue, fire damage or faults."),
         R("Evidence store", 200, "Locked store for evidence from every open investigation."), R("Reception", 50, "Visitors and witnesses sign in."),
         WC, F("Investigators' office", 40, "Investigators who lead each case."),
         F("Case room", 60, "A team's room for one open investigation, its walls covered with timelines, photos and radar plots."),
         F("Parts examination bay", 80, "A bench room where one damaged part is taken apart and photographed.")],
        [R("Hearing room", 150, "Public hearings where findings are presented."), R("Interview room", 20, "Witnesses and crews are interviewed.", 4),
         R("Reports office", 100, "Writes and publishes the final report on each incident."), KITCHENETTE, WC_STAFF,
         F("Investigators' office", 40, "Investigators who lead each case."),
         F("Human factors room", 50, "Specialists study fatigue, training and teamwork behind an accident."),
         F("Simulation room", 70, "Recreates the last minutes of a flight on screen from the recorder data.")],
    ],
    "structure": "Concrete frame with a tall clear-span wreckage hall.",
    "look": "A sober grey block with a tall loading door for wreckage and a long window onto the hearing room.",
    "entrances": "Public entrance for hearings; loading door for wreckage.",
    "capacity": "About {people} staff.",
    "services": "Overhead crane in the wreckage hall, sealed evidence store.",
    "m2_per_person": 25,
}

OFFICERS_CLUB = {
    "mode": "ring",
    "floors": [("Club floor", 5.0, 1), ("Lounge floor", 4.4, 1)],
    "wing": 24,
    "halls": [{"name": "Officers' dining room", "span": 1, "about": "Formal dining room where flight officers eat and hold mess dinners."}],
    "court": {"name": "Terrace garden", "outdoor": True, "about": "A garden terrace with tables."},
    "rooms": [
        [R("Club lobby", 80, "Members' entrance and porter's desk."), R("Bar", 150, "The officers' bar."), R("Kitchen", 200, "Cooks for the dining room and functions."),
         R("Private dining room", 50, "Bookable for squadron dinners.", 2), WC, F("Lounge", 100, "Armchairs and newspapers."),
         F("Card room", 40, "Tables for cards and board games."),
         F("Guest room", 25, "A bedroom for visiting officers.")],
        [R("Ballroom", 300, "For mess balls and ceremonies."), R("Billiards room", 80, "Billiard tables."), R("Library", 100, "Quiet library."),
         WC, F("Guest room", 25, "A bedroom for visiting officers."),
         F("Squadron room", 60, "Each squadron's own room, hung with its badges and photographs."),
         F("Lounge", 100, "Armchairs and newspapers.")],
    ],
    "structure": "Concrete frame with timber-panelled interiors.",
    "look": "A two-storey club in warm stone with tall windows, brass lamps and a terrace onto its garden.",
    "entrances": "Members' entrance from the street.",
    "capacity": "About {people} members at a function.",
    "services": "Kitchen extraction, bar cellar.",
    "m2_per_person": 6,
}

MAIN_BRIEFING_HALL = {
    "mode": "ring",
    "floors": [("Auditorium floor", 7.0, 1), ("Upper tier floor", 6.0, 1), ("Office floor", 4.2, 1)],
    "wing": 30,
    "halls": [{"name": "Main briefing auditorium", "span": 2,
               "about": "A 1,500-seat auditorium where crews gather every day for the deck-wide flight briefing on traffic, weather and orders.",
               "inside": [{"name": "Briefing stage and screen", "about": "The stage and giant screen the briefing officers speak from.",
                           "at": (0.1, 0.05, 0.8, 0.12)}]}],
    "rooms": [
        [R("Foyer", 600, "Crews gather here before the briefing; screens show the day's headlines."), R("Cloakroom and lockers", 150, "Crews leave flight bags here."),
         R("Green room", 60, "Briefing officers prepare before going on stage."), R("Control booth", 50, "Sound, screens and the live link to every briefing room on the deck."),
         WC, F("Seminar room", 80, "Smaller rooms for follow-up briefings."),
         F("Squadron breakout room", 50, "A squadron splits off here after the main briefing to plan its own flights."),
         F("Crew waiting lounge", 90, "Crews sit with coffee between the briefing and their flights.")],
        [R("Upper foyer", 300, "The foyer for the upper tier."), R("Translation booths", 15, "Interpreters for visiting crews.", 4), WC,
         F("Seminar room", 80, "Smaller rooms for follow-up briefings."),
         F("Press and visitors' room", 60, "Visiting officers and reporters watch the briefing on screens.")],
        [R("Briefing office", 150, "Writes the daily briefing."), R("Graphics room", 80, "Makes the maps and charts shown on screen."),
         KITCHENETTE, WC_STAFF, F("Offices", 40, "Offices for briefing staff.")],
    ],
    "structure": "Concrete frame with a raked auditorium under a long-span steel roof.",
    "look": "A wide hall with a sweeping teal-lit roof edge and a tall glass foyer facing the street.",
    "entrances": "Wide foyer doors from the street; stage door at the back.",
    "capacity": "1,500 seats.",
    "services": "Broadcast link to every briefing room on the deck, translation, stage lighting.",
    "m2_per_person": 4,
}

SQUADRON_BRIEFING = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Briefing floor", 4.2, 3)],
    "wing": 24,
    "rooms": [
        [R("Lobby and room board", 150, "Shows which squadron is in which of the forty rooms."), R("Crew lounge", 120, "Crews wait between briefing and flying."), WC,
         F("Briefing room", 70, "A briefing room for one crew or squadron, with screens and a map wall."),
         F("Route planning room", 40, "A crew plots its route on a big table screen and checks fuel and timings."),
         F("Crew ready room", 50, "Crews wait here in flight kit after their briefing, until they are called to board.")],
        [R("Debrief room", 40, "Crews go over their flight afterwards.", (2, 4)), KITCHENETTE, WC,
         F("Briefing room", 70, "A briefing room for one crew or squadron, with screens and a map wall."),
         F("Route planning room", 40, "A crew plots its route on a big table screen and checks fuel and timings."),
         F("Crew ready room", 50, "Crews wait here in flight kit after their briefing, until they are called to board.")],
    ],
    "fill_cap": 40,
    "structure": "Concrete frame on a 26 ft (8 m) grid.",
    "look": "A long teal-trimmed block with a lit room board in the lobby and rows of small windows.",
    "entrances": "Lobby entrance from the street.",
    "capacity": "Forty briefing rooms.",
    "services": "Screens and briefing network in every room.",
    "m2_per_person": 6,
}

FLIGHT_PLANS = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Office floor", 4.2, 2)],
    "wing": 24,
    "rooms": [
        [R("Filing counter", 120, "Pilots and companies file flight plans in person here."), R("Checking room", 150, "Every plan is checked for route, timing and safety before it is cleared."),
         R("Reception", 50, "Visitors sign in."), WC, F("Plans office", 60, "Officers who check and clear flight plans."),
         F("Route approvals office", 50, "Approves unusual routes and flights that need special permission.")],
        [R("Records room", 100, "Every filed plan is kept for a year."), R("Systems room", 80, "The flight plan computers."), KITCHENETTE, WC_STAFF,
         F("Plans office", 60, "Officers who check and clear flight plans."),
         F("Route approvals office", 50, "Approves unusual routes and flights that need special permission.")],
    ],
    "structure": "Concrete frame.",
    "look": "A plain purple-trimmed office with a public counter behind a glass front.",
    "entrances": "Public entrance for the filing counter.",
    "capacity": "About {people} staff; every flight on and off the ship is filed here.",
    "services": "Links to Dispatch and the Traffic Control Centre.",
    "m2_per_person": 12,
}

SPACE_WEATHER = {
    "court": LIGHT_COURT,
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Forecast floor", 4.2, 1)],
    "wing": 22,
    "rooms": [
        [R("Forecast room", 120, "Forecasters watch the solar wind, radiation and debris and issue warnings."),
         R("Sensor data room", 80, "Readings from the hull sensors and the escort cruisers come in here."), R("Warning desk", 40, "Sends storm and debris warnings to every control room."),
         WC, F("Forecasters' office", 40, "Desks for forecasters."),
         F("Model room", 50, "Computers that run the space weather forecasts.")],
        [R("Research room", 80, "Improves the forecasting models."), KITCHENETTE, WC_STAFF, F("Forecasters' office", 40, "Desks for forecasters."),
         F("Model room", 50, "Computers that run the space weather forecasts.")],
    ],
    "structure": "Concrete frame.",
    "look": "A small office with a white radome on its roof and a lit storm-warning sign.",
    "entrances": "Entrance from the street.",
    "capacity": "About {people} staff.",
    "services": "Sensor links, warning system.",
    "m2_per_person": 15,
}

CHARTS_LIBRARY = {
    "mode": "ring",
    "floors": [("Reading floor", 5.0, 1), ("Stacks floor", 4.2, 1)],
    "wing": 22,
    "halls": [{"name": "Chart room", "span": 1, "about": "Big tables where pilots and planners lay out charts of the Drift Network to plot routes."}],
    "rooms": [
        [R("Enquiry desk", 50, "Librarians find the right chart."), R("Digital chart room", 80, "Screens with the latest charts and route updates."),
         R("Copy room", 40, "Copies charts for crews."), WC, F("Study carrel", 15, "A quiet desk for route planning.")],
        [R("Chart stacks", 200, "Flat drawers of charts for every route in the Drift Network."), R("Chart updates office", 60, "Corrects charts as new information arrives."),
         F("Chart stacks", 150, "Flat drawers of charts.")],
    ],
    "structure": "Concrete frame.",
    "look": "A small teal-trimmed library with tall windows onto its chart room.",
    "entrances": "Entrance from the street.",
    "capacity": "About {people} readers.",
    "services": "Humidity control for paper charts.",
    "m2_per_person": 15,
}

PILOT_BOAT_STATION = {
    "mode": "hall",
    "floors": [("Boat hangar floor", 14.0, 1), ("Crew floor", 4.2, 1)],
    "support": 24,
    "halls": [{"name": "Pilot boat hangar", "span": 2,
               "about": "Pilot boats wait here, fuelled, to fly out and guide big ships into their berths.",
               "bays": {"name": "Pilot boat bay", "width": 30, "max": 10, "about": "One pilot boat on its stand, with fuel and power connected."}}],
    "rooms": [
        [R("Pilots' ready room", 100, "Boat pilots wait for their next ship."), R("Boat dispatch desk", 60, "Assigns a pilot boat to each arriving ship."),
         R("Boat workshop", 200, "Keeps the pilot boats flying."), R("Fuel control", 40, "Controls fuelling of the boats."), LOCKERS, WC_STAFF,
         F("Parts store", 80, "Spare parts for the boats.")],
        [R("Crew rest room", 15, "Bunks for boat crews on night duty.", 8), R("Mess", 80, "Kitchen and tables."), KITCHENETTE, F("Offices", 30, "Offices.")],
    ],
    "structure": "Steel hangar, 46 ft (14 m) clear, with a two-storey support wing.",
    "look": "A steel-grey hangar with tall striped doors and a lit pilot-boat badge over the entrance.",
    "entrances": "Hangar doors to the approach; staff door at the support wing.",
    "capacity": "A fleet of pilot boats; {people} crew.",
    "services": "Fuel, power and air at every bay.",
    "m2_per_person": 100,
}

PROGRAMS = [
    (r"^Port Approach Control$", approach_control("Port", "coming in to the port docks and the Hall of Arrivals",
                                                  ([R("Arrivals liaison desk", 50, "Keeps the Hall of Arrivals and the port docks told of every arrival.")], []))),
    (r"^Starboard Approach Control$", approach_control("Starboard", "taking a cruiser through the three Cruiser Gates",
                                                       ([R("Gate liaison desk", 50, "Keeps the Cruiser Gate Control told of every cruiser on approach.")],
                                                        [R("Cruiser movement desk", 60, "Controllers who handle only the cruisers, which need wide clear paths.")]))),
    (r"^Port Sensor Hall$", sensor_hall("port")),
    (r"^Starboard Sensor Hall$", sensor_hall("starboard")),
    (r"^Pilot Boat Station$", PILOT_BOAT_STATION),
    (r"^Port Controllers' Lodge$", controllers_lodge("port")),
    (r"^Starboard Controllers' Lodge$", controllers_lodge("starboard")),
    (r"^Port Approach Fire Station$", fire_station("Port Approach", [R("Antenna rescue kit room", 50, "Climbing gear for rescuing engineers from masts and towers.")],
                                                   ["Fire engine", "Rescue unit", "Aerial ladder", "Foam tender"], style=1)),
    (r"^Dispatch Fire Station$", fire_station("the Dispatch precinct", [R("Electrical fire kit room", 50, "Special extinguishers for fires in computer and radio rooms.")],
                                              ["Fire engine", "Fire engine", "Rescue unit", "Command car"], style=2)),
    (r"^Port Antenna Plant$", utility_plant("the port hull antennas", [R("Antenna power room", 150, "Power supplies for the antennas on the hull above.")], style=1)),
    (r"Utility Plant$", None),
    (r"Service Shaft$", None),
    (r"^Antenna Field", ANTENNA_FIELD),
    (r"^Main Briefing Hall$", MAIN_BRIEFING_HALL),
    (r"^Squadron Briefing Rooms$", SQUADRON_BRIEFING),
    (r"^Flight Plans Office$", FLIGHT_PLANS),
    (r"^Space Weather Office$", SPACE_WEATHER),
    (r"^Navigation Charts Library$", CHARTS_LIBRARY),
    (r"^Accident Investigation Board$", ACCIDENT_BOARD),
    (r"^Flight Officers' Club$", OFFICERS_CLUB),
    (r"^Briefing Halls Canteen$", canteen("briefing staff and crews", [R("Quick-meal counter", 50, "Meals packed to eat on the way to a flight.")], style=0)),
    (r"^Dispatch Canteen$", canteen("dispatch staff", [R("Night counter", 40, "Hot food through the night shift.")], style=2)),
    (r"^Briefing Annex", BRIEFING_ANNEX),
    (r"^Quiet Garden", garden("quiet garden", [("Shade pergola", 1, "A pergola with climbing plants and benches out of the bustle.")], pavilion=False)),
    (r"^The Beacon$", THE_BEACON),
    (r"^Traffic Control Centre$", TRAFFIC_CONTROL),
    (r"^Backup Control Room$", BACKUP_CONTROL),
    (r"^Beacon Plaza$", BEACON_PLAZA),
    (r"^Controllers' Rest Hall$", REST_HALL),
    (r"^Beacon Garden", garden("garden by the Beacon", [("Tower view lawn", 2, "A lawn with the best view up the Beacon tower."),
                                                         ("Water garden", 1, "A shallow pool with reeds and stepping stones.")])),
    (r"^Dispatch Centre$", DISPATCH_CENTRE),
    (r"^Shuttle Schedules Office$", SHUTTLE_SCHEDULES),
    (r"^Cruiser Liaison Office$", CRUISER_LIAISON),
    (r"^Analysts' Hall$", ANALYSTS),
    (r"^Controllers' Training Centre$", CONTROLLER_TRAINING),
    (r"^Flight Radio Hub$", RADIO_HUB),
    (r"^Dispatch Annex", DISPATCH_ANNEX),
    (r"^Staff Garden", garden("staff garden", [("Picnic lawn", 1, "Picnic tables where staff eat lunch outside.")])),
    (r"^Gate Traffic Desk$", GATE_TRAFFIC_DESK),
    (r"^Rescue Coordination Centre$", RESCUE_CENTRE),
    (r"^Evacuation Craft Hangar$", EVAC_HANGAR),
]

# Each precinct's own plant and shaft, varied by precinct
_PLANTS = {"Port Approach": 0, "Briefing Halls": 1, "Beacon": 2, "Dispatch": 3, "Starboard Approach": 1}
PROGRAMS = [(k, v) for k, v in PROGRAMS if v is not None]
for name, st in _PLANTS.items():
    extra = {"Beacon": [R("Tower power room", 120, "A dedicated, duplicated power feed to the Beacon and the Traffic Control Centre.")],
             "Dispatch": [R("Data centre cooling room", 120, "Extra cooling for the dispatch computers.")]}.get(name, [])
    PROGRAMS.append((r"^%s Utility Plant$" % name, utility_plant(name, extra, style=st)))
    PROGRAMS.append((r"^%s Service Shaft$" % name, service_shaft(name, style=st)))

# Big footprints: halls keep a sensible size; the spare middle becomes an open light court
for _k, _v in PROGRAMS:
    if isinstance(_v, dict) and _v.get("mode") == "ring":
        _v.setdefault("hall_max_m2", 12000)
