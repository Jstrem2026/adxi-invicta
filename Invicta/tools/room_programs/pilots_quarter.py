"""Room programs for the Pilots' Quarter (Deck 5 Aerion), written 27 Nov 2026. See tools/design_rooms.py.

The flight school, the simulator halls, the Commons town centre and the homes of pilots, crews and their families.
"""
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


def sim_hall(name, about, bay, bay_about, bay_w, h, support, upper, look, **kw):
    return shed(name, about, bay, bay_about, bay_w,
                support + [LOCKERS, WC], upper, look, h=h,
                structure="Steel hall with a deep floor slab to take the simulators' moving platforms.",
                entrances="Trainee entrance with a briefing lobby; equipment doors at the back.",
                capacity="About {people} trainees and instructors at once.",
                services="Heavy power, cooling for the simulator computers, data links to the Simulator Data Centre.",
                m2_per_person=60, **kw)


SIM_SUPPORT = [R("Briefing room", 60, "Instructor and trainee plan the session before climbing in.", 4),
               R("Debrief room", 40, "The session is replayed on screen and gone over step by step.", 4),
               R("Instructor station", 80, "Instructors set up faults, weather and enemies for each session.")]

# ------------------------------------------------------------------ P1 Flight School

FLIGHT_SCHOOL_MAIN = ring(
    [("Ground floor", 5.0, 1), ("Teaching floor", 4.2, 3)],
    [[R("Entrance hall", 400, "The school's grand entrance, hung with photos of every graduating class."),
      R("Admissions office", 80, "New trainees enrol here."), R("Lecture theatre", 300, "Lectures for a whole intake of trainees.", 2), WC,
      F("Classroom", 70, "A classroom for 24 trainees, with screens and a cockpit diagram wall."),
      F("Study room", 30, "Trainees revise together in small groups.")],
     [R("Staff room", 120, "Instructors' lounge and kitchen."), KITCHENETTE, WC,
      F("Classroom", 70, "A classroom for 24 trainees, with screens and a cockpit diagram wall."),
      F("Instructors' office", 40, "Desks for flight instructors."), F("Exam room", 80, "Written and screen exams.")],
     ],
    ["A broad teal-trimmed school with a tall glass entrance hall and the flight school's wings badge above its doors."],
    halls=[{"name": "Great Hall", "span": 1, "about": "The school's assembly hall, used for lectures, assemblies and the welcome of each new intake."}],
    capacity="About {people} trainees and staff.", m2_per_person=10)

TRAINING_HANGAR = shed(
    "Training hangar", "The flight school's training craft are kept here; trainees learn to inspect, fuel and prepare a craft before flying it.",
    "Training craft bay", "One training craft on its stand, with steps and a tool trolley so trainees can practise checks.", 40,
    [R("Inspection classroom", 120, "Instructors teach pre-flight checks with a craft in view through the glass."),
     R("Parts and tools store", 150, "Tools, spares and checklists for the training craft."), R("Fuel and power control", 50, "Controls fuel and power to the bays."),
     LOCKERS, WC_STAFF, F("Maintenance workshop", 100, "Engineers keep the training craft flying.")],
    [R("Flight line office", 60, "Books craft for each lesson."), KITCHENETTE, F("Viewing gallery", 60, "A gallery over the hangar floor for new trainees.")],
    ["A large steel hangar with teal doors and a training craft's silhouette painted on its end wall."], h=16.0,
    entrances="Hangar doors to the Training Flight Line; trainee entrance.", capacity="About 20 training craft.")


def flight_line(ctx):
    return [("Craft parking", 4, "Training craft parked in rows, chocked and tied down, between lessons.",
             [{"size": (20, 10), "rooms": [("Flight line hut", 2, "Line staff sign craft out and in."),
                                           ("Trainees' shelter", 1, "Trainees wait for their craft here.")]}]),
            ("Fuelling apron", 1, "Fuel bowsers and power carts service craft between flights."),
            ("Start-up line", 1, "Where trainees start their engines and run final checks before taxiing out."),
            ("Taxi lane", 1, "The lane craft taxi along to and from the flight deck.")]


FLIGHT_LINE = {
    "mode": "yard", "floors": [("Line", 4.0, 1)], "height_extra": 4.0, "zones": flight_line,
    "edge": ("Safety line", "A painted line and fence; nobody crosses without a line marshal."),
    "floors_text": "Open apron; a line hut",
    "structure": "Reinforced deck surface with tie-down rings and fuel points.",
    "look": "Rows of small white-and-teal training craft on a floodlit apron, with fuel bowsers moving between them.",
    "entrances": "Taxi lane to the flight deck; gate from the Training Hangar.",
    "capacity": "About 40 training craft.", "services": "Fuel points, ground power, floodlights.", "m2_per_person": 3000,
}

NAV_SCHOOL = ring(
    [("Ground floor", 4.8, 1), ("Teaching floor", 4.2, 2)],
    [[R("Star dome", 300, "A domed screen that shows the sky and the Drift Network as seen from the ship, for teaching navigation."),
      R("Chart room", 200, "Big tables for plotting routes on paper charts."), RECEPTION, WC,
      F("Classroom", 60, "A navigation classroom.")],
     [R("Navigation simulator room", 150, "Desks that recreate a craft's navigation station."), KITCHENETTE, WC,
      F("Classroom", 60, "A navigation classroom."), F("Instructors' office", 40, "Instructors.")]],
    ["A teal-trimmed school with a white dome on its roof over the star dome."], capacity="About {people} trainees.")

ENGINEERING_SCHOOL = ring(
    [("Workshop floor", 6.0, 1), ("Classroom floor", 4.2, 2)],
    [[R("Engine workshop", 400, "Trainee mechanics strip and rebuild real engines."), R("Weapons workshop", 300, "Trainee armorers learn to load and service craft weapons."),
      R("Electronics lab", 200, "Avionics and wiring practice."), R("Tool store", 100, "Tools signed out to trainees."), LOCKERS, WC,
      F("Workshop bay", 80, "A bench bay for one trainee team.")],
     [KITCHENETTE, WC, F("Classroom", 60, "A classroom for trainee mechanics and armorers."), F("Instructors' office", 40, "Instructors.")]],
    ["A teal-trimmed workshop block with big roller doors on the ground floor."], capacity="About {people} trainees.")

