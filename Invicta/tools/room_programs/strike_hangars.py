"""Room programs for the Strike Hangars (Deck 5 Aerion), written 27 Nov 2026. See tools/design_rooms.py.

Racks for 3,600 strike craft in 24 rack halls (four wings of six squadrons), 32 launch shafts up to the Forward
Grids (canon, errata C4), the ordnance yards, the repair yards and Wing Command.
"""
import re

from .common import (R, F, WC, WC_STAFF, CLEAN, COMMS, PLANT, KITCHENETTE, PRAYER, FIRST_AID, RECEPTION,
                     LOCKERS, BREAK, SECURITY, utility_plant, service_shaft, fire_station, clinic, canteen, garden,
                     LIGHT_COURT, shed, offices)


def ring(floors, rooms, look, halls=(), court=LIGHT_COURT, wing=24, **kw):
    p = {"mode": "ring", "floors": floors, "wing": wing, "court": court, "hall_max_m2": 12000,
         "halls": list(halls), "rooms": rooms, "look": look,
         "structure": "Concrete frame on a 26 ft (8 m) grid.",
         "entrances": "Main entrance from the street; service door at the back.",
         "capacity": "About {people} people.", "services": "Heating, cooling and data on every floor.", "m2_per_person": 12}
    p.update(kw)
    return p


def yard(zones, look, floors_text, capacity, extra=4.0, split=None, **kw):
    p = {"mode": "yard", "floors": [("Ground", 4.0, 1)], "height_extra": extra, "zones": zones,
         "edge": ("Safety line", "A painted safety line and barrier round the working area."),
         "floors_text": floors_text, "structure": "Reinforced deck surface with tie-downs, fuel and power points.",
         "look": look, "entrances": "Taxi roads and service roads.", "capacity": capacity,
         "services": "Floodlights, ground power, fuel points.", "m2_per_person": 3000}
    if split:
        p["split"] = split
    p.update(kw)
    return p


def picks(pool, hut, tail, lo=3, hi=5):
    def zones(ctx):
        rng = ctx["rng"]
        z = list(pool)
        rng.shuffle(z)
        return [z[0] + (hut,)] + z[1:rng.randint(lo, hi)] + [tail]
    return zones


# ------------------------------------------------------------------ P1 Keelway Gate

CREW_GATE = ring(
    [("Concourse floor", 7.0, 1), ("Upper floor", 4.2, 2)],
    [[R("Duty check-in barriers", 400, "Every strike crew member badges in and out of duty here."),
      R("Alert boards", 200, "Giant boards showing which squadrons are on alert, flying or stood down."),
      R("Kit issue counters", 300, "Crews collect flight suits, helmets and survival vests for their shift."), WC, FIRST_AID,
      F("Squadron muster point", 120, "A marked area where one squadron's crews gather before heading to their rack hall.")],
     [R("Shift managers' room", 80, "Managers watch arrivals and call in reserves."), KITCHENETTE, WC,
      F("Briefing room", 60, "Short shift briefings."), F("Kit store", 80, "Spare flight kit.")]],
    ["A vast concourse with a glowing wall of alert boards, crowds streaming through rows of duty barriers."],
    halls=[{"name": "Crew concourse", "span": 1, "about": "The great hall every strike crew member crosses at the start and end of a shift."}],
    capacity="About 20,000 crew passing through at shift change.", m2_per_person=5)

DECK_LIFT_HALL = shed(
    "Lift hall", "A hall of big crew lifts carrying strike crews who live on other decks up and down to the Strike Hangars.",
    "Lift bank", "A bank of crew lifts to the decks above, with a waiting area in front.", 40,
    [R("Lift control room", 80, "Controls the lifts and sends more at shift change."), R("Waiting hall", 400, "Seats for crews waiting for a lift."), WC,
     F("Lift machine room", 60, "Motors and brakes for one bank of lifts.")],
    [KITCHENETTE, F("Lift engineers' room", 50, "Engineers who keep the lifts running.")],
    ["A long hall of lit lift doors with the deck numbers glowing above each bank."], h=10.0,
    capacity="About 15,000 crew an hour at shift change.", m2_per_person=50)

SHIFT_LODGE = ring(
    [("Ground floor", 4.5, 1), ("Bunk floor", 3.2, (3, 4))],
    [[R("Front desk", 60, "Assigns bunks and wakes crews for their next shift."), R("Mess", 300, "Hot food any hour."), R("Showers", 100, "Showers.", 2), WC,
      F("Quiet lounge", 80, "Dim lounge for resting.")],
     [R("Washroom", 40, "Toilets and basins.", 2), F("Bunk room", 16, "A dark, quiet room with two bunks for crews between shifts.")]],
    ["A plain lodge with rows of small dark windows and a lit wake-up board in the lobby."],
    capacity="About 1,200 bunks.", m2_per_person=25)

ROSTERS = ring(
    [("Ground floor", 4.8, 1), ("Office floor", 4.2, 2)],
    [[R("Roster planning hall", 400, "Planners build shifts for 60,000 crew."), RECEPTION, WC, F("Planners' office", 60, "Shift planners.")],
     [R("Leave office", 80, "Books crews' leave."), KITCHENETTE, WC_STAFF, F("Planners' office", 60, "Shift planners."),
      F("Squadron liaison desk", 40, "Each squadron's roster contact.")]],
    ["A purple-trimmed office block with a giant roster screen in its lobby."], capacity="About {people} staff.")

GATE_CANTEEN = canteen("crews coming on and off shift", [R("All-night counter", 60, "Hot food at any hour.")], style=0)
HANGARS_CLINIC = clinic("the Strike Hangars", [R("Flight medicine room", 40, "Checks crews are fit to fly.", 3), R("Hearing test booth", 15, "Engine noise checks.", 2)],
                        size="large", style=1)
PROW_FIRE = fire_station("the bow end of the Strike Hangars", [R("Crash rescue kit room", 80, "Cutting gear for crashed craft.")],
                         ["Crash tender", "Crash tender", "Rescue unit", "Foam tender"], style=0)
PROW_GARDEN = garden("small park at the bow tip", [("Bow viewpoint", 1, "A lawn at the very tip of the deck.")], style=0)
CREW_GARDEN = garden("crew garden", [("Rest lawn", 1, "Grass to lie on between shifts.")], style=1)
GATE_YARD = yard(picks([("Pod parking", 3, "Crew pods parked in rows."), ("Tug parking", 2, "Tugs that tow craft."),
                        ("Charging lanes", 1, "Charging points."), ("Wash bay", 1, "Pods and tugs are washed.")],
                       [{"size": (12, 8), "rooms": [("Yard hut", 1, "The yard marshal's hut.")]}],
                       ("Access lane", 1, "Lane in and out.")),
                 ["A yard of parked crew pods and tugs under floodlights.", "Rows of yellow tugs and white crew pods."],
                 "Open yard; a hut", "Crew pods and tugs.")

# ------------------------------------------------------------------ P2 Ordnance Yards

