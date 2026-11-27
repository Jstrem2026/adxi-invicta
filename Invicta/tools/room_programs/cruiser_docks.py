"""Room programs for the Cruiser Docks (Deck 5 Aerion), written 27 Nov 2026. See tools/design_rooms.py.

The six escort cruisers (canon 2,000 x 420 m) berth nose first behind the three Cruiser Gates in the
starboard hull. Everything here serves them: stores, fuel, munitions, repairs, and their crews ashore.
"""
from .common import (R, F, WC, WC_STAFF, CLEAN, COMMS, PLANT, KITCHENETTE, PRAYER, FIRST_AID, RECEPTION,
                     LOCKERS, BREAK, SECURITY, utility_plant, service_shaft, fire_station, clinic, canteen, garden,
                     LIGHT_COURT, shed, offices)

# ------------------------------------------------------------------ P1 Cruiser Gates

def berths(gate):
    def zones(ctx):
        cabin = [{"size": (20, 10), "rooms": [("Berth control cabin", 2, "The berth master watches the cruiser's mooring arms, power and hoses from here."),
                                               ("Line handlers' shelter", 1, "Shelter and kit for the crew who make the cruiser fast.")]}]
        apron = [{"size": (30, 12), "rooms": [("Shore connection house", 2, "Where shore power, water, air and data cables plug into the cruiser."),
                                               ("Fuel valve house", 1, "Valves that open the fuel line from the fuel farm to the cruiser.")]}]
        a, b = ("%sA" % gate, "%sB" % gate)
        return [
            ("Berth %s" % a, 4, "A berth for one 2 km escort cruiser, which docks nose first towards Cruiser Gate %d, "
                                 "held by mooring arms along both sides." % gate, cabin,
             [("Mooring arms", "Hydraulic arms that grip the cruiser's hull and hold it steady.", (0.02, 0.1, 0.04, 0.8))]),
            ("Service apron", 1, "The strip between the two berths, with shore connections, fuel valves and the gangway towers.", apron,
             [("Gangway towers", "Towers with telescopic gangways that reach the cruisers' crew hatches.", (0.3, 0.45, 0.4, 0.1))]),
            ("Berth %s" % b, 4, "The second berth behind Cruiser Gate %d, for another escort cruiser." % gate, cabin,
             [("Mooring arms", "Hydraulic arms that grip the cruiser's hull and hold it steady.", (0.94, 0.1, 0.04, 0.8))]),
        ]
    return {
        "mode": "yard",
        "floors": [("Berth floor", 4.0, 1)],
        "height_extra": 0.0,
        "zones": zones,
        "split": "across",
        "edge": ("Berth edge walkway", "A railed walkway round the berths, used by line handlers and inspectors."),
        "floors_text": "Two open berths; cabins and gangway towers",
        "structure": "Reinforced deck floor with mooring-arm foundations, fuel, power and water lines in trenches.",
        "look": ["Two cavernous open berths, each long enough for a 2 km cruiser, lined with yellow mooring arms and "
                 "floodlit gangway towers, opening onto the dark gate in the hull.",
                 "A pair of vast floodlit berths with striped edges and rows of mooring arms, the gate's huge doors at one end."],
        "entrances": "Cruiser Gate %d for the cruisers; gangways from the Gangway Hall; service roads at the ends." % gate,
        "capacity": "Two escort cruisers.",
        "services": "Shore power, water, air and data at each berth; fuel from the Cruiser Fuel Farm.",
        "m2_per_person": 4000,
    }


def supply_quay(gates):
    return {
        "mode": "yard",
        "floors": [("Quay floor", 4.0, 1)],
        "height_extra": 30.0,
        "zones": [
            ("Crane rail", 2, "Rails for the big gantry cranes that swing stores across into the cruisers at Gates %s." % gates, [],
             [("Gantry cranes", "Tall gantry cranes that lift loads into the cruisers' cargo hatches.", (0.1, 0.2, 0.8, 0.3))]),
            ("Loading lanes", 3, "Lanes where loaders drop pallets and containers under the cranes.",
             [{"size": (18, 10), "rooms": [("Crane control room", 2, "The crane drivers' supervisor plans each lift here."),
                                           ("Riggers' room", 1, "Slings, chains and kit for the crew who hook up the loads.")]}]),
            ("Marshalling area", 2, "Loads wait here in the order they will go aboard."),
            ("Haul road", 1, "The road that brings loads from the Fleet Stores and Dock Freight."),
        ],
        "edge": ("Safety line", "A painted safety line and barrier round the working quay."),
        "floors_text": "Open quay; crane rails and a small control room",
        "structure": "Heavy-duty deck floor with crane rails set into it.",
        "look": "A long floodlit quay of yellow gantry cranes on rails, with pallets and containers lined up underneath.",
        "entrances": "Haul road at each end; walkways from the berths.",
        "capacity": "About 10 gantry cranes working at once.",
        "services": "Crane power rails, floodlights.",
        "m2_per_person": 3000,
    }


GATE_CONTROL = {
    "mode": "ring",
    "floors": [("Equipment floor", 5.0, 1), ("Gate control floor", 7.0, 1), ("Support floor", 4.2, 1)],
    "wing": 24,
    "hall_max_m2": 12000,
    "court": LIGHT_COURT,
    "halls": [{"name": "Gate control room", "span": 2,
               "about": "Controllers open and close the three Cruiser Gates and guide each cruiser in and out of its berth.",
               "inside": [{"name": "Gate status wall", "about": "Screens showing each gate's doors, air seals and the cruisers in the berths.",
                           "at": (0.05, 0.05, 0.9, 0.08)}]}],
    "rooms": [
        [R("Gate machinery control", 200, "Controls the motors, locks and seals of the three huge hull gates."),
         R("Air seal monitoring room", 120, "Watches the force fields and seals that keep the deck's air in while a gate is open."),
         R("Equipment room", 250, "Computers and radios for gate control."), R("Battery room", 120, "Keeps the gates working through any power failure."),
         R("Security entrance", 60, "Staff are checked in."), LOCKERS, WC_STAFF, F("Engineers' room", 60, "Gate engineers on call.")],
        [R("Berth movement desk", 80, "Plans each cruiser's arrival and departure with Starboard Approach Control."),
         R("Watch officer's office", 30, "The officer in charge of the watch."), KITCHENETTE, WC_STAFF,
         F("Pilots' room", 40, "Berthing pilots who board each cruiser to bring it in.")],
        [R("Rest room", 15, "Bunks for the night watch.", 6), R("Training room", 60, "Gate controllers practise emergency closures."),
         KITCHENETTE, WC_STAFF, F("Offices", 30, "Offices for managers and planners."),
         F("Records room", 40, "Logs of every gate opening and every cruiser movement.")],
    ],
    "structure": "Hardened concrete frame with blast glazing facing the berths.",
    "look": "A long low control block with a band of blue-lit windows looking out over the three berths.",
    "entrances": "Secure staff entrance.",
    "capacity": "About {people} staff over three watches.",
    "services": "Duplicate power and data links to the gates and Starboard Approach Control.",
    "m2_per_person": 25,
}

GANGWAY_HALL = {
    "mode": "ring",
    "floors": [("Concourse floor", 7.0, 1), ("Gangway floor", 5.0, 1)],
    "wing": 26,
    "hall_max_m2": 15000,
    "court": LIGHT_COURT,
    "halls": [{"name": "Crew concourse", "span": 2,
               "about": "A tall concourse where cruiser crews gather before going aboard and stream through when they come ashore.",
               "inside": [{"name": "Departures board", "about": "Shows which cruiser is boarding, from which gangway, and when.",
                           "at": (0.1, 0.05, 0.8, 0.06)}]}],
    "rooms": [
        [R("Crew check-in desks", 150, "Crew show their papers and are checked aboard or ashore."),
         R("Baggage room", 200, "Sea bags are weighed and loaded on carts to the gangways."), R("Waiting lounge", 300, "Seats for crews waiting to board."),
         R("Security screening", 200, "Scanners for everyone going aboard."), WC, FIRST_AID,
         F("Gangway gate", 60, "A gate leading to one gangway tower and a cruiser's hatch."),
         F("Family farewell room", 50, "A quiet room where crews say goodbye to their families.")],
        [R("Gangway control room", 60, "Moves the telescopic gangways into place."),
         R("Crew records office", 80, "Updates every cruiser's crew list."), KITCHENETTE, WC_STAFF,
         F("Gangway bridge", 80, "A covered bridge from the hall towards the gangway towers.")],
    ],
    "structure": "Steel and glass concourse on a concrete base.",
    "look": "A long glass hall with a sweeping roof and covered bridges reaching out to the berths.",
    "entrances": "Street entrance from the Quay Pod Stop; bridges to the gangway towers.",
    "capacity": "About 4,000 crew passing through in a crew change.",
    "services": "Scanners, baggage carts, departures boards.",
    "m2_per_person": 5,
}