SURVIVAL_SCHOOL = ring(
    [("Drill floor", 10.0, 1), ("Classroom floor", 4.2, 1)],
    [[R("Ejection seat trainer", 150, "A rig that fires trainees up a rail, so they know what an ejection feels like."),
      R("Vacuum chamber", 200, "A chamber where trainees practise in pressure suits as the air is pumped out."),
      R("Suit room", 200, "Pressure suits, helmets and survival packs."), R("Medical room", 60, "A doctor watches every drill."), LOCKERS, WC,
      F("Debrief room", 40, "Instructors go over each drill.")],
     [R("Survival kit room", 120, "Trainees learn what is in a survival pack and how to use it."), KITCHENETTE, WC,
      F("Classroom", 60, "A classroom for survival lessons.")]],
    ["A tall dark drill hall with a red warning light over the vacuum chamber door."],
    halls=[{"name": "Escape drill hall", "span": 2,
            "about": "A tall hall with mock cockpits and a water pool where trainees practise escaping a damaged craft."}],
    capacity="About {people} trainees.")

PARADE_GROUND = {
    "mode": "park", "floors": [("Ground", 4.0, 1)], "height_extra": 12.0,
    "zones": [("Parade square", 5, "A wide paved square where cadets drill and graduating classes march past.", [],
               [("Saluting dais", "A raised dais where the commandant takes the salute.", (0.4, 0.05, 0.2, 0.08)),
                ("Flag masts", "Masts for the flight school's and the wings' flags.", (0.2, 0.05, 0.6, 0.03))]),
              ("Spectator stands", 1, "Stands for families at graduation."),
              ("Tree avenue", 1, "An avenue of trees round the square.")],
    "edge": ("Planted edge", "Low hedges round the parade ground."),
    "floors_text": "Open square", "structure": "Paving over the deck.",
    "look": "A broad pale parade square with flags, a saluting dais and stands along one side.",
    "entrances": "Open from the school streets.", "capacity": "A parade of {people} cadets.",
    "services": "Lighting, PA system.", "m2_per_person": 4,
}


def halls_of_residence(who, look):
    return ring([("Ground floor", 4.5, 1), ("Bedroom floor", 3.2, (3, 5))],
                [[R("Front desk", 40, "Reception and post."), R("Common room", 200, "Sofas, games and a big screen."),
                  R("Laundry", 60, "Washing machines and dryers."), R("Kitchen and dining room", 200, "Meals for residents."), WC,
                  F("Study room", 30, "Quiet study.")],
                 [R("Shared kitchen", 25, "A small kitchen for each floor."), R("Bathroom", 25, "Showers and toilets.", 2),
                  F("Bedroom", 14, "A bedroom for one %s with a bed, desk and wardrobe." % who)]],
                look, court={"name": "Residents' garden", "outdoor": True, "about": "A garden court for residents."},
                capacity="About {people} residents.", m2_per_person=25)


TRAINEE_HALLS = halls_of_residence("trainee pilot", ["A long teal-trimmed hall of residence with rows of small windows.",
                                                      "A residence block round a garden court, with bikes parked by the door."])
CADET_HOUSE = halls_of_residence("cadet", ["A boarding house with a house crest over its door and a garden behind.",
                                           "A cadet house with teal shutters and a lit common room on the ground floor.",
                                           "A three-storey cadet house round a small courtyard."])
CADET_HOUSE["rooms"][0] = CADET_HOUSE["rooms"][0] + [R("Housemaster's flat", 90, "The housemaster lives in and looks after the cadets.")]


def apartments(who, extra0=(), look=None, floors=(4, 8), court=None, fills=None, **kw):
    fills = fills or [F("|Two-bedroom flat|Three-bedroom flat", 85, "A family flat with a living room, kitchen, bedrooms and bathroom."),
                      F("One-bedroom flat", 50, "A flat for a couple or one person.")]
    return ring([("Ground floor", 4.5, 1), ("Flat floor", 3.2, floors)],
                [[R("Entrance lobby", 80, "Post boxes and the lift lobby."), R("Bike and pram store", 60, "Bikes and prams."),
                  R("Bin store", 30, "Rubbish and recycling.")] + list(extra0) + fills,
                 [CLEAN] + fills],
                look, court=court or {"name": "Residents' courtyard", "outdoor": True, "about": "A shared courtyard garden for the %s." % who},
                capacity="About {people} residents.", m2_per_person=35, **kw)


INSTRUCTORS_APTS = apartments("instructors' families", look="A calm apartment block with balconies overlooking the school.", floors=(3, 4))

SCHOOL_LIBRARY = ring(
    [("Reading floor", 5.0, 1), ("Stacks floor", 4.2, 1)],
    [[R("Enquiry desk", 40, "Librarians help find manuals and logbooks."), R("Reading room", 300, "Long tables with lamps."), WC,
      F("Study room", 20, "A quiet room for one or two trainees.")],
     [R("Manual stacks", 300, "Flight manuals for every craft the school flies."), R("Logbook archive", 150, "Logbooks of past trainees and famous pilots."),
      F("Study carrel", 10, "A desk for quiet study.")]],
    ["A small teal-trimmed library with tall windows and reading lamps glowing inside."], capacity="About {people} readers.")

SCHOOL_CANTEEN = canteen("flight school staff and trainees", [R("Training meals counter", 40, "Light meals for trainees flying that day.")], style=1)

SPORTS_FIELD = {
    "mode": "park", "floors": [("Ground", 4.0, 1)], "height_extra": 10.0,
    "zones": [("Sports pitch", 4, "A grass pitch for football and rugby.", [{"size": (24, 12), "rooms": [
        ("Changing rooms", 2, "Changing rooms and showers."), ("Kit store", 1, "Balls, nets and goals.")]}]),
              ("Running track", 2, "A running track round the pitch for fitness tests."),
              ("Fitness trail", 1, "Outdoor exercise stations.")],
    "edge": ("Planted edge", "Hedges round the field."), "floors_text": "Open field; a changing pavilion",
    "structure": "Turf over soil beds on the deck.", "look": "A green pitch ringed by a red running track and floodlights.",
    "entrances": "Gates from the school.", "capacity": "About {people} people at sports day.", "services": "Floodlights, irrigation.",
    "m2_per_person": 50,
}