def magazine(what, vault, h=10.0):
    return {
        "mode": "hall",
        "floors": [("Magazine floor", h, 1), ("Deep vault level", 8.0, 1, "below")],
        "support": 24,
        "halls": [{"name": "Magazine vaults", "span": 1,
                   "about": "Armoured vaults holding %s, with blast walls between them so an accident in one cannot spread." % what,
                   "bays": {"name": vault, "width": 40, "max": 16,
                            "about": "One armoured vault with racks, its own fire suppression and a blast door."}}],
        "rooms": [[R("Armoured entrance", 80, "Two checks and a blast door."), R("Issue room", 150, "Rounds are signed out to the hauler drones."),
                   R("Magazine control room", 80, "Watches temperature, smoke and doors."), R("Suppression plant", 150, "Deluge and gas systems."),
                   LOCKERS, WC_STAFF, F("Armourers' workshop", 80, "Checks and repairs rounds."), F("Inspection bay", 100, "Rounds are checked before issue.")],
                  [R("Deep vault", 400, "The deepest vaults."), F("Overflow vault", 300, "Extra vaults below.")]],
        "structure": "Heavy reinforced concrete vaults buried in blast berms, with vent panels that blow outward.",
        "look": "A long, low concrete magazine half-buried in grassed berms, with red lights over its blast doors.",
        "entrances": "Drone doors to the haul road; one staff entrance.",
        "capacity": "%s for the strike wings." % what.capitalize(),
        "services": "Deluge fire suppression, temperature control, blast vents.",
        "m2_per_person": 1000,
    }


MISSILE_MAG = magazine("missiles", "Missile vault")
TORPEDO_MAG = magazine("heavy torpedoes", "Torpedo vault", h=12.0)
CANNON_STORE = magazine("belted and boxed cannon shells", "Shell vault", h=8.0)
COUNTERMEASURE = magazine("flares, chaff and decoy drones", "Countermeasure vault", h=8.0)
BOMB_STORE = magazine("free-fall and guided bombs", "Bomb vault")

MAG_CONTROL = ring(
    [("Ground floor", 4.8, 1), ("Upper floor", 4.2, 1)],
    [[R("Ordnance control room", 200, "Tracks every round in every magazine, and sends rounds to the rack halls."),
      R("Issue desk", 80, "Approves each issue."), SECURITY, WC, F("Controllers' office", 40, "Ordnance controllers.")],
     [KITCHENETTE, WC_STAFF, F("Records room", 50, "Records of every round."), F("Controllers' office", 40, "Ordnance controllers.")]],
    ["A small hardened block with a wall of status screens glowing through narrow windows."], capacity="About {people} staff.")

WEAPONS_ASSEMBLY = shed(
    "Assembly hall", "Armorers fit fuzes, mate warheads to missiles and test them before they go to the rack halls.",
    "Assembly cell", "A blast-walled cell where one missile or bomb is assembled.", 30,
    [R("Fuze room", 100, "Fuzes are fitted here, one at a time."), R("Test bay", 200, "Missiles' electronics are tested."),
     R("Blast shelter", 60, "Armorers shelter here if an alarm sounds."), LOCKERS, WC_STAFF, F("Armorers' bench room", 60, "Bench work.")],
    [R("Engineers' office", 80, "Plans assembly work."), KITCHENETTE, F("Records room", 40, "Assembly records.")],
    ["A long blast-walled hall with red warning lights and earth berms along both sides."], h=12.0)

ARMORERS_HALL = ring(
    [("Workshop floor", 6.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Tool crib", 200, "Tools signed out to armorers."), R("Training bay", 400, "A mock rack with dummy rounds for training new armorers."), LOCKERS, WC,
      F("Armorers' workshop", 100, "Workshop for one armorer team."), F("Gun shop", 120, "Repairs cannons.")],
     [KITCHENETTE, WC, F("Classroom", 60, "Armorer classes."), F("Team room", 50, "A team's office.")]],
    ["A sturdy workshop block with the armorers' crossed-shell badge over the door."], capacity="About {people} armorers.")

TEST_RANGE = yard([("Firing line", 1, "Where weapons are mounted and fired.",
                    [{"size": (20, 10), "rooms": [("Range control bunker", 2, "Controls firing; armoured glass."), ("Weapon prep room", 1, "Weapons are made ready.")]}]),
                   ("Range", 5, "A sealed, baffled range where weapons are fired into a backstop."),
                   ("Baffles", 1, "Armoured baffles that catch stray rounds."),
                   ("Backstop berm", 1, "An armoured earth backstop.")],
                  "A long sealed range lined with armoured baffles and a huge backstop berm.", "Open range; a control bunker",
                  "One firing at a time.", extra=12.0)
DISPOSAL_PIT = yard([("Disposal pit", 2, "A deep armoured pit where faulty rounds are destroyed safely.",
                      [{"size": (16, 10), "rooms": [("Control bunker", 1, "Controls each disposal from behind armour.")]}]),
                     ("Holding pad", 1, "Rounds waiting for disposal."), ("Blast berm", 1, "An earth berm round the pit.")],
                    "A fenced pit ringed by earth berms, with a squat control bunker.", "Open pit; a bunker", "Faulty rounds.", extra=6.0)

DRONE_DEPOT = shed(
    "Drone hall", "Hauler drones that carry rounds from the magazines to the rack halls park and charge here.",
    "Drone bay", "Charging pads for a group of hauler drones.", 30,
    [R("Drone control room", 150, "Routes every hauler drone."), R("Drone workshop", 300, "Repairs drones."), R("Battery room", 200, "Charges batteries."),
     LOCKERS, WC_STAFF, F("Parts store", 80, "Drone parts.")],
    [KITCHENETTE, F("Offices", 30, "Offices.")],
    ["A long shed with rows of glowing charging pads and drones taking off from its roof."], h=10.0)

PROPELLANT = yard([("Fuel tanks", 5, "Double-walled tanks of craft fuel inside bund walls.",
                    [{"size": (24, 12), "rooms": [("Pump house", 2, "Pumps fuel to the racks."), ("Farm control room", 1, "Watches every tank.")]}]),
                   ("Pipe rack", 1, "Pipes to the rack halls."), ("Fire water ring", 1, "Hydrants and foam monitors.")],
                  "Rows of white double-walled fuel tanks behind bund walls, lit orange.", "Open tank farm; a pump house",
                  "Fuel for the strike craft.", extra=26.0)
CELL_FARM = yard([("Cell racks", 4, "Racks of charged power cells for the craft.",
                   [{"size": (24, 12), "rooms": [("Charging control", 2, "Watches every cell charging."), ("Cell test room", 1, "Tests cells.")]}]),
                  ("Charging lanes", 2, "Cells on charge."), ("Cooling plant", 1, "Cools the charging cells.")],
                 "Long rows of glowing cell racks under a lattice of cooling pipes.", "Open cell farm; a control room",
                 "Power cells for the strike craft.", extra=10.0)
FUEL_CONTROL = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Fuel control room", 200, "Controls the pumps and valves on the fuel lines to the rack halls."), R("Pump room", 300, "Booster pumps."), WC,
      F("Operators' room", 40, "Operators.")],
     [KITCHENETTE, WC_STAFF, F("Engineers' office", 40, "Engineers.")]],
    ["A yellow-trimmed control block with pipe racks running into it."], capacity="About {people} staff.")
BERM_PARK = garden("planted blast buffer", [("Grassed berm", 3, "A long grassed earth berm that soaks up any blast."),
                                            ("Berm path", 1, "A path along the top of the berm.")], style=2, pavilion=False)