FLEET_INSPECTORS = offices(
    [R("Inspection desk", 120, "Inspectors book each cruiser's arrival and departure checks."),
     R("Hull survey room", 100, "Reviews scans of each cruiser's hull for damage."), RECEPTION, WC,
     F("Inspectors' office", 40, "An inspector's desk and files."), F("Kit room", 30, "Inspection tools, scanners and suits.")],
    [R("Certificates office", 80, "Issues the papers that say a cruiser is fit to sail."), R("Meeting room", 40, "Meetings with cruiser officers.", 3),
     KITCHENETTE, WC_STAFF, F("Inspectors' office", 40, "An inspector's desk and files."),
     F("Reports room", 50, "Inspectors write up each cruiser's condition.")],
    "A plain purple-trimmed office facing the berths, with an inspection gallery along its front.", floors=(1, 2))

GANGWAY_CANTEEN = canteen("cruiser crews coming ashore", [R("First-meal counter", 60, "Fresh food for crews just off a long patrol."),
                                                          R("Crew bar", 120, "A bar for crews on their first night ashore.")], style=1)

BERTHS_FIRE = fire_station("the cruiser berths", [R("Foam store", 120, "Foam for fuel fires on a cruiser or at the berth."),
                                                  R("Shipboard firefighting kit room", 80, "Breathing sets and hoses for fighting fires inside a cruiser.")],
                           ["Fire engine", "Foam tender", "Foam tender", "Rescue unit", "Heavy rescue unit"], style=3)

BERTH_PLANT = utility_plant("the cruiser berths", [R("Shore power hall", 300, "Converters that feed shore power into a docked cruiser so it can shut its engines down."),
                                                   R("Water and air pump room", 200, "Pumps fresh water and air into the cruisers.")], style=2)


def quay_yard(ctx):
    rng = ctx["rng"]
    pool = [("Container stacks", 3, "Containers of stores stacked three high, waiting to go aboard."),
            ("Pallet rows", 2, "Pallets of food, water and spares in long rows."),
            ("Crane lane", 2, "A lane under the mobile cranes that load the haulers."),
            ("Bulk tanks", 1, "Small tanks of oils and coolants for the cruisers."),
            ("Empty returns", 1, "Empty containers back from the cruisers, waiting to be cleaned."),
            ("Parts crates", 1, "Crates of repair parts for the cruisers.")]
    rng.shuffle(pool)
    hut = [{"size": (14, 8), "rooms": [("Yard office", 2, "The yard foreman tracks every load in the yard."),
                                       ("Checkers' hut", 1, "Checkers scan each load in and out.")]}]
    return [(pool[0][0], pool[0][1], pool[0][2], hut)] + pool[1:rng.randint(3, 5)] + [("Haul lane", 1, "The lane the haulers use through the yard.")]


QUAY_YARD = {
    "mode": "yard",
    "floors": [("Yard", 4.0, 1)],
    "height_extra": 14.0,
    "zones": quay_yard,
    "edge": ("Yard fence", "A fence and gate round the yard."),
    "floors_text": "Open yard; a small yard office",
    "structure": "Heavy-duty deck floor with tie-down points.",
    "look": ["An open quay yard of stacked containers in rust red and grey, with a mobile crane among them.",
             "A floodlit yard of pallets and crates in neat rows, crossed by haul lanes.",
             "A yard of container stacks and parts crates, with yellow cranes and blue floodlights."],
    "entrances": "Gates for haulers at each end.",
    "capacity": "Stores waiting to be loaded into the cruisers.",
    "services": "Floodlights, power points for refrigerated containers.",
    "m2_per_person": 5000,
}

# ------------------------------------------------------------------ P2 Fleet Stores

MAGAZINE = {
    "mode": "hall",
    "floors": [("Magazine floor", 10.0, 1), ("Deep magazine", 8.0, 1, "below")],
    "support": 24,
    "halls": [{"name": "Munitions vaults", "span": 1,
               "about": "Separate armoured vaults for the cruisers' shells and missiles, with blast walls between them so a fire in one cannot spread.",
               "bays": {"name": "Munitions vault", "width": 40, "max": 14,
                        "about": "One armoured vault with racks of shells or missiles, its own fire suppression and a blast door."}}],
    "rooms": [
        [R("Armoured entrance", 80, "Two checks and a blast door; only cleared staff enter."),
         R("Issue room", 150, "Munitions are signed out here for each cruiser and loaded on armoured carts."),
         R("Inspection bay", 200, "Every shell and missile is checked before it goes aboard."),
         R("Magazine control room", 80, "Watches temperature, smoke and doors in every vault."),
         R("Suppression plant room", 150, "Water deluge and gas systems that drown a vault in seconds."), LOCKERS, WC_STAFF,
         F("Armourers' workshop", 80, "Armourers service fuzes and missile parts.")],
        [R("Deep vault", 400, "The deepest vault, for the most dangerous warheads."), R("Lift lobby", 60, "Armoured lifts between the vaults."),
         F("Overflow vault", 300, "Extra vault space below the deck.")],
    ],
    "structure": "Heavy reinforced concrete vaults with blast walls and vent panels that blow outward, away from people.",
    "look": "A low, heavy block of earth-covered concrete with blast-vent panels along the roof and red warning lights at every door.",
    "entrances": "Armoured cart doors to the haul road; one staff entrance.",
    "capacity": "Shells and missiles for the six escort cruisers.",
    "services": "Deluge fire suppression, temperature control, blast vents.",
    "m2_per_person": 1000,
}

FUEL_FARM = {
    "mode": "yard",
    "floors": [("Tank floor", 4.0, 1)],
    "height_extra": 26.0,
    "zones": [
        ("Fuel tanks", 5, "Rows of tall tanks holding the cruisers' fuel, each inside a bunded wall to catch any spill.",
         [{"size": (24, 12), "rooms": [("Pump house", 2, "Pumps that push fuel down the pipe to the berths."),
                                       ("Farm control room", 1, "Operators watch every tank's level, pressure and temperature.")]}],
         [("Tank row", "Tall white fuel tanks in a bunded enclosure.", (0.1, 0.1, 0.8, 0.7))]),
        ("Pipe rack", 1, "Raised racks carrying fuel pipes to the berths."),
        ("Fire water ring", 1, "Fire hydrants and foam monitors round the tanks."),
        ("Tanker bay", 1, "Bays where fuel arrives by tanker train from the Keelway."),
    ],
    "edge": ("Fire break", "A clear strip round the fuel farm, kept empty in case of fire."),
    "floors_text": "Open tank farm; a pump house",
    "structure": "Steel tanks on concrete pads inside bund walls.",
    "look": "Rows of tall white fuel tanks behind bund walls, laced with silver pipe racks and lit by orange floodlights.",
    "entrances": "Tanker gate; staff gate.",
    "capacity": "Fuel for the six escort cruisers.",
    "services": "Foam fire protection, gas detectors, pipeline to the berths.",
    "m2_per_person": 5000,
}

STORES_WAREHOUSE = shed(
    "Warehouse floor", "Racks of food, water, clothing and supplies for cruiser crews, picked and packed for each cruiser.",
    "Rack aisle", "An aisle of tall racks served by robot pickers.", 40,
    [R("Goods in", 300, "Lorries unload here and goods are checked against the order."),
     R("Goods out", 300, "Packed loads wait for the haulers to the quays."),
     R("Packing hall", 400, "Supplies are packed by cruiser and by deck."), R("Warehouse office", 120, "Plans picking and loading."),
     LOCKERS, BREAK, WC_STAFF, F("Pallet store", 120, "Empty pallets and packing.")],
    [R("Robot control room", 80, "Controls the robot pickers."), KITCHENETTE, F("Inspection gallery", 60, "A walkway above the racks.")],
    ["A huge grey warehouse with a row of loading docks down one side and the fleet's badge on its end wall.",
     "A long warehouse with blue loading doors and a lit 'Fleet Stores' sign."], h=18.0)