SCHOOL_CLINIC = clinic("the flight school", [R("Flight medical room", 40, "Trainees' flight medicals: eyes, heart and balance.", 2),
                                             R("Altitude test room", 60, "Tests how trainees cope with thin air.")], style=0)

TRAINING_FIELD = garden("training field", [("Drill field", 2, "Open grass for drill and outdoor exercise."),
                                           ("Obstacle course", 1, "Walls, ropes and nets for fitness training.")], style=1, pavilion=False)

# ------------------------------------------------------------------ P2 Simulator Halls

FULL_MOTION = sim_hall(
    "Full-motion simulator hall", "Forty-eight full-motion cockpit simulators on moving legs, each a sealed cockpit that tilts and shakes like a real craft.",
    "Simulator pod", "One full-motion cockpit simulator on its six moving legs, with steps up to the cockpit door.", 30, 18.0,
    SIM_SUPPORT, [R("Simulator engineers' room", 100, "Engineers keep the simulators running."), KITCHENETTE,
                  F("Observation gallery", 60, "A gallery where visitors watch the pods move.")],
    ["A tall windowless hall with a row of glowing pod numbers along its side."])

SQUADRON_SIM = sim_hall(
    "Squadron simulator hall", "Rows of linked simulators where a whole squadron flies the same mission together.",
    "Squadron pod row", "A row of linked cockpit simulators for one squadron.", 40, 12.0,
    SIM_SUPPORT + [R("Mission planning room", 120, "Squadrons plan their simulated mission.")],
    [R("Exercise control", 150, "Instructors run the whole mission and play the enemy."), KITCHENETTE, F("Offices", 30, "Offices.")],
    ["A long dark hall with squadron badges on its doors."])

BRIDGE_SIM = ring(
    [("Simulator floor", 8.0, 1), ("Support floor", 4.2, 1)],
    [[R("Instructor control room", 120, "Instructors run the bridge simulation and set the scenario."),
      R("Gunnery trainer", 150, "Gunnery consoles linked to the bridge."), RECEPTION, LOCKERS, WC, F("Debrief room", 40, "Debriefs.")],
     [R("Engineers' room", 80, "Keeps the simulator running."), KITCHENETTE, WC, F("Classroom", 60, "Classes for cruiser officers.")]],
    ["A sober grey block with a curved glass front echoing a cruiser's bridge windows."],
    halls=[{"name": "Cruiser bridge simulator", "span": 2,
            "about": "A full-size copy of an escort cruiser's bridge, with helm, command and gunnery stations and a wraparound screen."}],
    capacity="One cruiser bridge crew at a time, plus instructors.")

ZERO_G = ring(
    [("Tank floor", 14.0, 1), ("Gallery floor", 4.2, 1)],
    [[R("Suit-up room", 150, "Trainees put on suits and weights."), R("Dive control room", 80, "Controls the tank's water and safety divers."),
      R("Medical room", 60, "A doctor for every session."), LOCKERS, WC, F("Debrief room", 40, "Debriefs.")],
     [R("Viewing gallery", 150, "Windows into the tank."), KITCHENETTE, F("Instructors' office", 40, "Instructors.")]],
    ["A tall blank-walled block with a blue glow from small windows into the tank."],
    halls=[{"name": "Zero-g training tank", "span": 2,
            "about": "A deep sealed water tank holding a mock craft interior; weighted trainees float as if weightless and practise moving and working."}],
    capacity="About 20 trainees at a time.")

CENTRIFUGE = ring(
    [("Centrifuge floor", 10.0, 1), ("Support floor", 4.2, 1)],
    [[R("Centrifuge control room", 80, "Controls the spin and watches the rider on camera."), R("Medical room", 80, "Doctors check each rider before and after."),
      R("Recovery room", 40, "Riders rest after a session.", 2), LOCKERS, WC, F("Debrief room", 30, "Debriefs.")],
     [KITCHENETTE, WC, F("Researchers' office", 40, "Studies how pilots cope with g-forces.")]],
    ["A round-roofed hall with a red light over its door when the centrifuge is spinning."],
    halls=[{"name": "Centrifuge hall", "span": 2, "about": "A long arm with a cockpit on the end that spins pilots round to build their tolerance to high g-forces."}],
    capacity="One rider at a time.")

SIM_CONTROL = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Master control room", 200, "Watches every simulator session in the precinct and starts and stops them."),
      R("Recording room", 100, "Records every session so instructors can replay it."), RECEPTION, WC,
      F("Scenario office", 50, "Designers who build new training missions.")],
     [KITCHENETTE, WC, F("Scenario office", 50, "Designers who build new training missions."), F("Review room", 30, "Instructors replay sessions.")]],
    ["A small block with a wall of screens glowing through its front windows."], capacity="About {people} staff.")

SIM_WORKSHOPS = shed(
    "Workshop hall", "Simulators are repaired here and new simulator cockpits are built.",
    "Cockpit build bay", "A bay where one simulator cockpit is built or rebuilt.", 30,
    [R("Electronics shop", 150, "Repairs screens and controls."), R("Motion system shop", 200, "Repairs the moving legs."), LOCKERS, WC_STAFF,
     F("Parts store", 80, "Spares.")],
    [KITCHENETTE, F("Design office", 50, "Engineers design new cockpits.")],
    ["A grey workshop with a half-built cockpit visible through its open door."], h=10.0)

ARCADE = ring(
    [("Arcade floor", 6.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Ticket desk", 60, "Book a flight."), R("Café", 150, "Snacks and drinks."), R("Party room", 80, "Birthday parties.", 2), WC,
      F("Simulator booth", 30, "A simulator anyone can try, from a gentle ride to a full combat mission.")],
     [R("Leaderboard lounge", 200, "Screens show the best scores of the day."), WC,
      F("Simulator booth", 30, "A simulator anyone can try, from a gentle ride to a full combat mission.")]],
    ["A bright, playful building with a lit craft model over its entrance and screens in every window."],
    capacity="About {people} visitors.", m2_per_person=8)