ARMORERS_LODGE = SHIFT_LODGE
DRONE_RACKS = lambda what: shed(
    "Drone rack hall", "Ready racks of %s drones, stacked and charged, that can be launched quickly." % what,
    "Drone rack row", "A row of tiered racks of drones.", 30,
    [R("Drone launch control", 150, "Launches drones when they are called."), R("Drone workshop", 200, "Repairs drones."), LOCKERS, WC_STAFF,
     F("Charging room", 80, "Drone batteries.")],
    [KITCHENETTE, F("Offices", 30, "Offices.")],
    ["A tall rack hall with tiers of drones glowing through its high windows."], h=30.0)
ORDNANCE_FIRE = fire_station("the Ordnance Yards", [R("Blast suit room", 60, "Blast suits for bomb disposal."), R("Bomb disposal kit", 80, "Robots and kit.")],
                             ["Fire engine", "Foam tender", "Bomb disposal unit", "Rescue unit"], style=2)
ORDNANCE_CLINIC = clinic("the Ordnance Yards", [R("Burns room", 40, "Burn treatment.", 2), R("Decontamination room", 40, "Washes chemicals off.")], style=0)
BLAST_BERM = yard([("Earth berm", 4, "An earth and armour berm that keeps a blast in one magazine from reaching the next."),
                   ("Armour wall", 1, "An armoured wall in the berm."), ("Berm path", 1, "A patrol path along the top.")],
                  ["A long grassed earth berm with an armoured core.", "A tall earth berm with armour plates on its face."],
                  "Earth berm", "Blast protection.", extra=12.0)
BUNKER = magazine("spare munitions", "Bunker vault", h=6.0)
BUNKER["look"] = ["A small concrete bunker buried in an earth berm, with a single blast door.", "A grass-roofed bunker with a red light over its door."]

# ------------------------------------------------------------------ P3 / P4 Launch wings

def launch_shafts(ctx):
    nums = [int(x) for x in re.findall(r"\d+", ctx["name"])]
    lo = nums[0] if nums else 1
    side = "port" if lo <= 16 else "starboard"
    z = []
    for k in range(4):
        z.append(("Launch shaft %d" % (lo + k), 60,
                  "A 197 x 131 ft (60 x 40 m) shaft that lifts a strike craft on its launch cradle up to the %s Forward Grid and fires it out." % side,
                  [], [("Shaft head doors", "Armoured doors that close over the shaft between launches.", (0.05, 0.05, 0.9, 0.9))]))
        if k < 3:
            z.append(("Shaft wall", 40, "The armoured wall between two shafts, holding the cradle rails and cables."))
    return z


LAUNCH_SHAFTS = yard(launch_shafts, "Four huge rectangular shaft openings in a row, ringed with yellow-black stripes and lit from below.",
                     "Four shaft heads", "Four launch shafts.", extra=0.0,
                     structure="Armoured shaft walls rising through the deck ceiling to the Forward Grid (canon errata C4).",
                     entrances="Craft roll onto the cradles from the launch queue.")

LAUNCH_CONTROL = ring(
    [("Ground floor", 5.0, 1), ("Control floor", 6.0, 1)],
    [[R("Equipment room", 200, "Computers for launch control."), R("Battery room", 100, "Back-up power."), LOCKERS, WC_STAFF,
      F("Engineers' room", 50, "Shaft engineers on call.")],
     [R("Launch control room", 300, "Controllers at windows over the shaft heads clear each craft to launch."), KITCHENETTE, WC_STAFF,
      F("Shaft desk room", 40, "A desk for one group of shafts.")]],
    ["A glass-fronted control block on stilts looking down over the shaft heads, its windows lit blue."],
    capacity="About {people} controllers.", m2_per_person=20)

QUEUE_APRON = yard([("Launch queue", 4, "Craft line up nose to tail in order for their shaft."), ("Marshal's lane", 1, "Marshals walk the line.",
                    [{"size": (12, 8), "rooms": [("Marshal's hut", 1, "The launch marshal's hut.")]}])],
                   "A long apron of craft lined up nose to tail under floodlights.", "Open apron; a hut", "About 40 craft in line.")
ARMING_APRON = yard([("Arming bays", 4, "Craft stop here while armorers pull the safety pins and make last weapons checks.",
                      [{"size": (14, 8), "rooms": [("Armorers' shelter", 2, "Armorers' kit and shelter."), ("Pin board room", 1, "Every safety pin is hung here and counted.")]}]),
                     ("Safe arc", 1, "A clear area weapons point into while being armed.")],
                    "An apron of marked arming bays with blast screens between them.", "Open apron; armorers' shelter", "About 20 craft at once.")
READY_ROOMS = ring(
    [("Ground floor", 4.5, 1), ("Upper floor", 4.0, 1)],
    [[R("Alert board room", 80, "Shows which crews are on alert and how fast they must launch."), R("Kit room", 100, "Flight kit ready to grab."), WC,
      F("Ready room", 50, "A crew waits here on alert, in flight kit, with a screen and recliners.")],
     [R("Rest room", 15, "Bunks for crews on long alerts.", 6), KITCHENETTE, F("Ready room", 50, "A crew waits here on alert, in flight kit, with a screen and recliners.")]],
    ["A low block with a red alert lamp over every door and slides down to the apron."], capacity="About {people} crew on alert.")
SHAFT_SHOP = shed("Workshop hall", "Lift cradles and shaft doors are repaired here.", "Cradle bay", "A bay holding one launch cradle under repair.", 40,
                  [R("Rail shop", 200, "Repairs the cradle rails."), R("Door seal shop", 150, "Repairs the shaft door seals."), LOCKERS, WC_STAFF,
                   F("Parts store", 80, "Spares.")],
                  [KITCHENETTE, F("Engineers' office", 40, "Engineers.")], ["A tall yellow-striped workshop with a cradle on its floor."], h=16.0)
CATAPULT_PLANT = shed("Launch power hall", "The plant that powers the launch rails in the shafts: big capacitor banks that charge between launches.",
                      "Capacitor bank", "One bank of capacitors and switchgear for a group of shafts.", 30,
                      [R("Plant control room", 120, "Watches every bank."), R("Cooling plant", 200, "Cools the capacitors."), LOCKERS, WC_STAFF,
                       F("Switch room", 60, "Switchgear.")],
                      [F("Cable gallery", 60, "Cables to the shafts.")], ["A blank yellow-trimmed plant hall humming with power."], h=12.0)
LAUNCH_APRON = yard(picks([("Launch line", 3, "Craft lined up for the shafts."), ("Tug lane", 1, "Tugs move craft."),
                           ("Fuel point", 1, "Quick refuelling."), ("Holding bay", 2, "Craft waiting for a slot.")],
                          [{"size": (12, 8), "rooms": [("Marshal's hut", 1, "The marshal's hut.")]}], ("Taxi lane", 1, "The taxi lane.")),
                    ["An apron of craft in neat lines under floodlights.", "Rows of strike craft on a marked apron."],
                    "Open apron; a hut", "Craft waiting for launch.")