REPAIR_PARTS = shed(
    "Parts store", "Racks and cradles of repair parts for the cruisers, made in the Ferrum foundries on Deck 8 and sent up by freight lift.",
    "Parts bay", "A bay of racks or cradles for one kind of part: pumps, plates, cables or engine pieces.", 40,
    [R("Freight lift landing", 300, "Parts arrive from Deck 8 on the Freight Lift to Ferrum."),
     R("Receiving and checking", 300, "Each part is checked against the order and its test papers."),
     R("Heavy parts cradle area", 400, "Cradles for the biggest parts, moved by overhead crane."),
     R("Parts office", 100, "Tracks every part and which cruiser it is for."), LOCKERS, WC_STAFF, F("Small parts cage", 80, "Locked cages of small, costly parts.")],
    [R("Ferrum liaison office", 60, "Orders parts from the Deck 8 foundries."), KITCHENETTE, F("Records room", 50, "Part test papers and histories.")],
    ["A tall steel depot with overhead crane rails visible through clerestory windows.",
     "A grey parts depot with heavy roller doors facing the freight lift."], h=20.0)

STORES_CONTROL = offices(
    [R("Stock control room", 200, "A wall of screens showing every item in the Fleet Stores."), RECEPTION, WC,
     F("Planners' office", 60, "Planners who work out how each cruiser is loaded, deck by deck.")],
    [R("Load planning room", 120, "Works out the order loads go aboard so the cruiser stays balanced."),
     KITCHENETTE, WC_STAFF, F("Planners' office", 60, "Planners who work out how each cruiser is loaded, deck by deck."),
     F("Orders office", 50, "Orders new stock from the rest of the ship.")],
    "A narrow office block with a long strip window and the stock wall glowing inside.", floors=(1, 2))

LOADERS_HALL = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    "wing": 24,
    "court": LIGHT_COURT,
    "hall_max_m2": 8000,
    "halls": [{"name": "Loaders' canteen", "span": 1, "about": "A big canteen where loaders eat between shifts."}],
    "rooms": [
        [R("Shift board", 60, "Shows which crew loads which cruiser today."), R("Kitchen", 200, "Cooks for the canteen."),
         R("Kit store", 150, "Hard hats, gloves, hi-vis and radios."), WC_STAFF,
         F("Locker room", 90, "Lockers and showers for loaders."), F("Drying room", 40, "Dries wet work clothes.")],
        [R("Union office", 60, "The loaders' union rep."), R("Training room", 80, "Safety and forklift training."), KITCHENETTE,
         F("Rest room", 50, "Quiet room with recliners for loaders on long shifts.")],
    ],
    "structure": "Concrete frame.",
    "look": "A plain two-storey hall with steamy kitchen vents and a lit shift board by the door.",
    "entrances": "Staff entrance from the yards.",
    "capacity": "About {people} loaders at a shift change.",
    "services": "Showers, kitchen extraction.",
    "m2_per_person": 10,
}

STORES_FIRE = fire_station("the Fleet Stores", [R("Magazine fire plan room", 50, "Plans for fighting a fire near the munitions magazine."),
                                                R("Hazmat kit room", 60, "Suits and kit for leaks of fuel and chemicals.")],
                           ["Fire engine", "Foam tender", "Hazmat unit"], style=0)


def stores_shed_support(ctx):
    rng = ctx["rng"]
    return [R("Loading docks", 200, "Lorry docks where goods arrive and leave."), R("Shed office", 50, "The shed supervisor's office."), WC_STAFF] + \
        rng.sample([R("Chilled room", 200, "Chilled stores for fresh food."), R("Clothing store", 150, "Uniforms and boots for the crews."),
                    R("Medical stores", 120, "Medicines and first-aid kits for the cruisers' sick bays."),
                    R("Spirits and stores cage", 80, "A locked cage for valuable items."),
                    R("Battery charging room", 80, "Charges the forklifts.")], 2) + [F("Pallet store", 100, "Empty pallets and wrap.")]


STORES_SHED = shed(
    "Store floor", "A covered store where fleet supplies wait under cover until they are loaded.",
    "Storage bay", "A bay of racks or floor stacks.", 36,
    stores_shed_support, [KITCHENETTE, F("Mezzanine store", 80, "Light goods on a mezzanine.")],
    ["A plain grey shed with blue roller doors.", "A long steel shed with translucent roof panels.",
     "A ribbed metal shed with a yellow-striped dock edge."], h=12.0)


def stores_yard(ctx):
    rng = ctx["rng"]
    pool = [("Pallet stacks", 3, "Pallets of tinned and dried food in long rows."), ("Water containers", 2, "Containers of drinking water."),
            ("Spares crates", 2, "Crates of general spares."), ("Container rows", 2, "Containers of mixed stores."),
            ("Empties", 1, "Empty containers waiting to go back.")]
    rng.shuffle(pool)
    return [pool[0] + ([{"size": (12, 8), "rooms": [("Yard hut", 1, "The yard checker's hut.")]}],)] + pool[1:rng.randint(3, 4)] + \
        [("Forklift lane", 1, "A lane for forklifts and haulers.")]


STORES_YARD = dict(QUAY_YARD, zones=stores_yard, height_extra=10.0,
                   look=["An open yard of pallets and containers in neat rows.", "A yard of stacked water containers and crates under floodlights."],
                   capacity="Fleet stores stacked in the open.")

# ------------------------------------------------------------------ P3 Cruiser Repair Yards

MODULE_REPAIR_HALL = shed(
    "Module repair hall", "A vast hall where engines, turrets and shield modules lifted out of the cruisers are stripped, repaired and tested.",
    "Repair bay", "One bay with a module on its cradle, an overhead crane and test connections.", 70,
    [R("Module receiving bay", 600, "Heavy transporters bring modules in from the berths."),
     R("Strip-down area", 800, "Modules are taken apart and every part is cleaned and checked."),
     R("Test cell control room", 120, "Engineers run repaired modules on test before they go back."),
     R("Tool crib", 120, "Tools and lifting gear signed out to the fitters."), LOCKERS, BREAK, WC_STAFF,
     F("Fitters' workshop", 150, "Benches and machines for repairing parts.")],
    [R("Engineering office", 200, "Engineers plan each repair."), R("Quality office", 80, "Signs off each repaired module."), KITCHENETTE,
     F("Crane gallery", 80, "A walkway along the crane rails for maintenance.")],
    ["A colossal repair hall with a sawtooth roof, giant doors and overhead cranes visible through its high windows.",
     "A huge steel-grey hall with orange crane girders and the glow of welding inside."], h=40.0, support_w=30,
    extra_halls=[{"name": "Engine test cell", "span": 1, "share": 0.15,
                  "about": "A sealed, soundproofed cell where repaired engine modules are run at full power."}])

TURRET_SHOP = shed(
    "Turret floor", "Cruiser turrets are rebuilt here: barrels relined, mounts and motors overhauled.",
    "Turret bay", "One turret on a rotating stand, with cranes and power to turn it.", 50,
    [R("Barrel shop", 400, "Long lathes reline and check the gun barrels."), R("Mount and motor shop", 300, "Overhauls the motors that turn and aim each turret."),
     R("Fire control lab", 150, "Tests the turret's aiming computers."), LOCKERS, WC_STAFF, F("Fitters' workshop", 120, "Benches for repairs.")],
    [R("Engineers' office", 100, "Plans turret repairs."), KITCHENETTE, F("Spares store", 80, "Turret spares.")],
    ["A tall dark shop with a blast-proof test range wall at one end and a red firing light over its door."], h=30.0,
    extra_halls=[{"name": "Test-firing range", "span": 1, "share": 0.25,
                  "about": "An armoured range where rebuilt turrets are test-fired into a shock-absorbing backstop."}])