STARBOARD_LAWN = garden("lawn between the simulator halls", [("Picnic lawn", 1, "Tables where trainees eat outside.")], style=2)
SIM_CANTEEN = canteen("simulator staff and trainees", [R("Coffee bar", 60, "Coffee for trainees between sessions.")], style=2)

SIM_DATA = shed(
    "Computer hall", "Rows of computers that run every simulator in the precinct.",
    "Server row", "A row of server racks with its own cooling.", 24,
    [R("Network control room", 100, "Watches the computers and links."), R("Battery room", 120, "Keeps the computers running."), LOCKERS, WC_STAFF,
     F("Spares store", 60, "Spare servers.")],
    [F("Cooling gallery", 60, "Access to the cooling plant.")],
    ["A windowless block with cooling fans along its roof."], h=6.0)

SIM_ANNEX = sim_hall(
    "Simulator annex hall", "Extra simulator bays for when the main halls are full.",
    "Simulator bay", "A fixed-base cockpit simulator with a wraparound screen.", 24, 8.0,
    SIM_SUPPORT[:2], [KITCHENETTE, F("Instructors' room", 40, "Instructors.")],
    ["A plain teal-trimmed simulator shed.", "A long grey annex with pod numbers on its doors.", "A simulator annex with a glass lobby."])

LAWN = garden("lawn between the halls", [("Sitting lawn", 1, "Grass with benches.")], style=0, pavilion=False)

# ------------------------------------------------------------------ P3 Pilots' Commons

TOWN_HALL = ring(
    [("Ground floor", 5.5, 1), ("Office floor", 4.2, 2)],
    [[R("Public hall", 300, "Residents come for permits, housing and help."), R("Council chamber", 200, "The Quarter's council meets here in public."), WC,
      F("Service counter", 40, "A counter for one local service.")],
     [R("Mayor's office", 60, "The Quarter's mayor."), KITCHENETTE, WC_STAFF, F("Council office", 50, "Council staff.")]],
    ["A dignified civic building in pale stone with a clock over its door, facing Commons Square."],
    capacity="About {people} staff.")

COMMONS_SQUARE = {
    "mode": "park", "floors": [("Ground", 4.0, 1)], "height_extra": 10.0,
    "zones": [("Square", 4, "The paved heart of the Quarter, where residents meet, markets set up and events are held.",
               [{"size": (16, 10), "rooms": [("Café kiosk", 2, "Coffee and snacks."), ("Toilets", 1, "Public toilets.")]}],
               [("Pilots' memorial", "A statue of a pilot looking up, with the names of those lost.", (0.45, 0.45, 0.1, 0.1))]),
              ("Fountain", 1, "A splash fountain children play in."), ("Tree terrace", 1, "Trees and benches along the edge.")],
    "edge": ("Planted edge", "Planters round the square."), "floors_text": "Open square; a kiosk",
    "structure": "Paving over the deck.", "look": "A lively paved square with a fountain, café tables and a pilot statue in the middle.",
    "entrances": "Open on all sides.", "capacity": "About {people} people at an event.", "services": "Lighting, fountain.", "m2_per_person": 3,
}

COMMONS_MARKET = ring(
    [("Market floor", 6.0, 1), ("Upper floor", 4.4, 1)],
    [[R("Market office", 50, "Runs the market."), WC,
      F("|Grocer|Butcher|Baker|Fishmonger|Cheese shop|Deli", 60, "A market stall selling fresh food."),
      F("|Flower stall|Hardware stall|Clothes stall", 50, "A market stall.")],
     [R("Food hall seating", 600, "Tables round the food counters."), WC,
      F("|Noodle counter|Grill counter|Curry counter|Pizza counter|Salad bar", 50, "A food hall counter.")]],
    ["A long glass-roofed market hall with striped awnings and the smell of bread at its doors."],
    halls=[{"name": "Market hall", "span": 1, "about": "The covered market of stalls where residents do their everyday shopping."}],
    capacity="About {people} shoppers.", m2_per_person=5)

RESTAURANTS = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.0, 1)],
    [[WC, F("|Bistro|Noodle house|Steak house|Curry house|Pizzeria|Tapas bar|Café", 150, "A restaurant with a terrace on the street."),
      F("Restaurant kitchen", 60, "The kitchen behind each restaurant.")],
     [F("|Flat|Studio flat", 50, "A flat above the restaurants."), F("Private dining room", 40, "A room for parties.")]],
    ["A long, lively street front of restaurants with lanterns, awnings and terraces."],
    capacity="About {people} diners.", m2_per_person=5)


def school(kind, age, extra, look, floors=(1, 2)):
    return ring(
        [("Ground floor", 4.5, 1), ("Upper floor", 4.0, floors)],
        [[R("Entrance and office", 120, "Parents and visitors are met here."), R("Kitchen", 120, "Cooks school lunches."), R("Nurse's room", 25, "First aid."),
          WC] + list(extra) + [F("Classroom", 65, "A classroom for 28 children aged %s." % age), F("Small group room", 25, "Teaching small groups.")],
         [R("Staff room", 80, "Teachers' lounge."), WC, F("Classroom", 65, "A classroom for 28 children aged %s." % age),
          F("Specialist room", 80, "A room for art, music, science or computing.")]],
        look, halls=[{"name": "School hall", "span": 1, "about": "Assemblies, lunch, sport and school plays."}],
        court={"name": "Playground", "outdoor": True, "about": "The children's playground."},
        capacity="About {people} pupils.", m2_per_person=10)


PRIMARY = school("primary", "5 to 11", [R("Library corner", 80, "Picture books and reading nooks.")],
                 ["A cheerful teal-and-yellow school round a playground."])
SECONDARY = school("secondary", "11 to 18", [R("Science lab", 90, "Labs for science lessons.", 4), R("Sports hall", 600, "Indoor sports."),
                                             R("Flight club room", 80, "Pupils build model craft and fly a simulator.")],
                   ["A larger teal-trimmed school with a sports hall and labs."], floors=(2, 3))