RECOVERY_APRON = yard([("Recovery lanes", 4, "Returning craft drop out of the shafts here and are stopped by arrestor gear.",
                        [{"size": (16, 10), "rooms": [("Recovery control", 2, "Controls landings."), ("Crash crew shelter", 1, "Crash crews on standby.")]}]),
                       ("Safing area", 1, "Weapons are made safe."), ("Taxi-off lane", 1, "Craft taxi to their rack hall.")],
                      "A long floodlit apron with arrestor cables and crash barriers.", "Open apron; a control hut", "About 30 craft an hour.")
TRIAGE = shed("Triage bay", "Craft that come back damaged get a first inspection here to decide what repairs they need.",
              "Triage stand", "A stand where one damaged craft is inspected.", 40,
              [R("Inspection office", 80, "Inspectors decide each craft's repairs."), R("Scanner room", 100, "Scans hulls for hidden damage."), LOCKERS, WC_STAFF,
               F("Inspectors' room", 40, "Inspectors.")],
              [KITCHENETTE, F("Records room", 40, "Damage records.")], ["A wide open-fronted bay with floodlit inspection stands."], h=14.0)

# ------------------------------------------------------------------ P5 / P6 Rack halls

def rack_hall(ctx):
    return None


RACK_HALL = shed(
    "Rack hall", "The squadron's 150 strike craft stored in tiered racks to the roof, brought down by rack lifts for each sortie.",
    "Rack tier column", "A column of racks, stacked in tiers to the roof, each holding one craft with its fuel, power and data plugged in.", 40,
    [R("Rack lift landing", 400, "Craft come down from the racks here onto the floor."), R("Squadron ready room", 150, "The squadron's crews wait here."),
     R("Line maintenance shop", 300, "Quick repairs between sorties."), R("Crew chief's office", 50, "Runs the hall's ground crew."), LOCKERS, WC_STAFF,
     F("Ground crew room", 60, "A ground crew team's room."), F("Spares cage", 60, "Quick-change spares.")],
    [R("Rack control room", 100, "Operators run the rack lifts and track every craft's place."), KITCHENETTE,
     F("Rack gallery", 60, "A walkway along the racks for checks."), F("Squadron office", 40, "Squadron staff.")],
    ["A colossal rack hall, its glass end wall showing tier upon tier of craft in their racks, lit by blue rack lights.",
     "A towering steel hall with a wide door at floor level and rows of lit rack numbers up its side."],
    h=60.0, support_w=30,
    structure="Steel rack frame 197 ft (60 m) tall inside a clad hall; rack lifts at each column.",
    entrances="Hall doors to the taxi apron; crew entrance at the support wing.",
    capacity="150 strike craft.", services="Fuel, power, data and air to every rack.")

READY_HALL = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 2)],
    [[R("Wing briefing theatre", 400, "The whole wing's crews are briefed together."), R("Alert board hall", 150, "Shows every squadron's state."), WC,
      F("Squadron ready room", 80, "A squadron's crews wait here on alert."), F("Briefing room", 60, "A crew's briefing.")],
     [R("Wing commander's office", 60, "The wing commander."), KITCHENETTE, WC,
      F("Squadron ready room", 80, "A squadron's crews wait here on alert."), F("Debrief room", 40, "Debriefs.")]],
    ["A long ready hall with the wing's badge over its doors and red alert lamps along its front."], capacity="About {people} crew.")
RACK_LIFT_CONTROL = ring(
    [("Ground floor", 5.0, 1), ("Control floor", 5.0, 1)],
    [[R("Equipment room", 200, "Computers for the rack lifts."), LOCKERS, WC_STAFF, F("Engineers' room", 50, "Lift engineers.")],
     [R("Rack lift control room", 300, "Operators bring craft down from the racks in every hall."), KITCHENETTE, F("Desk room", 40, "One hall's desk.")]],
    ["A small control block with screens showing every rack."], capacity="About {people} operators.")
TAXI_APRON_BIG = yard([("Taxi lanes", 4, "Craft taxi from the rack halls to the launch roads.",
                        [{"size": (12, 8), "rooms": [("Marshal's hut", 1, "The marshal's hut.")]}]),
                       ("Holding bays", 1, "Craft wait for a gap."), ("Tug parking", 1, "Tugs.")],
                      "A broad taxi apron with lit lane lines and craft moving in rows.", "Open apron", "Craft moving to and from the halls.")
HANGAR_CANTEEN = canteen("rack hall crews", [R("Flight meals counter", 50, "Meals packed for crews on alert.")], style=3)
PARTS_STORE = shed("Parts store", "Spare parts for the wings' craft, racked and picked by robots.", "Parts aisle", "An aisle of racks.", 36,
                   [R("Goods in", 300, "Parts arrive."), R("Issue counter", 100, "Crews collect parts."), LOCKERS, WC_STAFF, F("Small parts cage", 60, "Small parts.")],
                   [KITCHENETTE, F("Robot control", 50, "Controls the robots.")], ["A long grey parts store with loading docks."], h=14.0)
CREW_LOCKERS = ring(
    [("Locker floor", 4.5, 1), ("Upper floor", 4.0, 1)],
    [[R("Entrance", 60, "Crews badge in."), R("Laundry", 200, "Washes flight suits."), WC,
      F("Locker room", 90, "Lockers, benches and showers."), F("Drying room", 30, "Dries wet kit.")],
     [F("Locker room", 90, "Lockers, benches and showers."), F("Rest room", 40, "Rest between shifts.")]],
    ["A plain locker block with steam from its laundry vents."], capacity="About {people} crew.", m2_per_person=4)
RACKS_FIRE = lambda side, st: fire_station("the %s rack halls" % side, [R("Rack rescue kit room", 80, "Kit for fires high in the racks.")],
                                           ["Crash tender", "Aerial ladder", "Foam tender", "Rescue unit"], style=st)
OPEN_BAY = yard(picks([("Parking rows", 4, "Craft parked between sorties."), ("Service line", 2, "Fuel and power carts."),
                       ("Tug lane", 1, "Tugs."), ("Quick-turn bay", 1, "Quick refuel and rearm.")],
                      [{"size": (12, 8), "rooms": [("Crew chief's hut", 1, "Ground crew hut.")]}], ("Taxi lane", 1, "Lane to the apron.")),
                ["An open hangar floor of parked craft under floodlights.", "Rows of strike craft on a vast open floor.",
                 "Craft parked in neat rows with fuel carts between."], "Open hangar floor", "Craft between sorties.")
TAXI_APRON = yard(picks([("Taxi lanes", 3, "Craft taxi between the halls and the launch roads."), ("Holding bay", 1, "Craft wait."),
                         ("Tug parking", 1, "Tugs.")], [], ("Edge lane", 1, "Service lane.")),
                  ["A taxi apron with lit lane lines.", "A broad apron of painted taxi lanes."], "Open apron", "Craft moving.")
WASH_HALL = shed("Wash hall", "Every craft is washed and decontaminated after a sortie.", "Wash bay", "A wash bay with sprays and drains.", 40,
                 [R("Water treatment room", 300, "Cleans and recycles wash water."), R("Chemical store", 100, "Cleaning chemicals."), LOCKERS, WC_STAFF,
                  F("Plant room", 80, "Pumps.")],
                 [F("Control gallery", 60, "Controls the washes.")], ["A long steamy hall with spray arches over each bay."], h=14.0)