ENGINE_SHOP = shed(
    "Engine floor", "Cruiser engine modules are overhauled here, from fuel pumps to the main thrust chambers.",
    "Engine bay", "One engine module on a cradle with test connections.", 60,
    [R("Combustion chamber shop", 400, "Repairs and recoats the thrust chambers."), R("Pump and valve shop", 250, "Overhauls fuel pumps and valves."),
     R("Clean room", 150, "Dust-free room for precision parts."), R("Test control room", 100, "Runs engines on the test cell."), LOCKERS, WC_STAFF,
     F("Fitters' workshop", 120, "Benches for repairs.")],
    [R("Engineers' office", 120, "Plans engine overhauls."), KITCHENETTE, F("Records room", 50, "Engine logbooks.")],
    ["A long steel shop with exhaust stacks over its test cell and heavy doors on the haul road."], h=30.0,
    extra_halls=[{"name": "Engine test cell", "span": 1, "share": 0.2, "about": "A soundproofed cell where engines are run at full power."}])

HULL_PLATE_STORE = shed(
    "Plate store", "Racks of Void Ore armour plates, the cruisers' hull material, stored flat and moved by magnetic cranes.",
    "Plate rack", "A rack of armour plates of one size and thickness.", 40,
    [R("Cutting shop", 400, "Plates are cut and shaped to fit a damaged section of hull."), R("Plate inspection room", 150, "Each plate is scanned for flaws."),
     R("Store office", 80, "Tracks every plate."), LOCKERS, WC_STAFF, F("Offcuts store", 80, "Offcuts kept for small patches.")],
    [KITCHENETTE, F("Crane gallery", 60, "Walkway along the crane rails.")],
    ["A heavy steel store with magnetic crane rails and a dark, plated façade."], h=18.0)

SHIELD_LAB = {
    "mode": "ring",
    "floors": [("Lab floor", 6.0, 1), ("Upper lab floor", 4.5, 1)],
    "wing": 24,
    "court": LIGHT_COURT,
    "hall_max_m2": 10000,
    "halls": [{"name": "Shield test chamber", "span": 2,
               "about": "A screened chamber where shield emitters are switched on at full strength and tuned."}],
    "rooms": [
        [R("Emitter workshop", 300, "Shield emitters are repaired and rebuilt."), R("Tuning lab", 200, "Fine-tunes each emitter's field."),
         R("Power test room", 150, "Feeds emitters their full power on test."), R("Clean room", 120, "Dust-free assembly."), LOCKERS, WC_STAFF,
         F("Lab", 80, "A lab bench room for one test team.")],
        [R("Scientists' office", 100, "Physicists who study shield faults."), R("Data room", 80, "Stores every test result."), KITCHENETTE, WC_STAFF,
         F("Lab", 80, "A lab bench room for one test team.")],
    ],
    "structure": "Concrete frame with a screened test chamber.",
    "look": "A smooth white lab block with a faint blue glow from the test chamber's high windows.",
    "entrances": "Staff entrance; equipment door.",
    "capacity": "About {people} scientists and technicians.",
    "services": "Heavy power feed, screening, cooling.",
    "m2_per_person": 40,
}

CRANE_DEPOT = shed(
    "Crane shed", "The yards' mobile cranes park here between jobs and are serviced.",
    "Crane bay", "One mobile crane's bay, with a service pit.", 30,
    [R("Crane workshop", 300, "Repairs crane engines, booms and cables."), R("Crane dispatch office", 60, "Sends cranes to each job."),
     R("Rope and rigging store", 150, "Wire ropes, hooks and slings."), LOCKERS, WC_STAFF, F("Parts store", 80, "Crane parts.")],
    [R("Drivers' room", 80, "Crane drivers wait for their next job."), KITCHENETTE, F("Offices", 30, "Offices.")],
    ["A tall shed with yellow crane booms poking out of its open doors."], h=22.0)

INSPECTORS_HALL = offices(
    [R("Materials test lab", 300, "Tests metal samples from repairs for strength."), R("Weld inspection lab", 200, "X-rays and scans every weld."),
     R("Pressure test room", 150, "Tests repaired pipes and tanks under pressure."), RECEPTION, WC,
     F("Inspectors' office", 40, "An inspector's desk and files.")],
    [R("Sign-off office", 80, "Signs off finished repairs."), KITCHENETTE, WC_STAFF, F("Inspectors' office", 40, "An inspector's desk and files."),
     F("Report room", 50, "Writes up inspections.")],
    "A grey office and lab block with test-rig yards behind it.", floors=(1, 2))

DOCKSIDE_PARK = garden("park beside Dockside station", [("Station lawn", 2, "A lawn where travellers wait for their train."),
                                                         ("Crane view terrace", 1, "A raised terrace looking out over the repair yards' cranes.")], style=1)


def module_yard(ctx):
    rng = ctx["rng"]
    pool = [("Engine modules", 3, "Engine modules on cradles, waiting for a bay in the repair hall."),
            ("Turret mounts", 2, "Turrets waiting to go into the turret shop."),
            ("Shield modules", 2, "Shield emitters waiting for the lab, covered against dust."),
            ("Repaired modules", 2, "Repaired modules waiting to go back to their cruisers."),
            ("Scrap bay", 1, "Parts beyond repair, waiting to go back to Ferrum for melting.")]
    rng.shuffle(pool)
    return [pool[0] + ([{"size": (14, 8), "rooms": [("Yard office", 2, "Tracks every module in the yard."),
                                                     ("Riggers' hut", 1, "Riggers' kit and shelter.")]}],)] + pool[1:rng.randint(3, 5)] + \
        [("Transporter lane", 1, "The lane for the heavy transporters that carry modules.")]


MODULE_YARD = dict(QUAY_YARD, zones=module_yard, height_extra=16.0,
                   look=["An open yard of huge engine and turret modules on cradles, under floodlights.",
                         "A yard of tarpaulin-covered modules in rows, with a heavy transporter among them."],
                   capacity="Cruiser modules waiting for repair or return.")


def repair_shed_support(ctx):
    rng = ctx["rng"]
    return [R("Shed office", 60, "The foreman plans the shed's work."), LOCKERS, WC_STAFF] + rng.sample([
        R("Welding shop", 200, "Welding bays with fume extraction."), R("Machine shop", 250, "Lathes and mills for making parts."),
        R("Paint and coating booth", 200, "Sprays protective coatings."), R("Pipe shop", 150, "Bends and fits pipes."),
        R("Electrical shop", 150, "Repairs cables, motors and boards."), R("Hydraulics shop", 150, "Repairs pumps, rams and valves.")], 3) + \
        [F("Fitters' workshop", 120, "Benches for general repairs.")]


REPAIR_SHED = shed(
    "Workshop floor", "A covered workshop for cruiser repairs too small for the Module Repair Hall.",
    "Work bay", "A bay with an overhead crane and a workbench line.", 40,
    repair_shed_support, [KITCHENETTE, F("Stores mezzanine", 80, "Parts on a mezzanine.")],
    ["A long steel shed with a sawtooth roof and orange crane rails inside.", "A grey workshop with tall doors and welding glow in its windows.",
     "A ribbed metal shed with a row of roof vents and a lit bay number on each door."], h=16.0)

# ------------------------------------------------------------------ P4 Dock Freight

CONTAINER_YARD = {
    "mode": "yard",
    "floors": [("Yard", 4.0, 1)],
    "height_extra": 20.0,
    "zones": [
        ("Container stacks", 5, "Rows of containers stacked five high, sorted by which cruiser they are going to.",
         [{"size": (24, 12), "rooms": [("Yard control room", 2, "Plans where every container goes in the stacks."),
                                       ("Drivers' room", 1, "Straddle carrier drivers wait between moves.")]}]),
        ("Straddle carrier lanes", 2, "Lanes for the straddle carriers that lift and move containers."),
        ("Refrigerated rows", 1, "Plug-in points for refrigerated containers of fresh food."),
        ("Train transfer area", 1, "Where containers come off the freight trains from the Keelway Freight Siding."),
    ],
    "edge": ("Yard fence", "A fence and gates round the yard."),
    "floors_text": "Open container yard; a control room",
    "structure": "Heavy-duty deck floor.",
    "look": "A sea of stacked containers in red, blue and grey, crossed by straddle carriers under tall floodlight masts.",
    "entrances": "Gates to the freight siding and the haul roads.",
    "capacity": "Thousands of containers in transit.",
    "services": "Floodlights, power for refrigerated containers.",
    "m2_per_person": 5000,
}