PORT_SCHOOL = school("Port Homes", "5 to 11", [R("Library corner", 80, "Picture books and reading nooks.")],
                     ["A low school with a colourful playground and a garden."], floors=1)
STARBOARD_SCHOOL = school("Starboard Homes", "5 to 11", [R("Music room", 60, "Music lessons.")],
                          ["A two-storey school with big windows and a planted roof."], floors=1)

CHILDCARE = ring(
    [("Ground floor", 4.0, 1)],
    [[R("Entrance and office", 60, "Parents drop off and collect."), R("Kitchen", 50, "Meals and snacks."), R("Sleep room", 40, "Cots for naps.", 3), WC,
      F("Playroom", 60, "A playroom for one age group.")]],
    ["A low, bright nursery with a fenced garden and big round windows."],
    court={"name": "Play garden", "outdoor": True, "about": "A fenced play garden."}, capacity="About {people} children.", m2_per_person=8)

HOSPITAL = ring(
    [("Ground floor", 5.5, 1), ("Clinical floor", 4.5, 2), ("Ward floor", 4.0, (3, 5))],
    [[R("Emergency department", 1500, "Treats emergencies day and night; ambulances arrive at its own entrance."),
      R("Main entrance hall", 400, "Reception, café and shop."), R("Imaging department", 800, "X-ray, scanners and ultrasound."),
      R("Pharmacy", 200, "Dispenses medicines."), WC, F("Outpatient clinic room", 30, "A consulting room for outpatients.")],
     [R("Operating theatre", 60, "An operating theatre.", 8), R("Intensive care unit", 800, "Care for the most seriously ill."),
      R("Maternity unit", 600, "Births and care for mothers and babies."), WC_STAFF,
      F("Treatment room", 30, "A treatment room."), F("Lab", 60, "Tests blood and samples.")],
     [R("Nurses' station", 40, "Nurses watch over the ward.", 2), KITCHENETTE, WC,
      F("Ward bay", 40, "A bay of four beds."), F("Single room", 20, "A single patient room with its own bathroom.")]],
    ["Aerion's main hospital: a large white building with a red-edged roof, a helipad marked on top and a lit emergency entrance."],
    halls=[{"name": "Hospital atrium", "span": 1, "about": "A daylit atrium at the heart of the hospital, with seats, a café and garden planting."}],
    court={"name": "Healing garden", "outdoor": True, "about": "A quiet garden for patients and visitors."},
    entrances="Main entrance; separate emergency and ambulance entrance; service yard.",
    capacity="About 600 beds.", services="Medical gases, back-up power, clean and dirty lifts.", m2_per_person=50)

FAMILY_HEALTH = clinic("the Pilots' Quarter", [R("Dental surgery", 30, "A dentist's chair and X-ray.", 4), R("Midwives' room", 40, "Antenatal checks.", 2),
                                               R("Baby clinic", 60, "Weighing and check-ups for babies.")], size="large", style=3)

QUARTER_LIBRARY = ring(
    [("Ground floor", 5.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Lending desk", 60, "Borrow and return books."), R("Children's library", 200, "Picture books and story time."),
      R("Makers' space", 200, "3D printers, tools and electronics benches anyone can use."), WC, F("Reading room", 80, "Tables and armchairs.")],
     [R("Study hall", 200, "Quiet study."), WC, F("Study room", 20, "A bookable room for one or two."), F("Book stacks", 80, "Shelves of books.")]],
    ["A friendly library with big windows, a reading garden and a lit makers' space."], capacity="About {people} readers.")

MUSEUM = ring(
    [("Gallery floor", 10.0, 1), ("Upper gallery floor", 5.0, 1)],
    [[R("Entrance hall", 300, "Tickets, cloakroom and shop."), R("Café", 150, "Café overlooking the craft hall."), R("Education room", 100, "School groups."), WC,
      F("Gallery", 200, "A gallery telling one part of the strike wings' story with objects, film and models.")],
     [R("Archive", 200, "Pilots' logbooks, letters and photographs."), R("Conservation lab", 150, "Restores old craft and objects."), WC,
      F("Gallery", 200, "A gallery telling one part of the strike wings' story with objects, film and models.")]],
    ["A sweeping museum with a curved roof like a wing, glass ends showing craft hanging inside."],
    halls=[{"name": "Craft hall", "span": 2, "about": "A tall hall where historic craft hang from the roof and stand on the floor."}],
    capacity="About {people} visitors.", m2_per_person=8)

THEATRE = ring(
    [("Ground floor", 6.0, 1), ("Upper floor", 5.0, 1)],
    [[R("Foyer and bar", 300, "Tickets, bar and meeting place."), R("Cinema", 150, "A cinema screen.", 3), R("Dressing rooms", 30, "Actors get ready.", 4), WC,
      F("Rehearsal room", 80, "Rehearsals.")],
     [R("Projection room", 40, "Projectors for the cinemas."), WC, F("Workshop", 80, "Scenery and costumes.")]],
    ["A warm-lit theatre with a marquee of bulbs over its doors."],
    halls=[{"name": "Main auditorium", "span": 2, "about": "A 600-seat theatre for plays, concerts and shows."}],
    capacity="About 1,000 seats in all.", m2_per_person=5)

COMMONS_PARK = garden("the Quarter's main park", [("Lake", 2, "A lake with paddle boats."), ("Playground", 1, "A big adventure playground."),
                                                  ("Bandstand lawn", 1, "A lawn with a bandstand for summer concerts.")], style=3)

SPORTS_CENTRE = ring(
    [("Sports floor", 9.0, 1), ("Upper floor", 4.2, 1)],
    [[R("Reception", 60, "Book a court or a swim."), R("Changing rooms", 150, "Changing rooms and showers.", 2), R("Café", 100, "Café."), WC,
      F("Squash court", 62, "A squash court.")],
     [R("Gym", 600, "Weights and machines."), R("Studio", 150, "Classes.", 2), WC, F("Treatment room", 20, "Sports massage and physio.")]],
    ["A big sports centre with a glass wall onto the pool and a lit sports hall."],
    halls=[{"name": "Swimming pool hall", "span": 2, "about": "A 50 m pool and a learner pool."},
           {"name": "Sports hall", "span": 2, "share": 0.8, "about": "Courts for basketball, netball and badminton."}],
    capacity="About {people} people.", m2_per_person=15)