# ------------------------------------------------------------------ P7 / P9 Repair yards

def repair_hangar(about, bay, extra):
    return shed("Repair hangar", about, bay, "A bay where one craft is taken apart on stands, with an overhead crane.", 60,
                [R("Strip-down area", 600, "Parts are removed and labelled."), R("Inspection lab", 200, "Checks for cracks and damage."),
                 R("Tool crib", 120, "Tools."), LOCKERS, BREAK, WC_STAFF] + extra + [F("Fitters' workshop", 120, "Benches."), F("Parts kitting room", 80, "Parts for each job.")],
                [R("Engineering office", 150, "Plans each rebuild."), KITCHENETTE, F("Planning office", 50, "Planners."), F("Crane gallery", 60, "Crane access.")],
                ["A vast repair hangar with orange crane girders and craft on stands inside.",
                 "A huge steel hangar with sawtooth rooflights and the glow of welding."], h=30.0, support_w=30)


HEAVY_REPAIR = repair_hangar("Craft are fully stripped down and rebuilt here, up to six at a time.", "Strip-down bay", [])
REBUILD = repair_hangar("Craft with battle damage are rebuilt here.", "Rebuild bay", [R("Battle damage survey room", 100, "Maps each craft's damage.")])
ENGINE_SHOP = shed("Engine shop", "Craft engines are overhauled here.", "Engine bay", "A bay with an engine on a stand.", 40,
                   [R("Test cell control", 100, "Runs engines on test."), R("Clean room", 150, "Precision parts."), LOCKERS, WC_STAFF,
                    F("Fitters' workshop", 100, "Benches.")],
                   [KITCHENETTE, F("Engineers' office", 40, "Engineers."), F("Records room", 40, "Engine logbooks.")],
                   ["A long engine shop with exhaust stacks on its roof."], h=16.0,
                   extra_halls=[{"name": "Engine test cell", "span": 1, "share": 0.2, "about": "A soundproof cell where engines are run up."}])
ENGINE_TEST = yard([("Test stands", 3, "Engines are run up on stands behind blast fences.",
                     [{"size": (16, 10), "rooms": [("Test control bunker", 2, "Runs each test."), ("Instrument room", 1, "Records results.")]}]),
                    ("Blast fence", 1, "Tall fences that deflect the exhaust."), ("Engine transport lane", 1, "Lane for engine carts.")],
                   "Engine stands behind tall angled blast fences, lit by test lights.", "Open test stands; a bunker", "Four engines at once.", extra=12.0)
AIRFRAME = shed("Airframe shop", "Craft frames, skins and landing gear are repaired here.", "Airframe bay", "A bay with a craft frame on a jig.", 50,
                [R("Sheet metal shop", 300, "Makes skin panels."), R("Landing gear shop", 200, "Overhauls landing gear."), LOCKERS, WC_STAFF,
                 F("Fitters' workshop", 100, "Benches.")],
                [KITCHENETTE, F("Engineers' office", 40, "Engineers.")], ["A tall shop with craft frames on jigs visible inside."], h=20.0)
AVIONICS = ring(
    [("Lab floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Sensor lab", 200, "Repairs craft sensors."), R("Radio lab", 150, "Repairs radios."), R("Flight computer lab", 150, "Tests flight computers."),
      LOCKERS, WC, F("Electronics bench room", 50, "Benches.")],
     [R("Clean room", 150, "Dust-free assembly."), KITCHENETTE, WC, F("Engineers' office", 40, "Engineers.")]],
    ["A clean white lab block with blue-lit windows."], capacity="About {people} technicians.")
COATINGS = shed("Coatings hall", "Craft get their armour and low-signature coatings here.", "Spray booth", "A sealed spray booth for one craft.", 40,
                [R("Mixing room", 100, "Coatings are mixed."), R("Curing oven", 300, "Bakes coatings hard."), LOCKERS, WC_STAFF, F("Store", 60, "Coatings store.")],
                [F("Extraction gallery", 60, "Fume extraction fans.")], ["A long sealed hall with fume stacks along its roof."], h=16.0)
PAINT_HALL = shed("Paint hall", "Craft get squadron markings and paint touch-ups here.", "Paint booth", "A booth for one craft.", 40,
                  [R("Stencil room", 80, "Squadron markings cut here."), R("Paint store", 100, "Paints."), LOCKERS, WC_STAFF, F("Mixing room", 40, "Mixing.")],
                  [F("Extraction gallery", 60, "Fans.")], ["A paint hall with colourful squadron stripes on its doors."], h=14.0)
REPAIR_WAREHOUSE = PARTS_STORE
SALVAGE = yard([("Wreck rows", 4, "Wrecked craft waiting to be stripped.",
                 [{"size": (16, 10), "rooms": [("Salvage office", 2, "Records what is saved."), ("Strip-down shelter", 1, "Shelter for workers.")]}]),
                ("Parts piles", 2, "Saved parts sorted for checking."), ("Scrap bay", 1, "Scrap going to Ferrum."), ("Crane lane", 1, "Crane lane.")],
               "A yard of broken craft and sorted parts under floodlights, with a crane among them.", "Open yard; an office", "Wrecks and parts.", extra=14.0)
REPAIR_CREWS = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Canteen", 600, "Hot food for mechanics."), R("Kitchen", 200, "Cooks."), WC, F("Locker room", 90, "Lockers and showers.")],
     [KITCHENETTE, WC, F("Rest room", 40, "Rest between shifts."), F("Training room", 60, "Courses.")]],
    ["A sturdy mechanics' hall with steam from its kitchen vents."], capacity="About {people} mechanics.")
WORK_YARD = yard(picks([("Work stands", 3, "Craft on stands for big outdoor jobs."), ("Crane lane", 1, "Mobile cranes."),
                        ("Parts staging", 1, "Parts waiting to go on."), ("Engine carts", 1, "Engine carts.")],
                       [{"size": (12, 8), "rooms": [("Foreman's hut", 1, "The yard foreman.")]}], ("Access lane", 1, "Lane.")),
                 ["An outdoor yard with craft on stands and a mobile crane.", "A yard of work stands and parts crates."], "Open yard", "Big repairs.")
PARTS_SHED = shed("Parts shed", "A covered store for parts close to the repairs.", "Rack bay", "A bay of racks.", 30,
                  [R("Issue counter", 60, "Parts are signed out."), WC_STAFF, F("Small parts cage", 50, "Small parts.")],
                  [F("Mezzanine store", 60, "Light parts.")], ["A plain grey shed.", "A steel shed with roller doors.", "A shed with a yellow dock edge."], h=10.0)
WEAPONS_FIT = shed("Weapons fit hall", "Guns and weapon pylons are fitted to craft and tested.", "Fit bay", "A bay with a craft on stands.", 40,
                   [R("Gun shop", 200, "Repairs cannons."), R("Pylon shop", 150, "Repairs pylons."), LOCKERS, WC_STAFF, F("Bench room", 60, "Benches.")],
                   [KITCHENETTE, F("Engineers' office", 40, "Engineers.")], ["A blast-walled hall with a test butt at one end."], h=16.0)