BONDED = shed(
    "Bonded store", "A locked store for goods that have not yet passed inspection; nothing leaves until it is cleared.",
    "Bonded bay", "A caged bay of goods held for one shipper.", 36,
    [R("Customs desk", 100, "Officers check papers for every load."), R("Examination bay", 300, "Goods are opened and examined."),
     R("Seized goods cage", 100, "Goods that failed inspection."), R("Security room", 50, "Cameras on every bay."), LOCKERS, WC_STAFF,
     F("Agents' office", 40, "Desks for shipping agents waiting for clearance.")],
    [KITCHENETTE, F("Records room", 50, "Papers for every held load.")],
    ["A grey warehouse with caged bays and a guarded gate."], h=12.0)

COLD_STORE = shed(
    "Cold store", "Freezers and chillers holding food for the cruiser crews.",
    "Freezer room", "A freezer room held at -13 °F (-25 °C).", 36,
    [R("Chilled dock", 300, "A cooled loading dock so food never warms up."), R("Refrigeration plant", 300, "Compressors that keep the rooms cold."),
     R("Blast freezer", 120, "Freezes fresh food quickly."), R("Food quality lab", 60, "Checks food is safe."), LOCKERS, WC_STAFF,
     F("Chiller room", 100, "A chiller room held at 39 °F (4 °C) for fresh food.")],
    [R("Plant control room", 50, "Watches every room's temperature."), KITCHENETTE, F("Plant gallery", 60, "Access to the cooling plant.")],
    ["A windowless white insulated box with frost-rimmed loading doors."], h=14.0)

LOADERS_DEPOT = shed(
    "Vehicle hall", "Loader vehicles and hauler drones park, charge and get serviced here.",
    "Vehicle bay", "A row of charging points for loaders or drones.", 30,
    [R("Drone control room", 120, "Controls the hauler drones."), R("Vehicle workshop", 300, "Repairs loaders and drones."),
     R("Battery room", 200, "Swaps and charges batteries."), LOCKERS, WC_STAFF, F("Parts store", 80, "Vehicle parts.")],
    [R("Drivers' room", 100, "Drivers wait for their next load."), KITCHENETTE, F("Offices", 30, "Offices.")],
    ["A long shed with rows of charging lights and drones parked on its roof."], h=10.0)

INSPECTION_SHED = shed(
    "Inspection hall", "Every load bound for the fleet is scanned and checked here.",
    "Scanning lane", "A lane with a scanner arch that sees inside containers.", 30,
    [R("Scanner control room", 150, "Officers read the scans."), R("Hand search bay", 300, "Suspicious loads are opened and searched."),
     R("Dog unit", 80, "Sniffer dogs and their handlers."), R("Sample lab", 80, "Tests samples from loads."), LOCKERS, WC_STAFF,
     F("Inspectors' room", 50, "Inspectors' desks.")],
    [KITCHENETTE, F("Records room", 50, "Inspection records.")],
    ["A long shed with scanner arches over each lane and red-and-green signals."], h=14.0)

DOCK_FREIGHT_OFFICE = offices(
    [R("Bookings counter", 100, "Shippers book space and file papers."), RECEPTION, WC, F("Freight office", 50, "Freight clerks.")],
    [KITCHENETTE, WC_STAFF, F("Freight office", 50, "Freight clerks."), F("Meeting room", 30, "Meetings with shippers.")],
    "A small office block with a lit freight board in its window.", floors=(1, 2))

HAZARD_SHED = shed(
    "Hazard store", "Fuel cells and chemicals, kept apart from other cargo in separate fire-walled cells.",
    "Hazard cell", "A fire-walled cell for one class of dangerous goods.", 24,
    [R("Spill response room", 80, "Kit for cleaning up leaks."), R("Gas detection room", 50, "Watches for leaks."),
     R("Decontamination showers", 40, "For anyone splashed by chemicals."), LOCKERS, WC_STAFF, F("Office", 30, "Office.")],
    [F("Vent gallery", 60, "Access to the vent fans.")],
    ["A low shed set apart behind a blast wall, painted with hazard diamonds."], h=10.0)

TANKS = {
    "mode": "yard",
    "floors": [("Tank floor", 4.0, 1)],
    "height_extra": 30.0,
    "zones": [
        ("Water tanks", 3, "Big tanks of drinking water for resupplying the cruisers.",
         [{"size": (20, 10), "rooms": [("Pump house", 2, "Pumps water and air to the berths."), ("Control room", 1, "Watches tank levels.")]}]),
        ("Air tanks", 2, "Pressure tanks of breathing air for the cruisers."),
        ("Pipe rack", 1, "Pipes to the berths."),
    ],
    "edge": ("Service road", "A road round the tanks."),
    "floors_text": "Open tank farm; a pump house",
    "structure": "Steel tanks on concrete pads.",
    "look": "Rows of white water tanks and squat blue air spheres linked by pipe racks.",
    "entrances": "Service gate.",
    "capacity": "Water and air to resupply the cruisers.",
    "services": "Pipelines to the berths.",
    "m2_per_person": 5000,
}

CONTAINER_STACKS = dict(CONTAINER_YARD, zones=lambda ctx: _stacks(ctx), height_extra=18.0,
                        look=["Stacked containers in red and grey under floodlights.", "Rows of blue and white containers with a straddle carrier between them.",
                              "A yard of containers stacked four high, lit orange."], capacity="Containers in transit.")


def _stacks(ctx):
    rng = ctx["rng"]
    pool = [("Container rows", 4, "Containers stacked several high."), ("Refrigerated rows", 1, "Plug-in points for refrigerated containers."),
            ("Empty stacks", 1, "Empty containers waiting to be reused."), ("Inspection hold", 1, "Containers held for inspection.")]
    rng.shuffle(pool)
    return [pool[0] + ([{"size": (12, 8), "rooms": [("Checker's hut", 1, "Scans containers in and out.")]}],)] + pool[1:3] + \
        [("Carrier lane", 1, "Lane for straddle carriers.")]


def freight_shed_support(ctx):
    rng = ctx["rng"]
    return [R("Loading docks", 250, "Lorry docks."), R("Shed office", 50, "The shed supervisor."), WC_STAFF] + rng.sample([
        R("Cross-dock area", 300, "Goods move straight from one lorry to another."), R("Parcel sorting", 200, "Small packages sorted by cruiser."),
        R("Forklift charging", 80, "Charges forklifts."), R("Damaged goods room", 60, "Goods damaged in transit.")], 2) + [F("Pallet store", 100, "Pallets.")]


FREIGHT_SHED = shed(
    "Freight floor", "A covered freight store for goods in transit to the fleet.",
    "Freight bay", "A bay of racks or floor stacks.", 36,
    freight_shed_support, [KITCHENETTE, F("Mezzanine store", 80, "Light goods.")],
    ["A long grey freight shed with numbered loading doors.", "A steel shed with translucent roof strips and blue doors.",
     "A ribbed shed with a yellow dock edge and floodlights."], h=12.0)

# ------------------------------------------------------------------ P5 Fleet Quarter

ADMIRAL = {
    "mode": "ring",
    "floors": [("Ground floor", 6.0, 1), ("Staff floor", 4.4, 3), ("Admiral's floor", 5.0, 1)],
    "wing": 26,
    "court": {"name": "Fleet court", "outdoor": True, "about": "A formal courtyard with the fleet's flags, used for ceremonies."},
    "hall_max_m2": 12000,
    "halls": [{"name": "Fleet operations room", "span": 2,
               "about": "The fleet's nerve centre: a room with the position and readiness of every escort cruiser on its screens."},
              {"name": "Hall of the Fleet", "span": 1, "share": 0.6,
               "about": "The ceremonial entrance hall, hung with the badges of every cruiser that has served the Invicta."}],
    "rooms": [
        [R("Guarded entrance", 100, "Visitors are checked and escorted."), R("Press room", 80, "Fleet announcements."), WC,
         F("Staff office", 60, "Fleet staff officers."), F("Meeting room", 40, "Staff meetings.")],
        [R("Intelligence room", 150, "Studies threats to the ship."), R("Logistics office", 150, "Plans the fleet's supplies."),
         R("Personnel office", 120, "Postings and records of every crew member."), KITCHENETTE, WC_STAFF,
         F("Staff office", 60, "Fleet staff officers."), F("Planning room", 80, "Plans patrols and exercises.")],
        [R("Fleet Admiral's office", 120, "The office of the Fleet Admiral, commander of the escort fleet."),
         R("War room", 200, "A secure room for the admiral and captains in a crisis."), R("Admiral's staff office", 80, "The admiral's aides."),
         R("Dining room", 80, "For official guests."), WC, F("Senior officer's office", 50, "Offices for senior staff.")],
    ],
    "structure": "Concrete frame with stone cladding and a secure core.",
    "look": "A grand, symmetrical headquarters in pale stone with tall windows, the fleet's flags on its roof and a lit crest over the doors.",
    "entrances": "Ceremonial entrance from Fleet Plaza; guarded staff entrance at the side.",
    "capacity": "About {people} staff.",
    "services": "Secure communications, duplicate power.",
    "m2_per_person": 20,
}