COMMONS_HOTEL = ring(
    [("Ground floor", 5.0, 1), ("Room floor", 3.4, (4, 6))],
    [[R("Lobby and front desk", 200, "Families check in."), R("Restaurant", 300, "Breakfast and dinner."), R("Kitchen", 150, "Cooks."), WC,
      F("Lounge", 80, "Sofas.")],
     [R("Linen room", 20, "Sheets and towels."), F("Family room", 32, "A room with a double bed and bunks for children."),
      F("Double room", 24, "A double room with a bathroom.")]],
    ["A welcoming hotel with balconies and a lit name over its door."], capacity="About {people} guests.", m2_per_person=30)

POLICE = ring(
    [("Ground floor", 4.8, 1), ("Upper floor", 4.2, 1)],
    [[R("Front counter", 60, "The public report crimes."), R("Custody suite", 150, "Cells and interview rooms."), R("Control room", 60, "Cameras."), LOCKERS, WC,
      F("Patrol room", 50, "Officers prepare for patrol.")],
     [R("Neighbourhood team office", 80, "Officers who know the Quarter's streets."), KITCHENETTE, WC_STAFF, F("Offices", 30, "Offices.")]],
    ["A tidy blue-trimmed police station with a lit blue lamp by the door."],
    court={"name": "Vehicle yard", "outdoor": True, "about": "Patrol cars park here."}, capacity="About {people} officers.", m2_per_person=20)

QUARTER_FIRE = fire_station("the Pilots' Quarter", [R("Community safety room", 50, "Fire safety talks for schools and residents.")],
                            ["Fire engine", "Fire engine", "Aerial ladder", "Rescue unit"], style=1)


def commons_shops(ctx):
    rng = ctx["rng"]
    return [WC] + rng.sample([
        R("Café", 100, "Coffee and cake."), R("Bakery", 80, "Fresh bread."), R("Pharmacy", 80, "Medicines."), R("Bookshop", 120, "Books."),
        R("Toy shop", 100, "Toys."), R("Hairdresser", 60, "Haircuts."), R("Pub", 150, "The local pub."), R("Bike shop", 100, "Bikes and repairs."),
        R("Florist", 50, "Flowers."), R("Newsagent", 50, "Papers and sweets."), R("Pilot supply shop", 100, "Flight jackets, kit and model craft.")], 4) + \
        [F("|Shop|Takeaway|Boutique|Optician", 70, "A small shop.")]


COMMONS_SHOPS = ring(
    [("Shop floor", 5.0, 1), ("Flat floor", 3.2, (2, 4))],
    [commons_shops, [CLEAN, F("|Two-bedroom flat|One-bedroom flat|Studio flat", 60, "A flat above the shops.")]],
    ["Shops with bright awnings and flats with balconies above.", "A corner block of cafés with planted balconies.",
     "Shops at street level, flats above with teal window frames."],
    capacity="About {people} people.", m2_per_person=25)

POCKET_PARK = garden("small park", [("Seating corner", 1, "Benches under trees.")], style=2)

# ------------------------------------------------------------------ P4 Port Homes / P6 Starboard Homes

TOWERS = apartments("tower residents", look=["A slim apartment tower with lit balconies, a short walk from the station.",
                                             "A tall tower of glass and tan panels with a roof garden."], floors=(12, 20),
                    court={"name": "Lobby garden", "outdoor": True, "about": "A small garden at the tower's foot."})
FAMILY_APTS = apartments("families", look=["Family flats round a courtyard with a playground.", "A tan block of flats with deep balconies round a garden."])


def houses(kind, floors_up, look, garden_name="Shared garden court"):
    return ring(
        [("Ground floor", 3.4, 1), ("Upper floor", 3.0, floors_up)],
        [[F("%s, ground floor" % kind, 55, "The ground floor of one home: front door, kitchen, living room and a toilet.")],
         [F("%s, upper floor" % kind, 55, "The upper floor of one home: bedrooms and a bathroom.")]],
        look, court={"name": garden_name, "outdoor": True, "about": "A shared green court where neighbours meet and children play."},
        wing=12, capacity="About {people} residents.", m2_per_person=40,
        structure="Concrete frame with timber-clad fronts.")


COURTYARD_HOMES = houses("Courtyard home", 1, ["Two-storey homes in warm tan around a garden court."])
CREW_TERRACES = houses("Terraced house", 1, ["A neat row of two-storey houses with front gardens.", "Row houses with teal doors and window boxes."],
                       "Back gardens")
TERRACE_ROW = houses("Terraced house", 1, ["A row of terraced houses with small front gardens.", "Two-storey row houses in tan and white.",
                                           "Terraced homes with bay windows."], "Back gardens")
ROW_HOUSES = houses("Row house", 1, ["Row houses with planted roofs."], "Back gardens")
GARDEN_COURT = houses("Garden court home", (1, 2), ["Homes round a shared green court.", "Low homes with balconies over a garden court.",
                                                    "A ring of homes round a court with a big tree."])
FAMILY_COURTS = houses("Family home", (1, 2), ["Family homes round a safe court where children play."])
SENIOR_VILLAS = houses("Villa", 1, ["Quiet single-storey villas with gardens at the edge of Port Homes."], "Villa gardens")
SENIOR_VILLAS["floors"] = [("Ground floor", 3.6, 1)]
SENIOR_VILLAS["rooms"] = [[R("Residents' lounge", 120, "A shared lounge for coffee mornings."),
                           F("Villa", 90, "A single-storey home for a retired pilot: living room, kitchen, bedroom and garden door.")]]

PORT_SHOPS = ring([("Shop floor", 5.0, 1), ("Flat floor", 3.2, 2)],
                  [[R("Corner shop", 120, "Daily essentials."), R("Café", 100, "Café."), WC, F("|Hairdresser|Laundrette|Takeaway", 60, "A small shop.")],
                   [F("|One-bedroom flat|Studio flat", 50, "A flat above the shops.")]],
                  ["A small corner block of shops with flats above."], capacity="About {people} people.", m2_per_person=25)