SHIELD_HALL = shed("Shield hall", "A screened hall where craft shields are tuned.", "Calibration bay", "A screened bay for one craft.", 40,
                   [R("Tuning control room", 120, "Tunes each shield."), R("Emitter workshop", 150, "Repairs emitters."), LOCKERS, WC_STAFF,
                    F("Lab", 60, "Lab.")],
                   [KITCHENETTE, F("Engineers' office", 40, "Engineers.")], ["A smooth white hall with a faint blue glow."], h=16.0)
CANOPY_SHOP = ring(
    [("Workshop floor", 6.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Canopy shop", 300, "Repairs and polishes canopies."), R("Ejection seat shop", 300, "Overhauls ejection seats; explosive parts are kept separate."),
      R("Cockpit fit room", 200, "Fits cockpit panels."), LOCKERS, WC, F("Bench room", 50, "Benches.")],
     [KITCHENETTE, WC, F("Engineers' office", 40, "Engineers.")]],
    ["A workshop with canopies gleaming on racks inside."], capacity="About {people} technicians.")
CELL_SHOP = shed("Cell shop", "Craft power cells are tested and recharged.", "Cell test bay", "A bay of test rigs.", 30,
                 [R("Charging hall", 300, "Recharges cells."), R("Fire-safe store", 150, "Damaged cells kept apart."), LOCKERS, WC_STAFF,
                  F("Bench room", 50, "Benches.")],
                 [F("Cooling gallery", 60, "Cooling.")], ["A yellow-trimmed shed with cooling stacks."], h=10.0)
DRONE_REPAIR = shed("Drone repair hall", "Strike and intercept drones are repaired here.", "Repair bay", "A bay with a drone on a stand.", 30,
                    [R("Electronics shop", 150, "Repairs drone electronics."), R("Test flight cage", 300, "Repaired drones fly in a net cage."), LOCKERS, WC_STAFF,
                     F("Bench room", 50, "Benches.")],
                    [KITCHENETTE, F("Engineers' office", 40, "Engineers.")], ["A hall with a netted test cage on its roof."], h=14.0)
TOOL_STORE = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Issue counter", 100, "Tools and gauges signed out."), R("Calibration lab", 200, "Checks every tool is accurate."), WC,
      F("Tool store", 80, "Racks of tools.")],
     [WC, F("Gauge store", 60, "Gauges."), F("Calibration room", 50, "Calibration.")]],
    ["A tidy store with a long issue counter behind glass."], capacity="About {people} staff.")

# ------------------------------------------------------------------ P8 Wing Command

WING_COMMAND = ring(
    [("Ground floor", 6.0, 1), ("Staff floor", 4.4, 3), ("Command floor", 5.0, 1)],
    [[R("Guarded entrance", 100, "Visitors are checked and escorted."), R("Hall of the Wings", 400, "Hung with the badges of all 24 squadrons."), WC,
      F("Staff office", 60, "Wing staff."), F("Meeting room", 40, "Meetings.")],
     [R("Personnel office", 150, "Postings and records."), R("Logistics office", 150, "Plans supplies."), KITCHENETTE, WC_STAFF,
      F("Staff office", 60, "Wing staff."), F("Planning room", 80, "Plans.")],
     [R("Flight operations desk", 200, "Vector's flight operations desk, which runs the strike wings' flying."),
      R("Commander's office", 120, "The commander of the strike wings."), R("Conference room", 150, "Senior officers meet."), WC,
      F("Senior officer's office", 50, "Senior officers.")]],
    ["A grand headquarters in dark stone with the four wings' badges over its doors and a lit command floor on top."],
    capacity="About {people} staff.", m2_per_person=20)
STRIKE_OPS = ring(
    [("Equipment floor", 5.0, 1), ("Operations floor", 8.0, 1), ("Support floor", 4.2, 1)],
    [[R("Computer hall", 400, "Computers that track every craft."), R("Power room", 200, "Back-up power."), LOCKERS, WC_STAFF,
      F("Equipment room", 150, "Equipment.")],
     [R("Wing desks", 300, "Each wing's controllers."), KITCHENETTE, WC_STAFF, F("Analysts' room", 60, "Analysts.")],
     [R("Rest room", 15, "Bunks.", 6), KITCHENETTE, F("Offices", 40, "Offices.")]],
    ["A hardened block with a single long band of blue light."],
    halls=[{"name": "Strike operations room", "span": 2, "about": "A live picture of every strike craft in flight on a wall of screens."}],
    capacity="About {people} staff.", m2_per_person=25)
INTEL_BRIEFING = ring(
    [("Ground floor", 6.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Secure entrance", 80, "Cleared crews only."), WC, F("Threat briefing room", 80, "Crews are briefed on enemy threats before a sortie.")],
     [R("Intelligence office", 200, "Analysts prepare threat briefings."), KITCHENETTE, WC_STAFF, F("Analysts' office", 50, "Analysts.")]],
    ["A dark secure block with narrow windows and a guarded door."],
    halls=[{"name": "Main briefing theatre", "span": 2, "about": "A theatre where whole wings get threat briefings."}],
    capacity="About {people} crew.")
SQN_LEADERS = ring(
    [("Ground floor", 5.0, 1), ("Office floor", 4.2, 2)],
    [[R("Wardroom", 400, "The squadron leaders' mess and lounge."), R("Kitchen", 150, "Cooks."), WC,
      F("Squadron leader's office", 60, "One of the 24 squadron leaders' offices.")],
     [KITCHENETTE, WC, F("Squadron leader's office", 60, "One of the 24 squadron leaders' offices."), F("Meeting room", 40, "Meetings.")]],
    ["A dignified hall with 24 squadron flags along its front."], capacity="About {people} staff.")
MISSION_PLANNING = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 2)],
    [[R("Secure entrance", 60, "Checks."), WC, F("Mission planning room", 80, "A crew plans routes, targets and timings on a big table screen.")],
     [KITCHENETTE, WC, F("Mission planning room", 80, "A crew plans routes, targets and timings on a big table screen."),
      F("Target study room", 50, "Crews study images of targets.")]],
    ["A secure office block with screened windows."], capacity="About {people} crew.")
DEBRIEF_HALL = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Arrival desk", 80, "Crews report in straight after landing."), WC, F("Debrief room", 40, "A crew replays its flight and reports.")],
     [R("Gun camera review room", 100, "Reviews footage."), KITCHENETTE, WC, F("Debrief room", 40, "A crew replays its flight and reports.")]],
    ["A low block with a lit arrival desk visible through its glass front."], capacity="About {people} crew.")
SPACE_CONDITIONS = ring(
    [("Ground floor", 4.8, 1), ("Upper floor", 4.2, 1)],
    [[R("Forecast room", 120, "Forecasts space weather, debris and radiation for flight crews."), WC, F("Forecasters' office", 40, "Forecasters.")],
     [KITCHENETTE, WC_STAFF, F("Forecasters' office", 40, "Forecasters.")]],
    ["A small office with a white radome on its roof."], capacity="About {people} staff.")