CAPTAINS_HALL = offices(
    [R("Entrance hall", 150, "Hung with portraits of past captains."), R("Captains' mess", 200, "Where the captains eat and meet."), WC,
     F("Captain's shore office", 80, "One cruiser captain's office ashore, with a meeting table.")],
    [R("Conference room", 100, "The six captains meet here."), KITCHENETTE, WC_STAFF,
     F("Captain's shore office", 80, "One cruiser captain's office ashore, with a meeting table."),
     F("Executive officer's office", 50, "The captain's second-in-command.")],
    "A dignified two-storey hall in dark stone with six bay windows, one per cruiser.", floors=1)

FLEET_COMMS = shed(
    "Communications hall", "Rows of encrypted radio and data equipment keeping secure links with each cruiser.",
    "Link rack row", "Racks for one cruiser's secure links.", 30,
    [R("Communications control room", 150, "Operators watch every link to the fleet."), R("Crypto room", 80, "Holds the encryption keys; two-person entry only."),
     R("Battery room", 120, "Keeps links running through any power failure."), SECURITY, LOCKERS, WC_STAFF, F("Workshop", 80, "Repairs radios.")],
    [R("Operators' rest room", 60, "Rest room for operators on long watches."), KITCHENETTE, F("Offices", 30, "Offices.")],
    ["A windowless dark block bristling with dishes and masts, guarded at a single door."], h=8.0)

FLEET_PLAZA = {
    "mode": "park",
    "floors": [("Ground", 4.0, 1)],
    "height_extra": 12.0,
    "zones": [
        ("Parade square", 4, "A paved square in front of the Fleet Admiral's Office, used for parades and ceremonies.",
         [], [("Flag masts", "A row of masts flying the flags of the six cruisers.", (0.3, 0.05, 0.4, 0.06))]),
        ("Memorial garden", 1, "A quiet garden with a memorial to crews lost in service.",
         [], [("Fleet memorial", "A stone memorial with the names of the fallen.", (0.4, 0.4, 0.2, 0.2))]),
        ("Tree avenue", 1, "An avenue of trees leading to the Admiral's Office."),
        ("Café terrace", 1, "Outdoor tables beside a café kiosk.",
         [{"size": (16, 10), "rooms": [("Café kiosk", 2, "Coffee and food."), ("Toilets", 1, "Public toilets.")]}]),
    ],
    "edge": ("Planted edge", "Low planting along the plaza edge."),
    "floors_text": "Open square; a café kiosk",
    "structure": "Stone paving over the deck.",
    "look": "A broad stone parade square with a row of fleet flags, a memorial garden and an avenue of trees.",
    "entrances": "Open on all sides.",
    "capacity": "A parade of {people} people.",
    "services": "Lighting, PA system for ceremonies.",
    "m2_per_person": 4,
}

CREWS_HALL = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 2)],
    "wing": 26,
    "court": {"name": "Crew garden court", "outdoor": True, "about": "A garden court where crews on leave relax."},
    "hall_max_m2": 12000,
    "halls": [{"name": "Crew canteen", "span": 1, "about": "A big canteen serving hot meals to crews on leave."}],
    "rooms": [
        [R("Welcome desk", 80, "Crews on leave book rooms and get passes."), R("Kitchen", 300, "Cooks for the canteen."),
         R("Gym", 300, "Gym for crews keeping fit ashore."), R("Laundry", 150, "Washes crews' kit."), WC,
         F("Crew lounge", 120, "Sofas, games and screens."), F("Locker room", 90, "Lockers for crews' sea bags.")],
        [R("Games room", 150, "Pool tables and games."), R("Family room", 80, "Crews meet their families."), KITCHENETTE, WC,
         F("Shore room", 20, "A simple bedroom for a crew member ashore."), F("Quiet room", 40, "A quiet room to read or call home.")],
    ],
    "structure": "Concrete frame.",
    "look": "A big, friendly block with the six cruisers' badges along its front and a lit canteen on the ground floor.",
    "entrances": "Main entrance from the street.",
    "capacity": "About {people} crew.",
    "services": "Laundry, kitchen, gym.",
    "m2_per_person": 20,
}

DOCKWORKERS_HALL = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    "wing": 24,
    "court": LIGHT_COURT,
    "hall_max_m2": 10000,
    "halls": [{"name": "Union meeting hall", "span": 1, "about": "The dockworkers' union hall, where members meet and vote."}],
    "rooms": [
        [R("Canteen", 400, "Cheap hot food for dockworkers."), R("Kitchen", 200, "Cooks for the canteen."), WC,
         F("Locker room", 90, "Lockers and showers."), F("Hiring hall", 150, "Where casual dockworkers are picked for shifts.")],
        [R("Union offices", 150, "The union's officers."), R("Welfare office", 60, "Helps members with money and health troubles."),
         R("Training room", 80, "Safety and skills courses."), KITCHENETTE, WC, F("Club room", 80, "A members' bar and games room.")],
    ],
    "structure": "Concrete frame.",
    "look": "A sturdy brick-red hall with the union's banner over the door.",
    "entrances": "Main entrance from the street.",
    "capacity": "About {people} members at a meeting.",
    "services": "Showers, kitchen.",
    "m2_per_person": 10,
}

TRANSIT_LODGE = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Bedroom floor", 3.4, (4, 6))],
    "wing": 22,
    "court": {"name": "Lodge garden", "outdoor": True, "about": "A garden court for guests."},
    "hall_max_m2": 10000,
    "halls": [{"name": "Lodge dining hall", "span": 1, "about": "A dining hall serving crews between cruisers."}],
    "rooms": [
        [R("Front desk", 100, "Crews check in for a night or a week between postings."), R("Kitchen", 300, "Cooks for the dining hall."),
         R("Laundry", 200, "Washes crews' kit and the lodge's linen."), R("Luggage store", 150, "Sea bags left while crews are out."), WC,
         F("Lounge", 120, "Sofas and screens."), F("Bag store", 60, "Lockers for kit.")],
        [R("Linen room", 20, "Clean sheets and towels."), R("Shower room", 30, "Shared showers.", 2),
         F("Bunk room", 18, "A cabin with two bunks, a desk and lockers, like a cruiser cabin.")],
    ],
    "structure": "Concrete frame with heavy sound insulation.",
    "look": "A tall, plain lodge with rows of small cabin windows and a lit 'Crew Transit' sign.",
    "entrances": "Front entrance from the street.",
    "capacity": "About 2,000 rooms.",
    "services": "Laundry, kitchen, luggage store.",
    "m2_per_person": 20,
}

FLEET_TRAINING = {
    "mode": "ring",
    "floors": [("Drill floor", 12.0, 1), ("Classroom floor", 4.2, 1)],
    "wing": 24,
    "court": LIGHT_COURT,
    "hall_max_m2": 15000,
    "halls": [{"name": "Damage control rig", "span": 2,
               "about": "A full-size mock-up of a cruiser's decks that can be flooded, filled with smoke or set on fire, so crews practise saving their ship."},
              {"name": "Boarding drill hall", "span": 2, "share": 0.7,
               "about": "Mock corridors and hatches where crews practise boarding and repelling boarders."}],
    "rooms": [
        [R("Fire training control", 100, "Instructors control the fires and floods from here."), R("Breathing set room", 150, "Breathing sets for trainees."),
         R("Kit room", 150, "Fire suits, hoses and repair kit."), R("Showers and decontamination", 150, "Trainees wash after drills."),
         LOCKERS, WC, F("Debrief room", 40, "Instructors go over each drill.")],
        [R("Lecture room", 120, "Lessons on damage control and boarding."), KITCHENETTE, WC,
         F("Classroom", 60, "A classroom for 20 trainees."), F("Instructors' office", 40, "Instructors plan drills.")],
    ],
    "structure": "Steel drill halls with fire-proof linings; concrete classroom wing.",
    "look": "A tall dark training hall with smoke vents on its roof and a red light over the drill rig doors.",
    "entrances": "Main entrance; fire engine access to the rig.",
    "capacity": "About {people} trainees.",
    "services": "Smoke and fire systems, flooding tanks, drainage.",
    "m2_per_person": 30,
}