PORT_PARK = garden("Port Homes park", [("Playground", 2, "Swings, slides and climbing frames."), ("Paddling pool", 1, "A shallow pool for toddlers.")], style=1)
PORT_CLINIC = clinic("Port Homes", [R("Baby clinic", 40, "Check-ups for babies.")], style=2)
APARTMENT_BLOCK = apartments("families", look=["A long block of flats in tan with balconies.", "A block of flats with teal balconies round a garden.",
                                               "An apartment block with a roof garden."], floors=(4, 6))
NEIGHBOURHOOD_PARK = garden("neighbourhood park", [("Playground", 1, "A playground for local children.")], style=0)

STATION_SQUARE = dict(COMMONS_SQUARE, zones=[
    ("Square", 4, "The square in front of the station where residents meet and set off into the Quarter.",
     [{"size": (16, 10), "rooms": [("Coffee kiosk", 2, "Coffee for commuters."), ("Toilets", 1, "Public toilets.")]}],
     [("Departures board", "A board with the next trains and pods.", (0.45, 0.05, 0.1, 0.05))]),
    ("Bike park", 1, "Racks for residents' bikes."), ("Tree terrace", 1, "Trees and benches.")],
    look="A busy square with a departures board, a coffee kiosk and racks of bikes.")
STATION_SHOPS = ring([("Shop floor", 5.0, 1), ("Upper floor", 4.0, 1)],
                     [[R("Supermarket", 1500, "A grocery for commuters on their way home."), R("Pharmacy", 80, "Medicines."), WC,
                       F("|Newsagent|Florist|Bakery|Coffee shop", 60, "A small shop.")],
                      [F("Office", 40, "Small offices."), KITCHENETTE]],
                     ["A long glass shopfront by the station, lit late into the evening."], capacity="About {people} shoppers.", m2_per_person=8)
HOSTEL = ring([("Ground floor", 4.5, 1), ("Room floor", 3.2, (2, 3))],
              [[R("Front desk", 40, "Check-in."), R("Lounge", 120, "Common room."), R("Kitchen", 60, "Self-catering."), WC, F("Lockers", 30, "Lockers.")],
               [R("Showers", 30, "Shared showers.", 2), F("|Dorm room|Twin room", 24, "A room for visitors to the Quarter.")]],
              ["A plain, friendly hostel with a lit sign."], capacity="About {people} beds.", m2_per_person=12)
STATION_GARDEN = garden("garden by the station", [("Waiting lawn", 1, "A lawn to wait on for a train.")], style=3)

STARBOARD_TOWERS = apartments("tower residents", look=["A slender tower with a lit crown, by the station."], floors=(10, 16),
                              court={"name": "Lobby garden", "outdoor": True, "about": "A small garden at the tower's foot."})
GARDEN_APTS = apartments("families", look=["Flats with planted roof gardens and trailing green balconies."], floors=(3, 5),
                         fills=[F("|Two-bedroom flat|Three-bedroom flat", 85, "A family flat with its own share of the roof garden."),
                                F("One-bedroom flat", 50, "A flat for a couple or one person.")])
HANGAR_LOFTS = apartments("loft residents", look=["A former-hangar-style block with arched steel roofs and huge loft windows."], floors=(2, 3),
                          fills=[F("Loft", 140, "A big open loft with high ceilings, for crews who want flexible space.")])
STARBOARD_MARKET = ring([("Market floor", 6.0, 1)],
                        [[R("Market office", 40, "Runs the market."), WC,
                          F("|Grocer|Butcher|Baker|Fishmonger|Spice stall", 50, "A food stall.")]],
                        ["A food market with a sawtooth glass roof."],
                        halls=[{"name": "Market hall", "span": 1, "about": "Food stalls under a glass roof."}], capacity="About {people} shoppers.", m2_per_person=5)
STARBOARD_GREEN = garden("Starboard Homes green", [("Sports courts", 2, "Tennis and basketball courts."), ("Playground", 1, "A playground.")], style=0)
TRAINEE_FLATS = apartments("new graduates", look=["A compact block of small flats with bright doors."], floors=(3, 4),
                           fills=[F("|Studio flat|One-bedroom flat", 35, "A small flat for a new graduate pilot or crew member.")])
STARBOARD_CLINIC = clinic("Starboard Homes", [R("Baby clinic", 40, "Check-ups for babies.")], style=1)