COMMAND_PLAZA = {
    "mode": "park", "floors": [("Ground", 4.0, 1)], "height_extra": 12.0,
    "zones": [("Parade square", 5, "The parade and gathering square at Wing Command.", [],
               [("Flag masts", "Flags of the four strike wings.", (0.3, 0.05, 0.4, 0.04)),
                ("Reviewing stand", "A stand for the commander.", (0.4, 0.1, 0.2, 0.06))]),
              ("Tree avenue", 1, "Trees round the square."),
              ("Café terrace", 1, "Tables by a kiosk.", [{"size": (16, 10), "rooms": [("Café kiosk", 2, "Coffee."), ("Toilets", 1, "Toilets.")]}])],
    "edge": ("Planted edge", "Planting round the square."), "floors_text": "Open square; a kiosk", "structure": "Paving over the deck.",
    "look": "A huge parade square with the four wings' flags and a reviewing stand.", "entrances": "Open on all sides.",
    "capacity": "A parade of {people}.", "services": "Lighting, PA.", "m2_per_person": 4}
DUTY_LODGE = ring(
    [("Ground floor", 4.5, 1), ("Bunk floor", 3.2, (3, 4))],
    [[R("Front desk", 60, "Assigns bunks."), R("Mess", 300, "Food."), WC, F("Quiet lounge", 80, "Rest.")],
     [R("Washroom", 40, "Toilets and showers.", 2), F("Bunk room", 16, "Two bunks for crews on 24-hour duty, close to their craft.")]],
    ["A plain lodge with an alert lamp over the door.", "A long lodge with small dark windows."], capacity="About 1,500 bunks.", m2_per_person=25)
MESS_HALL = canteen("hangar crews, 8,000 a shift", [R("Second dining hall", 1500, "Extra seats at peak times.")], style=1)
MEDICAL_CENTRE = ring(
    [("Ground floor", 5.5, 1), ("Clinical floor", 4.5, 1), ("Ward floor", 4.0, 2)],
    [[R("Crash trauma unit", 1500, "Treats crash and blast injuries."), R("Flight surgeons' clinic", 400, "Flight surgeons check pilots."),
      R("Imaging", 600, "Scanners."), WC, F("Treatment room", 30, "Treatment.")],
     [R("Operating theatre", 60, "Surgery.", 6), R("Intensive care", 600, "Critical care."), WC_STAFF, F("Lab", 60, "Tests.")],
     [R("Nurses' station", 40, "Nurses.", 2), WC, F("Ward bay", 40, "Four beds."), F("Single room", 20, "A single room.")]],
    ["A white medical centre with a red-edged roof and a lit trauma entrance."],
    capacity="120 beds.", m2_per_person=40)
