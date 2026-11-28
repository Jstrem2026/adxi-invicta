# Port of Arrivals: city planner check

Made by `Invicta/tools/city_planner.py` on 2026-11-28 from the program in `Invicta/data/city_programs.json`. It checks the district against what it is for and lists what is missing. Items marked **proposed** are the planner's suggestions; nothing already designed was moved or removed.

**What this district is for** (Jordan, 28 Nov 2026): The main way in and out of the whole ship. People arrive and leave here, whether military, commercial or community, so the outer hull needs many doors, big and small, and the port needs high security.

## 1. Doors in the hull

| Kind of door | Used by | Doors | Widths | Opened by | Check |
|---|---|---|---|---|---|
| Passenger shuttle gates | commercial | 17 | 131 ft (40 m), see note | Gate Operations | ✅ |
| Ship berths (civilian and private ships) | commercial | 28 | 262 ft (80 m), 367 ft (112 m), 919 ft (280 m) | Harbourmaster, Stern Harbourmaster | ✅ |
| Yard lock (ships to the repair yards) | commercial | 1 | 1,640 ft (500 m) | Harbourmaster, Stern Harbourmaster | ✅ |
| Small craft locks (skiffs and private runabouts) | community | 0 | none | Harbourmaster, Stern Harbourmaster | ⚠️ Skiff Marina has no door to space. |
| Guard and government berths (security, military and official craft) | military | 0 | none | nobody yet | ⚠️ Needs at least 2. |
| Crew airlocks (small walk-through doors for crews, inspectors and suited work) | crew | 0 | none | nobody yet | ⚠️ Needs at least 1. |
| Freight gate (cargo ships) | commercial | 0 | none | nobody yet | ℹ️ left for Jordan |

Pressure zones: the hull front has 20 zones (one per 1,640 ft (500 m) frame). 0 of them have a crew airlock.

- **Guard and government berths (security, military and official craft):** Jordan: doors for military as well as commercial and community traffic. The big warships use the Cruiser Docks; the Port needs its own berths for patrol cutters, military transports and official arrivals, one at each end of the hull front.
- **Crew airlocks (small walk-through doors for crews, inspectors and suited work):** Every 1,640 ft (500 m) frame of hull is its own sealable pressure zone (Ship Reference 5), so each needs a small door that does not need a ship-sized door to open.
- **Freight gate (cargo ships):** Cargo now comes in through the berths and goes by Dock Road to Cargo Customs. A gate of its own beside Freight (P4) would need hull frontage that is all in use. Left for Jordan.

## 2. Help within reach of every door

| Service | Must be within | Doors out of reach | Furthest |
|---|---|---|---|
| Fire and rescue | 0.99 mi (1.60 km) | ⚠️ 8 of 46 | 1.77 mi (2.85 km) |
| Police and port security | 0.99 mi (1.60 km) | ⚠️ 6 of 46 | 1.97 mi (3.18 km) |
| Medical | 1.55 mi (2.50 km) | ⚠️ 6 of 46 | 2.43 mi (3.90 km) |
| Border clearance (passport, customs and health checks) | 1.24 mi (2.00 km) | ⚠️ 12 of 46 | 2.33 mi (3.76 km) |

- **Fire and rescue:** Airport fire rules: crash rescue reaches any point of a runway in 3 minutes, about 1 mile (1.6 km).
- **Police and port security:** Every hull door is a way into the ship; a police post within about a mile can reach it in minutes.
- **Medical:** Injured crew or sick arrivals reach a clinic within about 1.5 miles (2.5 km).
- **Border clearance (passport, customs and health checks):** Everyone who comes through a hull door is checked before they reach the public side of the port. Each door needs a clearance point close by, so no one walks a long way unchecked.

Distances are straight lines from the middle of each door to the nearest wall of the building. All are planner assumptions for Jordan to confirm.

## 3. Security and services the port must have

| Need | Found in | Check |
|---|---|---|
| Health screening and quarantine | Port Health | ✅ |
| Departure security screening | Departures Terminal | ✅ |
| Cargo inspection | Cargo Customs, Customs & Border Hq | ✅ |
| Custody suite (holding cells) | Arrivals Police Post, Customs & Border Hq, Concourse Police Post, Bow Docks Police Post, Stern Docks Police Post | ✅ |
| One command room for every hull door | nothing yet | ⚠️ |