FLEET_CLINIC = clinic("the Fleet Quarter", [R("Dental surgery", 30, "A dentist's chair and X-ray.", 4),
                                            R("Fitness-to-sail room", 40, "Checks crews are fit before they go aboard."),
                                            R("Vaccination room", 30, "Vaccines for crews heading out.")], size="large", style=2)

DOCK_CANTEEN = canteen("the dock workforce", [R("Takeaway hatch", 40, "Food to take back to the yards."),
                                              R("Night counter", 40, "Hot food through the night shift.")], style=3)


def fleet_offices(ctx):
    rng = ctx["rng"]
    return [RECEPTION, WC] + rng.sample([
        R("Pay office", 80, "Crews' pay and allowances."), R("Postings office", 80, "Decides who serves on which cruiser."),
        R("Welfare office", 60, "Helps crews' families."), R("Chaplaincy", 60, "Chaplains for crews and families."),
        R("Legal office", 60, "The fleet's lawyers."), R("Supply office", 80, "Orders the fleet's supplies.")], 2) + \
        [F("Staff office", 50, "Desks for the fleet's shore staff."), F("Meeting room", 30, "Small meeting room.")]


FLEET_OFFICES = offices(fleet_offices, [KITCHENETTE, WC_STAFF, F("Staff office", 50, "Desks for the fleet's shore staff."),
                                        F("Records room", 40, "Files for crews and cruisers.")],
                        ["A plain office block in grey stone with the fleet crest over the door.",
                         "A slim office block with navy-blue window frames.",
                         "An office block with a glass stair tower and the fleet's flag on the roof."])

CREW_GARDEN = garden("garden for crews ashore", [("Cruiser view lawn", 1, "A lawn with a view of the cruisers' masts in the berths."),
                                                 ("Barbecue terrace", 1, "Grills and tables for crews' get-togethers.")], style=2)

# ------------------------------------------------------------------ P6 Dockside

MARKET = {
    "mode": "ring",
    "floors": [("Market floor", 6.0, 1), ("Upper floor", 4.4, 1)],
    "wing": 20,
    "court": LIGHT_COURT,
    "hall_max_m2": 15000,
    "halls": [{"name": "Market hall", "span": 1,
               "about": "A covered market of stalls selling food, clothes and goods from all over the ship.",
               "bays": None}],
    "rooms": [
        [R("Market office", 60, "Lets stalls and keeps the market clean."), WC,
         F("|Grocer|Butcher|Baker|Fishmonger|Spice shop", 60, "A market shop selling fresh food."),
         F("|Workwear shop|Tool shop|Chandler|Phone shop", 80, "A shop for dock workers and crews."),
         F("|Noodle bar|Grill|Dumpling bar|Café", 80, "A small place to eat.")],
        [R("Food court", 600, "Tables round a ring of food stalls."), WC,
         F("|Barber|Tailor|Repair shop|Money changer", 50, "A small service shop."), F("Store room", 40, "Stock for the shops below.")],
    ],
    "structure": "Steel market roof on concrete columns.",
    "look": "A long, busy market hall with a glazed barrel roof, striped awnings and strings of lights.",
    "entrances": "Wide doors on every side.",
    "capacity": "About {people} shoppers.",
    "services": "Cold rooms, waste, lighting.",
    "m2_per_person": 5,
}

SPACERS_INN = {
    "mode": "ring",
    "floors": [("Ground floor", 5.0, 1), ("Room floor", 3.4, (3, 5))],
    "wing": 22,
    "court": {"name": "Inn courtyard", "outdoor": True, "about": "A courtyard with tables and lanterns."},
    "hall_max_m2": 8000,
    "halls": [{"name": "Taproom", "span": 1, "about": "The inn's big bar room, full of visiting crews swapping stories."}],
    "rooms": [
        [R("Front desk", 60, "Guests check in."), R("Kitchen", 200, "Cooks for the taproom."), R("Luggage room", 80, "Guests' bags."), WC,
         F("Lounge", 100, "Sofas round a fire screen."), F("Private dining room", 40, "Bookable for crews.")],
        [R("Linen room", 20, "Sheets and towels."), F("Guest room", 22, "A guest room with a bed, desk and shower."),
         F("Crew suite", 50, "A larger room for a whole small crew.")],
    ],
    "structure": "Concrete frame with timber-clad interiors.",
    "look": "A rambling inn with warm lit windows, a swinging sign of a ship and lanterns round its courtyard.",
    "entrances": "Front door from the street.",
    "capacity": "About {people} guests.",
    "services": "Kitchen, laundry.",
    "m2_per_person": 25,
}

DOCKSIDE_OFFICES = offices(
    [RECEPTION, WC, F("|Shipping agent|Freight broker|Insurance office|Crew agency", 60, "A small firm's office.")],
    [KITCHENETTE, WC_STAFF, F("|Shipping agent|Freight broker|Insurance office|Crew agency", 60, "A small firm's office."),
     F("Meeting room", 30, "Bookable meeting room.")],
    "A busy office block with brass plates for dozens of firms by its door.")

DOCKSIDE_GARDENS = garden("garden walk beside the Atrium Plaza", [("Riverside walk", 2, "A long path beside a stream."),
                                                                   ("Rose garden", 1, "Beds of roses.")], style=3)

HOSTEL = {
    "mode": "ring",
    "floors": [("Ground floor", 4.5, 1), ("Bunk floor", 3.2, (2, 3))],
    "wing": 20,
    "court": LIGHT_COURT,
    "rooms": [
        [R("Front desk", 40, "Beds by the night."), R("Kitchen", 80, "Self-catering kitchen."), R("Lounge", 150, "Common room."), WC,
         F("Locker room", 50, "Lockers.")],
        [R("Showers", 40, "Shared showers.", 2), F("Bunk room", 30, "A room of four bunks for dockworkers on double shifts.")],
    ],
    "structure": "Concrete frame.",
    "look": "A plain block with small windows and a lit 'Beds' sign.",
    "entrances": "Front door.",
    "capacity": "About {people} beds.",
    "services": "Laundry.",
    "m2_per_person": 8,
}

POLICE = {
    "mode": "ring",
    "floors": [("Ground floor", 4.8, 1), ("Upper floor", 4.2, 1)],
    "wing": 22,
    "court": {"name": "Vehicle yard", "outdoor": True, "about": "Patrol cars and bikes park here."},
    "rooms": [
        [R("Front counter", 60, "The public report crimes and lost property."), R("Custody suite", 200, "Cells and interview rooms."),
         R("Interview room", 15, "Suspects and witnesses are interviewed.", 4), R("Evidence store", 60, "Locked evidence."),
         R("Control room", 80, "Officers watch dock cameras."), LOCKERS, WC, F("Patrol room", 60, "Officers prepare for patrol.")],
        [R("Detectives' office", 150, "Investigates dock theft and smuggling."), R("Briefing room", 60, "Shift briefings."), KITCHENETTE, WC_STAFF,
         F("Offices", 30, "Offices.")],
    ],
    "structure": "Concrete frame with secure custody suite.",
    "look": "A blue-trimmed police post with a lit sign and a vehicle yard behind.",
    "entrances": "Public front door; custody entrance at the back.",
    "capacity": "About {people} officers.",
    "services": "Cameras, secure cells.",
    "m2_per_person": 20,
}

DOCKSIDE_CLINIC = clinic("Dockside", [R("Injury room", 30, "Treats cuts, crushes and burns from the docks.", 3)], size="small", style=1)


def shops(ctx):
    rng = ctx["rng"]
    return [WC] + rng.sample([
        R("Café", 120, "Coffee and food."), R("Chandler", 150, "Kit and clothing for ship crews."), R("Bar", 150, "A dockside bar."),
        R("Noodle bar", 100, "Hot noodles."), R("Convenience store", 150, "Daily essentials."), R("Pharmacy", 80, "Medicines."),
        R("Bookmaker", 60, "Bets on deck sports."), R("Tattoo studio", 50, "Crews' tattoos."), R("Pawn shop", 60, "Buys and sells.")], 4) + \
        [F("|Shop|Takeaway|Bakery|Repair shop", 70, "A small shop.")]