FITNESS_HALL = ring(
    [("Sports floor", 9.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Reception", 60, "Book."), R("Changing rooms", 150, "Changing.", 2), WC, F("Gym room", 200, "Weights and machines.")],
     [R("G-force trainer room", 200, "A small centrifuge and g-suit trainer."), WC, F("Studio", 120, "Classes.")]],
    ["A big fitness hall with a glass wall onto its pool."],
    halls=[{"name": "Pool hall", "span": 2, "about": "A 50 m pool."}], capacity="About {people} crew.", m2_per_person=15)
MEMORIAL = garden("memorial garden for crews lost in action", [("Memorial lawn", 2, "A quiet lawn round the memorial."),
                                                               ("Reflecting pool", 1, "A still pool with the names of the lost.")], style=3)
COMMISSARY = ring([("Shop floor", 5.0, 1)],
                  [[R("Checkouts", 100, "Checkouts."), WC, F("|Grocery aisle|Toiletries aisle|Snacks aisle|Clothing aisle", 150, "Shelves of daily needs.")]],
                  ["A big plain shop with a lit sign."], capacity="About {people} shoppers.", m2_per_person=8)
KIT_STORE = ring([("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
                 [[R("Issue counter", 150, "Crews collect new kit."), R("Fitting room", 60, "Helmets and suits are fitted.", 4), WC, F("Kit store", 100, "Racks of kit.")],
                  [F("Kit store", 100, "Racks of kit.")]],
                 ["A grey store with a long issue counter."], capacity="About {people} staff.")
POLICE = ring([("Ground floor", 4.8, 1), ("Upper floor", 4.2, 1)],
              [[R("Front counter", 60, "Reports."), R("Custody suite", 150, "Cells."), R("Control room", 80, "Cameras."), LOCKERS, WC, F("Patrol room", 50, "Patrols.")],
               [R("Security office", 100, "Strike deck security."), KITCHENETTE, WC_STAFF, F("Offices", 30, "Offices.")]],
              ["A blue-trimmed security post with a lit sign."], court={"name": "Vehicle yard", "outdoor": True, "about": "Patrol cars."},
              capacity="About {people} officers.", m2_per_person=20)
COMMAND_GARDEN = garden("garden between the command buildings", [("Lunch lawn", 1, "Staff eat lunch here.")], style=0)
STAFF_OFFICES = ring([("Ground floor", 4.8, 1), ("Office floor", 4.2, (2, 3))],
                     [[RECEPTION, WC, F("Staff office", 50, "Wing staff."), F("Meeting room", 30, "Meetings.")],
                      [KITCHENETTE, WC_STAFF, F("Staff office", 50, "Wing staff."), F("Records room", 40, "Records.")]],
                     ["A plain office block in dark panels.", "An office block with a glass stair tower.", "A slim office block with purple trim."],
                     capacity="About {people} staff.")

PROGRAMS = [
    (r"^Crew Gate Hall$", CREW_GATE), (r"^Deck Lift Hall$", DECK_LIFT_HALL), (r"^Shift Lodge$", SHIFT_LODGE), (r"^Duty Rosters Office$", ROSTERS),
    (r"^Gate Canteen$", GATE_CANTEEN), (r"^Strike Hangars Clinic$", HANGARS_CLINIC), (r"^Prow Fire Station$", PROW_FIRE), (r"^Prow Garden$", PROW_GARDEN),
    (r"^Crew Garden", CREW_GARDEN), (r"^Gate Yard", GATE_YARD),
    (r"^Missile Magazine$", MISSILE_MAG), (r"^Torpedo Magazine$", TORPEDO_MAG), (r"^Cannon Round Store$", CANNON_STORE),
    (r"^Countermeasure Store$", COUNTERMEASURE), (r"^Bomb Store$", BOMB_STORE), (r"^Magazine Control$", MAG_CONTROL),
    (r"^Weapons Assembly Shop$", WEAPONS_ASSEMBLY), (r"^Armorers' Hall$", ARMORERS_HALL), (r"^Ordnance Test Range$", TEST_RANGE),
    (r"^Disposal Pit$", DISPOSAL_PIT), (r"^Loader Drone Depot$", DRONE_DEPOT), (r"^Propellant Tank Farm$", PROPELLANT), (r"^Fuel Cell Farm$", CELL_FARM),
    (r"^Fuel Control Room$", FUEL_CONTROL), (r"^Berm Park$", BERM_PARK), (r"^Armorers' Lodge$", ARMORERS_LODGE),
    (r"^Intercept Drone Racks$", DRONE_RACKS("intercept")), (r"^Strike Drone Racks$", DRONE_RACKS("strike")),
    (r"^Ordnance Fire Station$", ORDNANCE_FIRE), (r"^Ordnance Clinic$", ORDNANCE_CLINIC), (r"^Blast Berm", BLAST_BERM), (r"^Munitions Bunker", BUNKER),
    (r"^Launch Shafts", LAUNCH_SHAFTS), (r"^(Port|Starboard) Launch Control$", LAUNCH_CONTROL), (r"^Launch Queue Apron$", QUEUE_APRON),
    (r"^(Port|Starboard) Arming Apron$", ARMING_APRON), (r"^(Port|Starboard) Launch Ready Rooms$", READY_ROOMS),
    (r"^Shaft Maintenance Shop$", SHAFT_SHOP), (r"^Shaft Door Workshop$", SHAFT_SHOP), (r"^(Port|Starboard) Catapult Plant$", CATAPULT_PLANT),
    (r"^Port Wing Fire Station$", RACKS_FIRE("port launch wing", 1)), (r"^Starboard Wing Fire Station$", RACKS_FIRE("starboard launch wing", 3)),
    (r"^Launch Apron", LAUNCH_APRON), (r"^Recovery Apron$", RECOVERY_APRON), (r"^Damage Triage Bay$", TRIAGE),
    (r"^Rack Hall", RACK_HALL), (r"^\d\w\w Wing Ready Hall$", READY_HALL), (r"^(Port|Starboard) Rack Lift Control$", RACK_LIFT_CONTROL),
    (r"^(Port|Starboard) Taxi Apron$", TAXI_APRON_BIG), (r"^(Port|Starboard) Hangar Canteen$", HANGAR_CANTEEN),
    (r"^(Port|Starboard) Parts Store$", PARTS_STORE), (r"^(Port|Starboard) Crew Lockers$", CREW_LOCKERS),
    (r"^Port Racks Fire Station$", RACKS_FIRE("port", 0)), (r"^Starboard Racks Fire Station$", RACKS_FIRE("starboard", 2)),
    (r"^Open Bay", OPEN_BAY), (r"^Taxi Apron", TAXI_APRON), (r"^Craft Wash Hall$", WASH_HALL),
    (r"^Heavy Repair Hangar$", HEAVY_REPAIR), (r"^Rebuild Hangar$", REBUILD), (r"^Engine Shop$", ENGINE_SHOP), (r"^Engine Test Stand$", ENGINE_TEST),
    (r"^Airframe Shop$", AIRFRAME), (r"^Avionics Lab$", AVIONICS), (r"^Coatings Hall$", COATINGS), (r"^Craft Paint Hall$", PAINT_HALL),
    (r"^(Port|Starboard) Repair Parts Warehouse$", REPAIR_WAREHOUSE), (r"^Salvage Yard$", SALVAGE), (r"^Repair Crews' Hall$", REPAIR_CREWS),
    (r"^Port Yards Fire Station$", RACKS_FIRE("port repair yards", 1)), (r"^Starboard Yards Fire Station$", RACKS_FIRE("starboard repair yards", 0)),
    (r"^Work Yard", WORK_YARD), (r"^Parts Shed", PARTS_SHED), (r"^Weapons Fit Shop$", WEAPONS_FIT), (r"^Shield Calibration Hall$", SHIELD_HALL),
    (r"^Canopy and Seat Shop$", CANOPY_SHOP), (r"^Fuel Cell Shop$", CELL_SHOP), (r"^Drone Repair Bay$", DRONE_REPAIR), (r"^Tool and Gauge Store$", TOOL_STORE),
    (r"^Wing Command$", WING_COMMAND), (r"^Strike Operations Centre$", STRIKE_OPS), (r"^Intelligence Briefing Hall$", INTEL_BRIEFING),
    (r"^Squadron Leaders' Hall$", SQN_LEADERS), (r"^Mission Planning Rooms$", MISSION_PLANNING), (r"^Debrief Hall$", DEBRIEF_HALL),
    (r"^Space Conditions Office$", SPACE_CONDITIONS), (r"^Command Plaza$", COMMAND_PLAZA), (r"^Duty Crew Lodge", DUTY_LODGE),
    (r"^Hangar Mess Hall$", MESS_HALL), (r"^Hangar Medical Centre$", MEDICAL_CENTRE), (r"^Fitness Hall$", FITNESS_HALL),
    (r"^Wing Memorial Garden$", MEMORIAL), (r"^Hangar Commissary$", COMMISSARY), (r"^Uniform and Kit Store$", KIT_STORE),
    (r"^Hangar Police Post$", POLICE), (r"^Command Fire Station$", fire_station("Wing Command", [], ["Fire engine", "Rescue unit"], style=3)),
    (r"^Command Garden", COMMAND_GARDEN), (r"^Staff Offices", STAFF_OFFICES),
]

for _n, _st in {"Gate": 0, "Ordnance": 1, "Port Racks": 2, "Starboard Racks": 3, "Port Yards": 0, "Wing Command": 1, "Starboard Yards": 2}.items():
    _ex = {"Ordnance": [R("Magazine cooling room", 150, "Keeps the magazines cool.")],
           "Port Racks": [R("Rack power room", 200, "Power for the rack lifts.")], "Starboard Racks": [R("Rack power room", 200, "Power for the rack lifts.")]}.get(_n, [])
    PROGRAMS.append((r"^%s Utility Plant$" % _n, utility_plant(_n, _ex, style=_st)))
for _n, _st in {"Gate": 1, "Ordnance": 2, "Port Launch": 3, "Starboard Launch": 0, "Port Racks": 1, "Starboard Racks": 2, "Port Yards": 3,
                "Wing Command": 0, "Starboard Yards": 1}.items():
    PROGRAMS.append((r"^%s Service Shaft$" % _n, service_shaft(_n, style=_st)))

# More fill types for the biggest floors, so they don't repeat one room hundreds of times
_MORE = [
    (AIRFRAME, 1, [F("Planning office", 50, "Plans each frame repair."), F("Composite repair room", 80, "Repairs composite skin panels.")]),
    (COATINGS, 0, [F("Masking room", 80, "Craft are masked before spraying."), F("Inspection booth", 60, "Coatings are checked for thickness.")]),
    (COATINGS, 1, [F("Filter room", 60, "Filters for the spray booths.")]),
    (PAINT_HALL, 0, [F("Masking room", 60, "Craft are masked before painting.")]),
    (SHIELD_HALL, 1, [F("Test data room", 50, "Stores shield test results."), F("Training room", 60, "Technicians learn shield tuning.")]),
    (DEBRIEF_HALL, 0, [F("Intelligence debrief room", 40, "Intelligence officers question crews about what they saw.")]),
    (DEBRIEF_HALL, 1, [F("Report writing room", 40, "Crews write up their flight reports.")]),
    (HANGARS_CLINIC, 0, [F("Treatment room", 30, "Dressings and injuries."), F("Eye test room", 30, "Pilots' eyesight checks.")]),
    (ORDNANCE_CLINIC, 0, [F("Treatment room", 30, "Dressings and burns.")]),
    (ARMORERS_HALL, 1, [F("Weapons manual library", 60, "Manuals for every weapon.")]),
    (ROSTERS, 1, [F("Meeting room", 40, "Meetings with squadrons.")]),
    (WING_COMMAND, 2, [F("Planning room", 80, "Senior staff planning."), F("Briefing room", 60, "Briefings for senior officers.")]),
]
for _p, _i, _rows in _MORE:
    if not callable(_p["rooms"][_i]):
        _p["rooms"][_i] = list(_p["rooms"][_i]) + _rows