PROGRAMS = [
    (r"^Flight School Main Hall$", FLIGHT_SCHOOL_MAIN), (r"^Training Hangar$", TRAINING_HANGAR), (r"^Training Flight Line$", FLIGHT_LINE),
    (r"^Navigation School$", NAV_SCHOOL), (r"^Engineering School$", ENGINEERING_SCHOOL), (r"^Survival School$", SURVIVAL_SCHOOL),
    (r"^Cadet Parade Ground$", PARADE_GROUND), (r"^Trainee Halls", TRAINEE_HALLS), (r"^Instructors' Apartments$", INSTRUCTORS_APTS),
    (r"^School Library$", SCHOOL_LIBRARY), (r"^School Canteen$", SCHOOL_CANTEEN), (r"^School Sports Field$", SPORTS_FIELD),
    (r"^Flight School Clinic$", SCHOOL_CLINIC), (r"^Cadet House", CADET_HOUSE), (r"^Training Field", TRAINING_FIELD),
    (r"^Full-Motion Simulator Hall$", FULL_MOTION), (r"^Squadron Simulator Hall$", SQUADRON_SIM), (r"^Cruiser Bridge Simulator$", BRIDGE_SIM),
    (r"^Zero-G Training Tank$", ZERO_G), (r"^Centrifuge Hall$", CENTRIFUGE), (r"^Simulator Control Centre$", SIM_CONTROL),
    (r"^Simulator Workshops$", SIM_WORKSHOPS), (r"^Public Flight Arcade$", ARCADE), (r"^Starboard Lawn$", STARBOARD_LAWN),
    (r"^Simulator Halls Canteen$", SIM_CANTEEN), (r"^Simulator Data Centre$", SIM_DATA), (r"^Simulator Annex", SIM_ANNEX), (r"^Lawn( \d+)?$", LAWN),
    (r"^Pilots' Quarter Town Hall$", TOWN_HALL), (r"^Commons Square$", COMMONS_SQUARE), (r"^Commons Market$", COMMONS_MARKET),
    (r"^Restaurants Row$", RESTAURANTS), (r"^Quarter Primary School$", PRIMARY), (r"^Quarter Secondary School$", SECONDARY),
    (r"^Childcare Centre$", CHILDCARE), (r"^Quarter Hospital$", HOSPITAL), (r"^Family Health Centre$", FAMILY_HEALTH),
    (r"^Quarter Library$", QUARTER_LIBRARY), (r"^Aerion Flight Museum$", MUSEUM), (r"^Pilots' Theatre$", THEATRE),
    (r"^Commons Park$", COMMONS_PARK), (r"^Sports Centre$", SPORTS_CENTRE), (r"^Commons Hotel$", COMMONS_HOTEL),
    (r"^Quarter Police Station$", POLICE), (r"^Quarter Fire Station$", QUARTER_FIRE), (r"^Commons Shops", COMMONS_SHOPS),
    (r"^Pocket Park", POCKET_PARK),
    (r"^Pilots' Towers", TOWERS), (r"^Family Apartments", FAMILY_APTS), (r"^Port Homes Shops$", PORT_SHOPS), (r"^Port Homes Park$", PORT_PARK),
    (r"^Courtyard Homes", COURTYARD_HOMES), (r"^Port Homes School$", PORT_SCHOOL), (r"^Crew Terraces", CREW_TERRACES),
    (r"^Senior Pilots' Villas$", SENIOR_VILLAS), (r"^Port Homes Clinic$", PORT_CLINIC), (r"^Apartment Block", APARTMENT_BLOCK),
    (r"^Garden Court", GARDEN_COURT), (r"^Neighbourhood Park", NEIGHBOURHOOD_PARK), (r"^Terrace Row", TERRACE_ROW),
    (r"^Station Square$", STATION_SQUARE), (r"^Station Shops$", STATION_SHOPS), (r"^Quarter Hostel$", HOSTEL), (r"^Station Garden", STATION_GARDEN),
    (r"^Starboard Towers", STARBOARD_TOWERS), (r"^Garden Apartments", GARDEN_APTS), (r"^Hangar Lofts$", HANGAR_LOFTS),
    (r"^Starboard Homes Market$", STARBOARD_MARKET), (r"^Starboard Green$", STARBOARD_GREEN), (r"^Trainee Flats$", TRAINEE_FLATS),
    (r"^Family Courts", FAMILY_COURTS), (r"^Starboard Homes School$", STARBOARD_SCHOOL), (r"^Row Houses", ROW_HOUSES),
    (r"^Starboard Homes Clinic$", STARBOARD_CLINIC),
]

for _n, _st in {"Flight School": 0, "Simulator Halls": 1, "Commons": 2, "Port Homes": 3, "Station": 1, "Starboard Homes": 2}.items():
    _ex = {"Simulator Halls": [R("Simulator power room", 200, "Extra power for the moving simulators.")],
           "Commons": [R("Hospital supply room", 150, "A dedicated, duplicated feed to the Quarter Hospital.")]}.get(_n, [])
    PROGRAMS.append((r"^%s Utility Plant$" % _n, utility_plant(_n, _ex, style=_st)))
    PROGRAMS.append((r"^%s Service Shaft$" % _n, service_shaft(_n, style=(_st + 1) % 4)))

# More fill types for the biggest floors, so they don't repeat one room hundreds of times
_MORE = [
    (SIM_ANNEX, 0, [F("Procedures trainer room", 50, "A fixed cockpit with real switches, for practising checklists."),
                    F("Briefing room", 50, "Instructor and trainee plan the session.")]),
    (SIM_ANNEX, 1, [F("Classroom", 60, "Lessons between simulator sessions."), F("Rest lounge", 60, "Trainees rest between sessions.")]),
    (FULL_MOTION, 0, [F("Briefing room", 60, "Instructor and trainee plan the session.")]),
    (FULL_MOTION, 1, [F("Classroom", 60, "Lessons on the craft being flown."), F("Instructors' office", 40, "Instructors.")]),
    (SQUADRON_SIM, 0, [F("Squadron ready room", 80, "A squadron waits and plans before its mission."),
                       F("Debrief room", 60, "The whole squadron replays its mission.")]),
    (SQUADRON_SIM, 1, [F("Classroom", 60, "Tactics lessons.")]),
    (SPORTS_CENTRE, 1, [F("Fitness studio", 120, "Classes such as spinning, yoga and circuits."), F("Climbing wall room", 150, "An indoor climbing wall.")]),
    (STATION_SHOPS, 1, [F("Community room", 60, "A room residents can book.")]),
    (TOWN_HALL, 1, [F("Meeting room", 40, "Meetings with residents.")]),
    (FAMILY_HEALTH, 0, [F("Treatment room", 30, "Dressings, injections and checks."), F("Health visitor room", 30, "Visits for new families.")]),
    (SCHOOL_CLINIC, 0, [F("Treatment room", 30, "Dressings and injuries from training.")]),
    (PORT_CLINIC, 0, [F("Treatment room", 30, "Dressings, injections and checks.")]),
    (STARBOARD_CLINIC, 0, [F("Treatment room", 30, "Dressings, injections and checks.")]),
    (SURVIVAL_SCHOOL, 0, [F("Kit drying room", 40, "Wet survival kit dries out after drills.")]),
]
for _p, _i, _rows in _MORE:
    if not callable(_p["rooms"][_i]):
        _p["rooms"][_i] = list(_p["rooms"][_i]) + _rows
HOSTEL["rooms"][0] = [r for r in HOSTEL["rooms"][0] if r[0] != "*Lockers"] + [F("Games room", 60, "Pool table and games."), F("Lounge", 80, "Sofas.")]
SPORTS_CENTRE["rooms"][0] = list(SPORTS_CENTRE["rooms"][0]) + [F("Dance studio", 120, "Dance and martial arts classes."),
                                                               F("Indoor court", 300, "A court for five-a-side, futsal and volleyball.")]