Every precinct has its own utility plant and service shaft.

## 4. What the planner adds (proposed)

- **P1-13 Bow Guard Berth** in P1, 1 bay, 394 × 262 ft (120 × 80 m), at D5-F41-A. A secure berth in the hull for the port guard's patrol cutters, military transports and official arrivals. Ships here are met by the guard and cleared on the spot, away from the passenger gates.
- **P3-19 Stern Guard Berth** in P3, 1 bay, 394 × 262 ft (120 × 80 m), at D5-F55-A. A secure berth in the hull for the port guard's patrol cutters, military transports and official arrivals. Ships here are met by the guard and cleared on the spot, away from the passenger gates.
- **P1-14 Port Guard Station** in P1, 820 × 656 ft (250 × 200 m), at D5-F37-B. Home of the port guard, the armed security force for the hull doors. Guard crews for the cutters, a ready room, an armoury and a holding area sit beside the guard berths, so the guard can close and hold any door in minutes.
- **P1-12 Skiff Marina**: 2 new doors in the hull (Planner, 28 Nov 2026: two skiff locks in the hull, 131 ft (40 m) wide, at the thirds of the marina).
- **P2-24 Arrivals Crew Airlocks** in P2, 5 airlocks, each 33 × 26 ft (10 × 8 m), at D5-F44-A. Small airlocks in the hull, one in each pressure zone, so crews, inspectors and suited workers can step outside or come in without opening a ship-sized door. Each is a chamber with a door at each end.
- **P1-15 Bow Docks Crew Airlocks** in P1, 5 airlocks, each 33 × 26 ft (10 × 8 m), at D5-F39-A. Small airlocks in the hull, one in each pressure zone, so crews, inspectors and suited workers can step outside or come in without opening a ship-sized door. Each is a chamber with a door at each end.
- **P3-20 Stern Docks Crew Airlocks** in P3, 10 airlocks, each 33 × 26 ft (10 × 8 m), at D5-F51-A. Small airlocks in the hull, one in each pressure zone, so crews, inspectors and suited workers can step outside or come in without opening a ship-sized door. Each is a chamber with a door at each end.
- **P1-16 Bow Docks Border Post** in P1, 984 × 656 ft (300 × 200 m), at D5-F36-B. A border post beside the docks. Crews and passengers of ships berthed here show their passports, declare goods and are health-checked before they walk into the port, and departing crews are checked out here.
- **P2-25 Port Security Command** in P2, 820 × 656 ft (250 × 200 m), at D5-F45-C. The one room that watches every hull door of the port. It sees every gate, berth, lock and airlock, can lock them all down at once, runs the port guard and works with Customs & Border Hq, the harbourmasters and Gate Operations.
- **P8-21 Stern Docks First Aid Post** in P8, 492 × 328 ft (150 × 100 m), at D5-F53-E. A first aid post close to the far berths, with paramedics, a treatment room and an ambulance bay, for injured crews and sick arrivals before they go on to a clinic.
- **P1-17 Bow Docks Fire Post** in P1, 656 × 492 ft (200 × 150 m), at D5-F35-B. A small crash-fire-rescue post close to the far berths, with two rescue appliances and a crew on watch, so a fire or accident at any hull door is reached within about three minutes.
- **P1-18 Bow Docks First Aid Post** in P1, 492 × 328 ft (150 × 100 m), at D5-F35-B. A first aid post close to the far berths, with paramedics, a treatment room and an ambulance bay, for injured crews and sick arrivals before they go on to a clinic.

### After the additions

Still missing: Fire and rescue (9 doors out of reach); Border clearance (6 doors out of reach).

The planner found no free land for these (every lot near those doors is taken):

- P3: no free land within 0.99 mi (1.60 km) of 5 hull doors for a Stern Docks Fire Post.
- P3: no free land within 1.24 mi (2.00 km) of 5 hull doors for a Stern Docks Border Post.

## 5. Left for Jordan

- Freight gate (cargo ships): Cargo now comes in through the berths and goes by Dock Road to Cargo Customs. A gate of its own beside Freight (P4) would need hull frontage that is all in use. Left for Jordan.
- Escape craft and lifeboats are not designed anywhere on the ship yet, so the planner does not place any.
- Room plans, heights and looks of the new items are not designed yet.