DOCKSIDE_SHOPS = {
    "mode": "ring",
    "floors": [("Shop floor", 5.0, 1), ("Upper floor", 4.0, 1)],
    "wing": 20,
    "court": LIGHT_COURT,
    "rooms": [shops, [KITCHENETTE, F("|Flat|Studio flat", 50, "A small flat above the shops."), F("Store room", 40, "Stock.")]],
    "structure": "Concrete frame.",
    "look": ["A row of small shops with bright signs and awnings.", "A two-storey block of cafés and bars, lit late into the night.",
             "Shops with neon signs and flats above."],
    "entrances": "Shopfronts on every street side.",
    "capacity": "About {people} shoppers.",
    "services": "Shop power and water.",
    "m2_per_person": 10,
}

POCKET_PARK = garden("small dockside park", [("Play area", 1, "Swings and climbing frames."), ("Seating corner", 1, "Benches under trees.")], style=0)

PROGRAMS = [
    (r"^Cruiser Gate 1 Berths$", berths(1)),
    (r"^Cruiser Gate 2 Berths$", berths(2)),
    (r"^Cruiser Gate 3 Berths$", berths(3)),
    (r"^Supply Quay A$", supply_quay("1 and 2")),
    (r"^Supply Quay B$", supply_quay("2 and 3")),
    (r"^Cruiser Gate Control$", GATE_CONTROL),
    (r"^Gangway Hall$", GANGWAY_HALL),
    (r"^Fleet Inspectors' Office$", FLEET_INSPECTORS),
    (r"^Gangway Canteen$", GANGWAY_CANTEEN),
    (r"^Berths Fire Station$", BERTHS_FIRE),
    (r"^Berth Utility Plant$", BERTH_PLANT),
    (r"^Quay Yard", QUAY_YARD),
    (r"^Cruiser Munitions Magazine$", MAGAZINE),
    (r"^Cruiser Fuel Farm$", FUEL_FARM),
    (r"^Fleet Stores Warehouse$", STORES_WAREHOUSE),
    (r"^Repair Parts Depot$", REPAIR_PARTS),
    (r"^Stores Control$", STORES_CONTROL),
    (r"^Loaders' Hall$", LOADERS_HALL),
    (r"^Stores Fire Station$", STORES_FIRE),
    (r"^Stores Shed", STORES_SHED),
    (r"^Stores Yard", STORES_YARD),
    (r"^Module Repair Hall$", MODULE_REPAIR_HALL),
    (r"^Turret Shop$", TURRET_SHOP),
    (r"^Engine Module Shop$", ENGINE_SHOP),
    (r"^Hull Plate Store$", HULL_PLATE_STORE),
    (r"^Shield Module Lab$", SHIELD_LAB),
    (r"^Yard Crane Depot$", CRANE_DEPOT),
    (r"^Inspectors' Hall$", INSPECTORS_HALL),
    (r"^Dockside Park$", DOCKSIDE_PARK),
    (r"^Repair Yards Fire Station$", fire_station("the cruiser repair yards", [R("Heavy cutting kit room", 60, "Cutters for freeing people trapped under heavy modules.")],
                                                  ["Fire engine", "Heavy rescue unit", "Foam tender"], style=2)),
    (r"^Module Yard", MODULE_YARD),
    (r"^Repair Shed", REPAIR_SHED),
    (r"^Container Yard$", CONTAINER_YARD),
    (r"^Bonded Warehouse$", BONDED),
    (r"^Cold Store$", COLD_STORE),
    (r"^Loaders' Depot$", LOADERS_DEPOT),
    (r"^Freight Inspection Shed$", INSPECTION_SHED),
    (r"^Dock Freight Office$", DOCK_FREIGHT_OFFICE),
    (r"^Hazardous Cargo Shed$", HAZARD_SHED),
    (r"^Water and Air Tanks$", TANKS),
    (r"^Dock Freight Fire Station$", fire_station("Dock Freight", [R("Hazmat kit room", 60, "Suits and kit for chemical leaks from cargo.")],
                                                  ["Fire engine", "Hazmat unit", "Rescue unit"], style=1)),
    (r"^Container Stacks", CONTAINER_STACKS),
    (r"^Freight Shed", FREIGHT_SHED),
    (r"^Fleet Admiral's Office$", ADMIRAL),
    (r"^Cruiser Captains' Hall$", CAPTAINS_HALL),
    (r"^Fleet Communications Centre$", FLEET_COMMS),
    (r"^Fleet Plaza$", FLEET_PLAZA),
    (r"^Cruiser Crews' Hall$", CREWS_HALL),
    (r"^Dockworkers' Hall$", DOCKWORKERS_HALL),
    (r"^Crew Transit Lodge$", TRANSIT_LODGE),
    (r"^Fleet Training Hall$", FLEET_TRAINING),
    (r"^Fleet Clinic$", FLEET_CLINIC),
    (r"^Dock Canteen$", DOCK_CANTEEN),
    (r"^Fleet Offices", FLEET_OFFICES),
    (r"^Crew Garden", CREW_GARDEN),
    (r"^Dockside Market$", MARKET),
    (r"^Spacers' Inn$", SPACERS_INN),
    (r"^Dockside Offices$", DOCKSIDE_OFFICES),
    (r"^Dockside Gardens$", DOCKSIDE_GARDENS),
    (r"^Dockside Hostel$", HOSTEL),
    (r"^Dock Police Post$", POLICE),
    (r"^Dockside Clinic$", DOCKSIDE_CLINIC),
    (r"^Dockside Shops", DOCKSIDE_SHOPS),
    (r"^Pocket Park", POCKET_PARK),
]

_PLANTS = {"Fleet Stores": (0, [R("Magazine cooling room", 120, "Keeps the munitions vaults cool.")]),
           "Repair Yards": (3, [R("Heavy power room", 200, "Big power feeds for the repair hall's cranes and welders.")]),
           "Dock Freight": (1, [R("Refrigeration power room", 120, "Power for the cold store and refrigerated containers.")]),
           "Fleet Quarter": (2, []), "Dockside": (0, [])}
for _n, (_st, _ex) in _PLANTS.items():
    PROGRAMS.append((r"^%s Utility Plant$" % _n, utility_plant(_n, _ex, style=_st)))
for _n, _st in {"Gates": 1, "Fleet Stores": 2, "Repair Yards": 0, "Dock Freight": 3, "Fleet Quarter": 1, "Dockside": 2}.items():
    PROGRAMS.append((r"^%s Service Shaft$" % _n, service_shaft(_n, style=_st)))

# More fill types for the biggest floors, so they don't repeat one room hundreds of times
_MORE = [
    (MODULE_REPAIR_HALL, 1, [F("Repair planning office", 60, "Planners who schedule each module's repair."),
                             F("Parts kitting room", 80, "Parts are gathered into a kit for each repair job.")]),
    (ENGINE_SHOP, 1, [F("Engine analysis room", 60, "Engineers study wear and test data from each engine."),
                      F("Training room", 60, "Fitters learn new engine types.")]),
    (TURRET_SHOP, 1, [F("Fire control office", 50, "Engineers who set up the turrets' aiming systems.")]),
    (FLEET_TRAINING, 0, [F("Equipment drying room", 50, "Wet fire suits and hoses dry out after a drill."),
                         F("Instructors' room", 40, "Instructors prepare the next drill.")]),
    (FLEET_TRAINING, 1, [F("Simulator room", 60, "Screen-based damage control simulators.")]),
    (ADMIRAL, 1, [F("Records office", 60, "The fleet's records and orders."), F("Liaison office", 50, "Officers from Flight Control and the ship's command.")]),
    (FLEET_CLINIC, 0, [F("Treatment room", 30, "Dressings, stitches and injections."), F("Physiotherapy room", 50, "Helps crews recover from injuries.")]),
    (DOCKSIDE_CLINIC, 0, [F("Treatment room", 30, "Dressings, stitches and injections.")]),
    (GATE_CONTROL, 0, [F("Spares store", 60, "Spare parts for the gate machinery.")]),
    (FLEET_INSPECTORS, 1, [F("Survey team room", 50, "A team that surveys one cruiser at a time.")]),
]
for _p, _i, _rows in _MORE:
    if not callable(_p["rooms"][_i]):
        _p["rooms"][_i] = list(_p["rooms"][_i]) + _rows
